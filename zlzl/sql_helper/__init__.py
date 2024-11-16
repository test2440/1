import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

# the secret configuration specific things
from ..Config import Config
from ..core.logger import logging

LOGS = logging.getLogger(__name__)

BASE = declarative_base()

def start() -> scoped_session:
    if Config.DB_URI is None:
        LOGS.error("DB_URI is not configured. Features depending on the database might have issues.")
        raise ValueError("DB_URI is not configured.")  # يمكن إضافة هذا لإيقاف التنفيذ إذا لم تكن القيمة موجودة

    database_url = (
        Config.DB_URI.replace("postgres:", "postgresql:")
        if "postgres://" in Config.DB_URI
        else Config.DB_URI
    )

    try:
        engine = create_engine(database_url)
        BASE.metadata.bind = engine
        BASE.metadata.create_all(engine)
        return scoped_session(sessionmaker(bind=engine, autoflush=False))
    except Exception as e:
        LOGS.error(f"Failed to create engine: {e}")
        raise

try:
    SESSION = start()
except AttributeError as e:
    LOGS.error("Failed to start the session due to AttributeError.")
    LOGS.error(str(e))
