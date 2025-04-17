from flask import Flask, request
from flask_restx import Api, Resource, fields
from flask_cors import CORS
from flask import send_file
import os
import sys
from werkzeug.datastructures import FileStorage

app = Flask(__name__)
CORS(app)
api = Api(app, version='1.0', title='Template Generator API',
          description='Template Generator App',
          )
from template import getCatergoryDropDownData, getTemplateFeilds, generateProtectedPDF, updateTemplateFields, extractDataItems, getDatafromTable, updateRecordInTable

ns = api.namespace('template', description='Template operations')


# Models for Swagger docs
update_model = api.model('UpdateModel', {
    'updateData': fields.Raw(required=True, description='Fields to update'),
    'whereCondition': fields.Raw(required=True, description='WHERE conditions to identify records'),
})

# GET Endpoint
@ns.route('/<string:tableName>')
class TableData(Resource):
    def get(self, tableName):
        """Fetch all data from the specified table"""
        try:
            data = getDatafromTable(tableName)
            return data, 200
        except Exception as e:
            return {"error": str(e)}, 500

    @ns.expect(update_model)
    def put(self, tableName):
        """Update records in the specified table"""
        payload = request.json
        updateData = payload.get('updateData', {})
        whereCondition = payload.get('whereCondition', {})
        if not updateData or not whereCondition:
            return {"error": "Both 'updateData' and 'whereCondition' must be provided."}, 400
        result = updateRecordInTable(tableName, updateData, whereCondition)
        return result
@ns.route('/list-templates')
class TodoList(Resource):
    def get(self):
        data = getCatergoryDropDownData()
        return data


getTemplateDataParams = api.model('Todo', {
    'CaseType': fields.String(required=True, description='The CaseType unique identifier'),
    'templateType': fields.String(required=True, description='The templateType identifier')
})


@ns.route('/get-templates-feilds')
class getTemplateData(Resource):
    @ns.expect(getTemplateDataParams)
    def post(self):
        CaseType = api.payload['CaseType']
        templateType = api.payload['templateType']
        data = getTemplateFeilds(CaseType, templateType)
        return data


GenerateProtectedPDFParams = api.model('GenerateProtectedPDFParams', {
    'CaseType': fields.String(required=True, description='The CaseType unique identifier'),
    'templateType': fields.String(required=True, description='The templateType identifier'),
    'replacements': fields.Raw(required=True, description='Dynamic replacement key-value pairs')
})


@ns.route('/update-templates-fields')
class UpdateFormFields(Resource):
    @ns.expect(GenerateProtectedPDFParams)
    def post(self):
        CaseType = api.payload['CaseType']
        templateType = api.payload['templateType']
        replacements = api.payload['replacements']
        response = updateTemplateFields(CaseType, templateType, replacements)
        return response

upload_parser = api.parser()
upload_parser.add_argument('file', location='files',
                           type=FileStorage, required=True,
                           help='Word document file (.docx)')
upload_parser.add_argument('caseType', location='form',
                           type=str, required=True,
                           help='Name of the case type')
upload_parser.add_argument('TemplateType', location='form',
                           type=str, required=True,
                           help='Name of the template type')

@ns.route('/upload-documents')
@ns.expect(upload_parser)
class UploadWordDoc(Resource):
    def post(self):
        args = upload_parser.parse_args()
        file = args['file']
        caseType = args['caseType']
        TemplateType = args['TemplateType']
        if file and file.filename.endswith('.docx'):
            doc = extractDataItems(file, caseType, TemplateType)
            return doc, 200
        else:
            return {"error": "Invalid file type. Please upload a .docx file."}, 400

@ns.route('/generate-template-pdf')
class GenerateProtectedPDF(Resource):
    @ns.expect(GenerateProtectedPDFParams)
    def post(self):
        try:
            CaseType = api.payload['CaseType']
            templateType = api.payload['templateType']
            replacements = api.payload['replacements']
            secured_pdf, today_date = generateProtectedPDF(CaseType, templateType, replacements)
            if sys.platform == "win32":
                mainPath = os.getcwd() + '\\temp\\'
            else:
                mainPath = os.getcwd() + '\\temp\\'
            try:
                temp_docx = mainPath + str(today_date) + templateType.replace(' ', '_') + '.docx'
                output_pdf = mainPath + str(today_date) + templateType.replace(' ', '_') + '.pdf'
                os.remove(temp_docx)
                os.remove(output_pdf)
            except Exception as e:
                print(e)
            return send_file(
                secured_pdf,
                as_attachment=True,
                download_name="Secured" + templateType + ".pdf",
                mimetype='application/pdf'
            )
        except Exception as e:
            return str(e), 500


if __name__ == '__main__':
    app.run(debug=True)
