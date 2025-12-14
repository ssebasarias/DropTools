
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

user = os.getenv("POSTGRES_USER", "dahell_admin")
pwd = os.getenv("POSTGRES_PASSWORD", "secure_password_123")
host = "127.0.0.1"
port = os.getenv("POSTGRES_PORT", "5433")
dbname = os.getenv("POSTGRES_DB", "dahell_db")
url = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{dbname}"

print(f"Password used: '{pwd}'")
try:
    # Usar UTF-8 consistentemente
    engine = create_engine(url, connect_args={'client_encoding': 'UTF8'})
    with engine.connect() as conn:
        print("Connected.")
        try:
            conn.execute(text("INSERT INTO categories (name) VALUES (:n)"), {"n": "Prueba ó"})
            conn.commit()
            print("Inserted ó successfully.")
        except Exception as e:
            print(f"Insert failed: {e}")
except Exception as e:
    print(f"Connection failed: {e}")
