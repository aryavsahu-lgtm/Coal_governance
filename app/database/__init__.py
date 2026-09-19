from app.database.mongo import mongo, MongoDB
from app.database.indexes import create_indexes

__all__ = ["mongo", "MongoDB", "create_indexes"]
