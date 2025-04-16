from flask import Flask
from flask_restx import Api, Resource, fields
from flask_cors import CORS
from flask import send_file

app = Flask(__name__)
CORS(app)
api = Api(app, version='1.0', title='Template Generator API',
          description='Template Generator App',
          )
from template import getCatergoryDropDownData, getTemplateFeilds, generateProtectedPDF
ns = api.namespace('template', description='Template operations')


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

@ns.route('/generate-template-pdf')
class GenerateProtectedPDF(Resource):
    @ns.expect(GenerateProtectedPDFParams)
    def post(self):
        CaseType = api.payload['CaseType']
        templateType = api.payload['templateType']
        replacements = api.payload['replacements']
        secured_pdf = generateProtectedPDF(CaseType, templateType, replacements)
        return send_file(
                secured_pdf,
                as_attachment=True,
                download_name="Secured"+templateType+".pdf",
                mimetype='application/pdf'
    )

if __name__ == '__main__':
    app.run(debug=True)
