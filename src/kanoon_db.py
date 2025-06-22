from connect_db import getConnection

def requestDataDelete(payload):
    conn = getConnection()
    cur = conn.cursor()
    insert_query = """
               INSERT INTO Applications (Name, Email, Contact, AppType, isCompleted)
               VALUES (%s, %s, %s, %s, %s)
               RETURNING ID;
           """
    cur.execute(insert_query, (payload['name'], payload['email'], payload['contact'], payload['app_type'], payload['is_completed']))
    app_id = cur.fetchone()[0]
    conn.commit()
    return app_id

