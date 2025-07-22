"""Database initialization module."""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# Create the database instance that will be shared
db = SQLAlchemy(model_class=Base)