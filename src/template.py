import pandas as pd
from connect_db import getConnection
import json
from docx import Document
from docx2pdf import convert
from io import BytesIO
from datetime import datetime
import re
import os
import sys
import subprocess
import pikepdf


def getCatergoryDropDownData():
    conn = getConnection()
    sql = ("SELECT LOWER(REPLACE(ct2.name, ' ', '_')) as caseTypeValue, ct2.name as caseTypeLabel ,  LOWER(REPLACE("
           "templateName, ' ', '_')) as value, templateName  as label from TemplateTypes ct  inner join CaseTypes ct2 "
           "on ct.caseTypeid  = ct2.id where ct.isActive = 1")
    # Load into DataFrame
    df = pd.read_sql_query(sql, conn)
    grouped_dict = df.groupby("caseTypeValue").apply(
        lambda g: g[["value", "label"]].to_dict(orient="records")
    ).to_dict()
    case_types_array = df[["caseTypeValue", "caseTypeLabel"]].drop_duplicates().rename(
        columns={"caseTypeValue": "value", "caseTypeLabel": "label"}
    ).to_dict(orient="records")
    data = {
        "CaseTypes": case_types_array,
        "TemplateTypes": grouped_dict
    }
    return data

def getDatafromTable(tableName):
    conn = getConnection()
    sql = f'''SELECT * FROM {tableName}'''
    df = pd.read_sql_query(sql, conn)
    df = df.to_dict(orient='records')
    return df

def updateRecordInTable(tableName: str, updateData: dict, whereCondition: dict):
    conn = getConnection()
    cursor = conn.cursor()
    try:
        set_clause = ", ".join([f"{key} = ?" for key in updateData.keys()])
        set_values = list(updateData.values())
        where_clause = " AND ".join([f"{key} = ?" for key in whereCondition.keys()])
        where_values = list(whereCondition.values())
        sql = f'''UPDATE {tableName} SET {set_clause} WHERE {where_clause}'''
        values = set_values + where_values
        cursor.execute(sql, values)
        conn.commit()
        return f"{cursor.rowcount} row(s) updated in '{tableName}'."
    except Exception as e:
        conn.rollback()
        return "Error updating record:" + str(e)
    finally:
        conn.close()

def getTemplateFeilds(caseType, TemplateType):
    conn = getConnection()
    sql = f'''
    SELECT templateForm FROM Templates t WHERE t.caseTypeid = ( SELECT id FROM CaseTypes where name = '{caseType}') and 
    t.TemplateTypeid = ( SELECT id FROM TemplateTypes tt  where templateName = '{TemplateType}')
    '''
    df = pd.read_sql_query(sql, conn)
    df = df.iloc[0][0]
    df = df.replace("'", '"')
    df = json.loads(df)
    return df


def updateTemplateFields(caseType, TemplateType, updatedData):
    conn = getConnection()
    cursor = conn.cursor()
    # Ensure the updated data is a JSON string with single quotes for SQL
    updated_json = json.dumps(updatedData).replace('"', "'")
    sql = f'''
    UPDATE Templates
    SET templateForm = '{updated_json}'
    WHERE caseTypeid = (SELECT id FROM CaseTypes WHERE name = '{caseType}')
      AND TemplateTypeid = (SELECT id FROM TemplateTypes WHERE templateName = '{TemplateType}')
    '''
    try:
        cursor.execute(sql)
        conn.commit()
        return "Template updated successfully."
    except Exception as e:
        return "Error updating template:" + str(e)
    finally:
        conn.close()


