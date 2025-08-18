import psycopg2

DB_HOST = "localhost"
DB_NAME = "Heritage"
DB_USER = "postgres"
DB_PASSWORD = "adakjitu"
DB_PORT = "5432"

WEEK_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )
