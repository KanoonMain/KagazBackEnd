import psycopg2
def getConnection():
    # Build connection string
    db_params = {
        "host": "kanoon-dev.cn0qwqy6wred.eu-north-1.rds.amazonaws.com",
        "port": 5432,
        "database": "postgres",
        "user": "kanoon",
        "password": "XwVebVtUUtAiiE4jYv9l"
    }
    conn = psycopg2.connect(
        dbname=db_params['database'],
        user=db_params['user'],
        password=db_params['password'],
        host=db_params['host'],
        port=db_params['port']
    )
    return conn
