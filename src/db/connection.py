import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     os.getenv("DB_PORT", 5432),
    "dbname":   os.getenv("DB_NAME", "bcb_dashboard"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}


def get_connection():
    """Retorna uma conexão psycopg2 com o PostgreSQL."""
    return psycopg2.connect(**DB_CONFIG)


def get_dict_connection():
    """Retorna conexão com cursor que devolve dicionários (útil para pandas)."""
    conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
    return conn