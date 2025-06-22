import json

from connect_db import getConnection

def requestDataDelete(payload):
    print("Payload:", payload)  # Debug print
    conn = getConnection()
    cur = conn.cursor()
    insert_query = """
        INSERT INTO request_deletion (name, email, contact, apptype)
        VALUES (%s, %s, %s, %s)
        RETURNING ID;
    """
    print("SQL Query:", insert_query)

    try:
        cur.execute(insert_query, (
            payload['name'],
            payload['email'],
            payload['contact'],
            payload['app_type']
        ))
        app_id = cur.fetchone()[0]
        conn.commit()
        print("Insert Successful. ID:", app_id)
        return {"id": app_id}
    except Exception as e:
        print("DB Error:", str(e))
        return {"error": str(e)}
    finally:
        cur.close()
        conn.close()


