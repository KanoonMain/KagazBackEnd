import ast
import json
from flask import Flask, request
from flask_restx import Api, Resource, fields
from flask_cors import CORS
from flask import send_file, jsonify
import os
import sys
from werkzeug.datastructures import FileStorage
from flask_jwt_extended import JWTManager, get_jwt_identity, jwt_required
from flask_bcrypt import Bcrypt
from flask import  redirect
from kanoon_db import requestDataDelete
from userOperations import userRegister, userLogin, userCredits, rechargeCredits, userUpdatePassword, userOrders, userOrderRegenerate, initiatePhonePePayment, verify_payment
app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)
from datetime import timedelta
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=12)
app.config['JWT_SECRET_KEY'] = 'kanoon-prod'
jwt = JWTManager(app)
api = Api(app, version='1.0', title='Template Generator API',
          description='Template Generator App',
          )
from template import getCatergoryDropDownData, getTemplateFeilds, generateProtectedPDF, updateTemplateFields, \
    extractDataItems, getDatafromTable, updateRecordInTable, getDataSet, checkUserBalance

ns = api.namespace('template', description='Template operations')
kn = api.namespace('kanoon', description='Kanoon DB operations')
# Models for Swagger docs
update_model = api.model('UpdateModel', {
    'updateData': fields.Raw(required=True, description='Fields to update'),
    'whereCondition': fields.Raw(required=True, description='WHERE conditions to identify records'),
})


# GET Endpoint
@ns.route('/getValues')
class TableData(Resource):
    def get(self):
        """Fetch all data from the specified table"""
        try:
            data = getDataSet()
            return data, 200
        except Exception as e:
            return {"error": str(e)}, 500

@ns.route('/register')
class TableDataRegister(Resource):
    def post(self):
        """Fetch all data from the specified table"""
        try:
            data = request.get_json()
            email = data['email']
            password = data['password']
            data, statusCode = userRegister(email, password, bcrypt)
            return data, statusCode
        except Exception as e:
            return {"error": str(e)}, 500

@ns.route('/credits')
class TableDataUserCredits(Resource):
    @jwt_required()
    def get(self):
        try:
            user_id = get_jwt_identity()
            data, statusCode = userCredits(int(user_id))
            return data, statusCode
        except Exception as e:
            return jsonify({'message': 'Failed to retrieve credits', 'error': str(e)}), 500

# @ns.route('/recharge')
# class TableDataUserCreditRecharge(Resource):
#     @jwt_required()
#     def post(self):
#         try:
#             data = api.payload
#             amount = data.get('amount')
#             user = get_jwt_identity()
#             data, statusCode = rechargeCredits(user, amount)
#             return data, statusCode
#         except Exception as e:
#             return {'message': 'Recharge failed', 'error': str(e)}, 500

@ns.route('/protected')
class TableDataUser(Resource):
    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        return {'message': f'Hello {current_user["email"]}'}, 200

@ns.route('/login')
class TableDataLogin(Resource):
    def post(self):
        """Fetch all data from the specified table"""
        try:
            data = request.get_json()
            email = data['email']
            password = data['password']
            data, statusCode = userLogin(email, password, bcrypt)
            return data, statusCode
        except Exception as e:
            return {"error": str(e)}, 500

@ns.route('/update-password')
class TableDataUpdatePassword(Resource):
    @jwt_required()
    def post(self):
        """Fetch all data from the specified table"""
        try:
            data = request.get_json()
            email = data['email']
            oldPassword = data['oldPassword']
            newPassword = data['newPassword']
            data, statusCode = userUpdatePassword(email, oldPassword, newPassword,  bcrypt)
            return data, statusCode
        except Exception as e:
            return {"error": str(e)}, 500

@ns.route('/orders')
class TableDataUserOrders(Resource):
    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        data, statusCode = userOrders(current_user)
        return data, statusCode
@ns.route('/<string:tableName>')
class TableData(Resource):
    def get(self, tableName):
        """Fetch all data from the specified table"""
        try:
            data = getDatafromTable(tableName)
            return data, 200
        except Exception as e:
            return {"error": str(e)}, 500

    def post(self, tableName):
        """Update records in the specified table"""
        payload = request.json
        updateData = api.payload
        result = updateRecordInTable(tableName, updateData)
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


@ns.route('/get-templates-fields')
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
        replacements = api.payload['replacement']
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
@ns.route('/regenerate')
class ReGenerateProtectedPDF(Resource):
     @jwt_required()
     def post(self):
            try:
                user_id = get_jwt_identity()
                orderId = api.payload['orderId']
                CaseType, templateType, replacements = userOrderRegenerate(user_id, orderId)
                replacements = ast.literal_eval(replacements)
                secured_pdf, today_date = generateProtectedPDF(CaseType, templateType, replacements)
                secured_pdf.seek(0)
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
                    download_name=templateType.replace(' ', '_') + ".pdf",
                    mimetype='application/pdf'
                )
            except Exception as e:
                return str(e), 500

@ns.route('/generate-template-pdf')
class GenerateProtectedPDF(Resource):
    @jwt_required()
    @ns.expect(GenerateProtectedPDFParams)
    def post(self):
        try:
            user_id = get_jwt_identity()
            CaseType = api.payload['CaseType']
            templateType = api.payload['templateType']
            replacements = api.payload['replacements']
            isOk, response, statusCode = checkUserBalance(user_id, CaseType, templateType, replacements)
            if not isOk:
                return response, statusCode
            secured_pdf, today_date = generateProtectedPDF(CaseType, templateType, replacements)
            secured_pdf.seek(0)
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
                download_name=templateType.replace(' ', '_') + ".pdf",
                mimetype='application/pdf'
            )
        except Exception as e:
            return str(e), 500

# GET Endpoint

@ns.route('/recharge')
class TableDataUserCreditRecharge(Resource):
    @jwt_required()
    def post(self):
        try:
            data = api.payload
            amount = data.get('amount')
            user = get_jwt_identity()
            payment_info, status_code = initiatePhonePePayment(user, amount)
            return payment_info, status_code
        except Exception as e:
            return {'message': 'Recharge failed', 'error': str(e)}, 500

@ns.route('/verify-payment/<string:transaction_id>')
class TableDataUserCreditRechargeStatus(Resource):
    @jwt_required()
    def get(self, transaction_id):
        try:
            payment_info, status_code = verify_payment(transaction_id)
            return payment_info, status_code
        except Exception as e:
            return {'message': 'Recharge failed', 'error': str(e)}, 500

@ns.route('/verify-payment-callback')
class TableDataUserCreditRechargeCallback(Resource):
    def post(self):
        try:
            transaction_id = request.form.get("transactionId") or request.args.get("transactionId")
            print(f"[API CALL] Verifying payment for {transaction_id}")
            if not transaction_id:
                return "Missing transactionId", 400
            # Redirect to frontend GET page
            return redirect(f"https://kagaz.ruaaventures.com/payment-status?transactionId={transaction_id}")
            return {'message': 'Request Created' }, 200
        except Exception as e:
            return {'message': 'Request Creation failed', 'error': str(e)}

@kn.route('/request-deletion')
class TableDeleteUserData(Resource):
    def post(self):
        try:
            data = api.payload
            res = requestDataDelete(data)
            return {'message': 'Request Created', 'id': res }, 200
        except Exception as e:
            return {'message': 'Request Failed', 'id': e }, 500
if __name__ == '__main__':
    app.run(debug=True)
