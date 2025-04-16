import sqlite3

def getConnection():
    db_path = r'template.db'
    conn = sqlite3.connect(db_path)
    return conn


