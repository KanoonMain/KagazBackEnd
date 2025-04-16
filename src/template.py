import pandas as pd
from connect_db import getConnection
import json
from docx import Document
from docx2pdf import convert
from io import BytesIO
from datetime import datetime
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import re


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
    print(df)
    return df

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
    # today_date = datetime.now().strftime("%Y-%m-%d")
    temp_docx = "Filled_Rental_Agreement.docx"
    doc.save(temp_docx)
    # output_pdf = "Filled_Rental_Agreement_New.pdf"
    # secured_pdf = "Secured_Rental_Agreement.pdf"
    # convert(temp_docx, output_pdf)
    # with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as temp_docx_file:
    #     temp_docx_path = temp_docx_file.name
    #     doc.save(temp_docx_path)
    #
    # # Step 2: Convert DOCX to PDF using docx2pdf and save to temp PDF
    # with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf_file:
    #     temp_pdf_path = temp_pdf_file.name
    #     convert(temp_docx_path, temp_pdf_path)
    # # === Step 5: Apply PDF security (disable copy & print) ===
    # with pikepdf.open(temp_pdf_path) as pdf:
    #     encrypted_pdf_stream = BytesIO()
    #     pdf.save(
    #         encrypted_pdf_stream,
    #         encryption=pikepdf.Encryption(
    #             user="",
    #             owner="secret",
    #             allow=pikepdf.Permissions(
    #                 extract=False,
    #                 modify_annotation=False,
    #                 modify_assembly=False,
    #                 modify_form=False,
    #                 modify_other=False,
    #                 print_lowres=True,
    #                 print_highres=True
    #             )
    #         )
    #     )
    # encrypted_pdf_stream.seek(0)
    return True


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
