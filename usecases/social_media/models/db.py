import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

_client = None
_db = None

def get_db():
    """Get database connection, creating it if necessary."""
    global _client, _db

    if _db is not None:
        return _db

    docdb_uri = os.getenv('DOCDB_URI')
    if not docdb_uri:
        raise ValueError('DOCDB_URI environment variable not set')

    _client = MongoClient(docdb_uri)
    _db = _client.social

    return _db

def close_db():
    """Close database connection."""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
