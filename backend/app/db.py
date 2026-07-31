import pymongo
from app.config import MONGO_URI, MONGO_DATABASE

_client = None


def get_db():
    global _client
    if _client is None:
        _client = pymongo.MongoClient(MONGO_URI)
    return _client[MONGO_DATABASE]
