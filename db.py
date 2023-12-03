from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

SQL_DB_URL="sqlite:///./student.db"

engine = create_engine(SQL_DB_URL,connect_args={"check_same_thread":False})

SessionLocal = sessionmaker(autocommit=False,autoflush=False,bind=False)

Base = declarative_base()