def extractDataItems(document, caseType, TemplateType):
    doc = Document(document)
    full_text = ''
    for para in doc.paragraphs:
        full_text += para.text + '\n'
    placeholders = re.findall(r'\[([^\[\]]+)\]', full_text)
    placeholdersData = {item: item for item in placeholders}
    conn = getConnection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id FROM CaseTypes WHERE name = ?', (caseType,))
        case_row = cursor.fetchone()
        if not case_row:
            raise ValueError(f"CaseType '{caseType}' not found.")
        caseTypeid = case_row[0]
        cursor.execute('SELECT id FROM TemplateTypes WHERE templateName = ?', (TemplateType,))
        template_row = cursor.fetchone()
        TemplateTypeid = template_row[0]
        cursor.execute(
            '''
            SELECT id FROM Templates 
            WHERE caseTypeid = ? AND TemplateTypeid = ?
            ''',
            (caseTypeid, TemplateTypeid)
        )
        existing = cursor.fetchone()
        if existing:
            cursor.execute(
                '''
                UPDATE Templates 
                SET templateData = ?, templateForm = ?
                WHERE caseTypeid = ? AND TemplateTypeid = ?
                ''',
                (document, str(placeholdersData), caseTypeid, TemplateTypeid)
            )
            print("Existing template updated.")
        else:
            cursor.execute(
                '''
                INSERT INTO Templates (caseTypeid, TemplateTypeid, templateData, templateForm)
                VALUES (?, ?, ?, ?)
                ''',
                (caseTypeid, TemplateTypeid, document, str(placeholdersData))
            )
            print("New template inserted.")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("Error in extractDataItems:", e)
    finally:
        conn.close()
    return placeholdersData


def replace_placeholders_in_paragraph(paragraph, replacements):
    # Combine runs into full text
    full_text = ''.join(run.text for run in paragraph.runs)

    # Replace placeholders like [LandlordFullName] with data values
    for key, value in replacements.items():
        pattern = rf"\[{re.escape(key)}\]"
        full_text = re.sub(pattern, value, full_text)

    # Clear all existing runs
    for run in paragraph.runs:
        run.text = ''

    # Set the new text to the first run
    if paragraph.runs:
        paragraph.runs[0].text = full_text
    else:
        paragraph.add_run(full_text)


def generateProtectedPDF(caseType, TemplateType, replacements):
    conn = getConnection()
    cursor = conn.cursor()
    sql = f'''
    SELECT templateData FROM Templates t WHERE t.caseTypeid = ( SELECT id FROM CaseTypes where name = '{caseType}') and
    t.TemplateTypeid = ( SELECT id FROM TemplateTypes tt  where templateName = '{TemplateType}')
    '''
    cursor.execute(sql)
    row = cursor.fetchone()
    conn.close()
    doc_blob = row[0]
    doc_stream = BytesIO(doc_blob)
    doc = Document(doc_stream)
    for para in doc.paragraphs:
        replace_placeholders_in_paragraph(para, replacements)
    today_date = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
    if sys.platform == "win32":
        mainPath = os.getcwd() + '\\temp\\'
    else:
        mainPath = os.getcwd() + '\\temp\\'
    if not os.path.exists(mainPath):
        print("Created")
        os.mkdir(mainPath)
    temp_docx = mainPath + str(today_date) + TemplateType.replace(' ', '_') + '.docx'
    doc.save(temp_docx)
    output_pdf = mainPath + str(today_date) + TemplateType.replace(' ', '_') + '.pdf'
    if sys.platform == "win32":
        import pythoncom
        pythoncom.CoInitialize()
        convert(temp_docx, output_pdf)
    else:
        # sudo apt-get install unoconv libreoffice
        subprocess.run(['unoconv', '-f', 'pdf', '-o', output_pdf, temp_docx])
    with pikepdf.open(output_pdf) as pdf:
        encrypted_pdf_stream = BytesIO()
        pdf.save(
            encrypted_pdf_stream,
            encryption=pikepdf.Encryption(
                user="",
                owner="secret",
                allow=pikepdf.Permissions(
                    extract=False,
                    modify_annotation=False,
                    modify_assembly=False,
                    modify_form=False,
                    modify_other=False,
                    print_lowres=True,
                    print_highres=True
                )
            )
        )
    print("Completed")
    encrypted_pdf_stream.seek(0)
    return encrypted_pdf_stream, today_date


if __name__ == '__main__':
    data = {
        "LandlordFullName": "John Doe Landlord",
        "LandlordAddress": "Random Landlord",
        "Tenant Full Name": "John Doe Tenant ",
        "Tenant Address": "Random Tenant’s ",
        "Rental Property Address": "ABCD",
        "Start Date": "16-04-2025",
        "End Date": "16-04-2025",
        "Amount": "1000",
        "month/week": "Month",
        "day": "5th",
        "payment method": "NEFT",
        "SecurityAmount": "10000",
        "X": "10",
        "number": "30"
    }
    generateProtectedPDF("Civil Templates", "Rental Lease Templates", data)
