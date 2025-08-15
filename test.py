# test_db.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+psycopg2://admin:admin@localhost:5432/doctor_app"

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        print("✅ Database connection successful!")
        result = connection.execute(text("SELECT 1"))
        for row in result:
            print(f"PostgreSQL responded with: {row[0]}")
except Exception as e:
    print("❌ Database connection failed!")
    print(f"Error: {e}")