import psycopg2
from flask import current_app

def get_db_connection():
    try:
        return psycopg2.connect(
            host=current_app.config.get('DB_HOST'),
            database=current_app.config.get('DB_NAME'),
            user=current_app.config.get('DB_USER'),
            password=current_app.config.get('DB_PASSWORD'),
            port=current_app.config.get('DB_PORT')
        )
    except Exception as e:
        print("Database connection error:", e)
        return None
