from connect_db import getConnection
from flask_jwt_extended import create_access_token
from flask import jsonify


# from flask_mail import Mail, Message
# from itsdangerous import URLSafeTimedSerializer
# serializer = URLSafeTimedSerializer("your-secret-key")


def userCredits(id):
    conn = getConnection()
    cursor = conn.cursor()
    cursor.execute("SELECT credits FROM template.users WHERE id = %s;", (id,))
    credits = cursor.fetchone()[0]
    return {"credits": credits}, 200


def rechargeCredits(id, amount):
    conn = getConnection()
    cursor = conn.cursor()
    if not isinstance(amount, int) or amount <= 0:
        return {'message': 'Invalid recharge amount'}, 400
    try:
        # Start transaction
        cursor.execute("""
            UPDATE template.users
            SET credits = credits + %s
            WHERE id = %s
            RETURNING credits;
        """, (amount, id))

        result = cursor.fetchone()
        if not result:
            return {'message': 'User not found'}, 404

        updated_credits = result[0]

        # Insert recharge history
        cursor.execute("""
            INSERT INTO template.recharge_history (user_id, amount)
            VALUES (%s, %s);
        """, (id, amount))

        conn.commit()
        return {'message': 'Credits recharged successfully', 'credits': updated_credits}, 200
    except Exception as e:
        conn.rollback()
        return {'message': 'Error Occurred: ' + str(e)}, 400
    finally:
        cursor.close()
        conn.close()


def userRegister(email, password, bcrypt):
    conn = getConnection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM template.users WHERE email = %s;", (email,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return {'message': 'User already exists'}, 400
    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
    cursor.execute(
        "INSERT INTO template.users (email, password, credits) VALUES (%s, %s, %s);",
        (email, hashed_pw, 0)
    )
    conn.commit()  # ✅ Commit the transaction to save the data
    cursor.close()
    conn.close()
    # send_confirmation_email(email)  # Uncomment if email confirmation is implemented
    return {'message': 'Registered. Check your email to confirm.'}, 201


def userLogin(email, password, bcrypt):
    conn = getConnection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, password FROM template.users WHERE email = %s;", (email,))
    result = cursor.fetchone()
    if result is None:
        return {'message': 'User not found'}, 404
    user_id, hashed_password = result
    if not bcrypt.check_password_hash(hashed_password, password):
        return {'message': 'Incorrect password'}, 401
    token = create_access_token(identity=str(user_id), additional_claims={"email": email})
    return {'message': 'Login successful', "token": token}, 200


def userUpdatePassword(email, oldPass, newPass, bcrypt):
    conn = getConnection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT password FROM template.users WHERE email = %s", (email,))
        result = cur.fetchone()
        if not result:
            return {"error": "User not found"}, 404
        if not bcrypt.check_password_hash(result[0], oldPass):
            return {"error": "Old password incorrect"}, 401
        hashed_pw = bcrypt.generate_password_hash(newPass).decode('utf-8')
        cur.execute("UPDATE template.users SET password = %s WHERE email = %s", (hashed_pw, email))
        conn.commit()
        return {"message": "Password updated successfully"}, 200
    except Exception as e:
        print("Error updating password:", e)
        conn.rollback()
        return {"error": "Internal server error"}, 500
    finally:
        cur.close()
        conn.close()

def userOrderRegenerate(userId, orderId):
    conn = getConnection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT case_type, template_type, payload
        FROM template.orders
        WHERE user_id={userId} and id={orderId}
    """)
    result = cursor.fetchone()
    case_type, template_type, payload = result
    return case_type, template_type, payload


def userOrders(user_id):
    conn = getConnection()
    cur = conn.cursor()
    try:
        cur.execute(f"""
            SELECT id, created_at, case_type, template_type, price
            FROM template.orders
            WHERE user_id={user_id}
            ORDER BY id DESC
        """)
        rows = cur.fetchall()
        orders = [
            {
                "id": row[0],
                "created_at": row[1].strftime("%Y-%m-%d %H:%M"),
                "case_type": row[2],
                "template_type": row[3],
                "price": str(row[4]),
            }
            for row in rows
        ]
        return {"orders": orders }, 200
    except Exception as e:
        print("Error fetching orders:", e)
        return {"error": "Internal server error"}, 500
    finally:
        cur.close()
        conn.close()

# def send_confirmation_email(user_email):
#     token = serializer.dumps(user_email, salt='email-confirm')
#     link = url_for('confirm_email', token=token, _external=True)
#     msg = Message('Confirm Your Email', sender='test@gmail.com', recipients=[user_email])
#     msg.body = f'Click the link to confirm your email: {link}'
#     mail.send(msg)

if __name__ == '__main__':
    from flask_bcrypt import Bcrypt

    bcrypt = Bcrypt()
    userLogin("sagarsanjeev24@gmail.com", "123", bcrypt)
