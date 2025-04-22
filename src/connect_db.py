import psycopg2


def getConnection():
    db_params = {
        "host": "kanoon-dev.cn0qwqy6wred.eu-north-1.rds.amazonaws.com",
        "port": 5432,
        "database": "postgres",
        "user": "kanoon",
        "password": "XwVebVtUUtAiiE4jYv9l"
    }
    conn = psycopg2.connect(**db_params)
    return conn
