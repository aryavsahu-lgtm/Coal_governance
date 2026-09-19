import logging
import re
from datetime import datetime
from bson import ObjectId
import pymongo
from pymongo.errors import ConnectionFailure, OperationFailure, ServerSelectionTimeoutError
from app.config import Config

logger = logging.getLogger("coal_governance.database")


class MockCursor:
    """Mock cursor for fallback in-memory database."""

    def __init__(self, items):
        self.items = list(items)

    def __iter__(self):
        return iter(self.items)

    def sort(self, key_or_list, direction=None):
        if isinstance(key_or_list, str):
            key = key_or_list
            reverse = (direction == pymongo.DESCENDING or direction == -1)
        elif isinstance(key_or_list, list) and key_or_list:
            key = key_or_list[0][0]
            reverse = (key_or_list[0][1] == pymongo.DESCENDING or key_or_list[0][1] == -1)
        else:
            return self

        def sort_val(x):
            val = x.get(key)
            return (val is not None, val if val is not None else "")

        self.items.sort(key=sort_val, reverse=reverse)
        return self

    def limit(self, n):
        self.items = self.items[:n]
        return self

    def skip(self, n):
        self.items = self.items[n:]
        return self


class MockCollection:
    """In-memory collection emulator providing PyMongo-compatible CRUD for graceful fallback."""

    def __init__(self, name):
        self.name = name
        self.docs = []

    def _matches(self, doc, query):
        if not query:
            return True
        for k, v in query.items():
            if k == "$or" and isinstance(v, list):
                if not any(self._matches(doc, cond) for cond in v):
                    return False
                continue
            if k == "$and" and isinstance(v, list):
                if not all(self._matches(doc, cond) for cond in v):
                    return False
                continue
            if k == "_id":
                if str(doc.get("_id")) != str(v):
                    return False
            elif isinstance(v, dict):
                val = doc.get(k)
                if "$in" in v and val not in v["$in"]:
                    return False
                if "$nin" in v and val in v["$nin"]:
                    return False
                if "$gte" in v and not (val is not None and val >= v["$gte"]):
                    return False
                if "$lte" in v and not (val is not None and val <= v["$lte"]):
                    return False
                if "$gt" in v and not (val is not None and val > v["$gt"]):
                    return False
                if "$lt" in v and not (val is not None and val < v["$lt"]):
                    return False
                if "$ne" in v and val == v["$ne"]:
                    return False
                if "$regex" in v:
                    flags = re.IGNORECASE if "i" in v.get("$options", "") else 0
                    if not re.search(v["$regex"], str(val or ""), flags):
                        return False
            elif doc.get(k) != v:
                return False
        return True

    def insert_one(self, doc):
        new_doc = dict(doc)
        if "_id" not in new_doc:
            new_doc["_id"] = ObjectId()
        self.docs.append(new_doc)
        return type("InsertResult", (), {"inserted_id": new_doc["_id"]})()

    def insert_many(self, docs):
        inserted_ids = []
        for d in docs:
            res = self.insert_one(d)
            inserted_ids.append(res.inserted_id)
        return type("InsertManyResult", (), {"inserted_ids": inserted_ids})()

    def find_one(self, query=None, projection=None):
        query = query or {}
        for d in self.docs:
            if self._matches(d, query):
                return dict(d)
        return None

    def find(self, query=None, projection=None):
        query = query or {}
        matching = [dict(d) for d in self.docs if self._matches(d, query)]
        return MockCursor(matching)

    def count_documents(self, query=None):
        query = query or {}
        return sum(1 for d in self.docs if self._matches(d, query))

    def update_one(self, query, update, upsert=False):
        for i, d in enumerate(self.docs):
            if self._matches(d, query):
                if "$set" in update:
                    self.docs[i].update(update["$set"])
                if "$inc" in update:
                    for ik, iv in update["$inc"].items():
                        self.docs[i][ik] = self.docs[i].get(ik, 0) + iv
                return type("UpdateResult", (), {"matched_count": 1, "modified_count": 1, "upserted_id": None})()
        if upsert:
            new_doc = dict(query)
            if "$set" in update:
                new_doc.update(update["$set"])
            if "_id" not in new_doc:
                new_doc["_id"] = ObjectId()
            self.docs.append(new_doc)
            return type("UpdateResult", (), {"matched_count": 0, "modified_count": 1, "upserted_id": new_doc["_id"]})()
        return type("UpdateResult", (), {"matched_count": 0, "modified_count": 0, "upserted_id": None})()

    def update_many(self, query, update, upsert=False):
        matched = 0
        for i, d in enumerate(self.docs):
            if self._matches(d, query):
                matched += 1
                if "$set" in update:
                    self.docs[i].update(update["$set"])
                if "$inc" in update:
                    for ik, iv in update["$inc"].items():
                        self.docs[i][ik] = self.docs[i].get(ik, 0) + iv
        if matched == 0 and upsert:
            new_doc = dict(query)
            if "$set" in update:
                new_doc.update(update["$set"])
            if "_id" not in new_doc:
                new_doc["_id"] = ObjectId()
            self.docs.append(new_doc)
            return type("UpdateResult", (), {"matched_count": 0, "modified_count": 1, "upserted_id": new_doc["_id"]})()
        return type("UpdateResult", (), {"matched_count": matched, "modified_count": matched, "upserted_id": None})()

    def delete_one(self, query):
        for i, d in enumerate(self.docs):
            if self._matches(d, query):
                del self.docs[i]
                return type("DeleteResult", (), {"deleted_count": 1})()
        return type("DeleteResult", (), {"deleted_count": 0})()

    def delete_many(self, query):
        before = len(self.docs)
        self.docs = [d for d in self.docs if not self._matches(d, query)]
        return type("DeleteResult", (), {"deleted_count": before - len(self.docs)})()

    def create_index(self, keys, **kwargs):
        return "mock_idx"

    def aggregate(self, pipeline):
        # Basic aggregation handling for analytics
        results = list(self.docs)
        for stage in pipeline:
            if "$match" in stage:
                results = [d for d in results if self._matches(d, stage["$match"])]
            elif "$group" in stage:
                group_id_key = stage["$group"].get("_id")
                groups = {}
                for d in results:
                    gid = d.get(group_id_key.replace("$", "")) if isinstance(group_id_key, str) and group_id_key.startswith("$") else None
                    if gid not in groups:
                        groups[gid] = {"_id": gid, "count": 0}
                    groups[gid]["count"] += 1
                results = list(groups.values())
            elif "$sort" in stage:
                pass
            elif "$limit" in stage:
                results = results[:stage["$limit"]]
        return results


class MockDatabase:
    """In-memory database emulator used when MongoDB server is offline or authentication fails."""

    def __init__(self, name):
        self.name = name
        self.collections = {}

    def __getitem__(self, item):
        if item not in self.collections:
            self.collections[item] = MockCollection(item)
        return self.collections[item]

    def list_collection_names(self):
        return list(self.collections.keys())


class MongoDB:
    """
    Central MongoDB client singleton with Atlas/Local support,
    automatic connection pooling, resilience, and graceful fallback.
    """

    _instance = None
    _client = None
    _db = None
    _is_mock = False
    _connection_error = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDB, cls).__new__(cls)
            cls._instance._init_connection()
        return cls._instance

    def _init_connection(self):
        uri = Config.MONGODB_URI.strip() if Config.MONGODB_URI else ""
        db_name = Config.MONGODB_DATABASE

        if not uri:
            logger.warning("[MongoDB] No MONGODB_URI configured in environment. Using in-memory fallback store.")
            self._is_mock = True
            self._db = MockDatabase(db_name)
            self._connection_error = "MONGODB_URI is empty"
            return

        try:
            logger.info(f"[MongoDB] Attempting connection to MongoDB database '{db_name}'...")
            client = pymongo.MongoClient(
                uri,
                serverSelectionTimeoutMS=3500,
                connectTimeoutMS=3500,
                retryWrites=True,
                w="majority"
            )
            # Ping database to verify authentication and reachability
            client.admin.command("ping")
            self._client = client
            self._db = client[db_name]
            self._is_mock = False
            self._connection_error = None
            logger.info(f"[MongoDB] Successfully connected to MongoDB database '{db_name}'.")
        except (OperationFailure, ServerSelectionTimeoutError, ConnectionFailure, Exception) as e:
            self._client = None
            self._is_mock = True
            self._db = MockDatabase(db_name)
            self._connection_error = str(e)
            logger.warning(
                f"[MongoDB Warning] Could not connect to remote MongoDB ({e}). "
                "Operating in resilient fallback mode so application startup succeeds. "
                "Update MONGODB_URI with valid Atlas credentials in .env when ready."
            )

    @property
    def db(self):
        return self._db

    @property
    def client(self):
        return self._client

    @property
    def is_mock(self):
        return self._is_mock

    @property
    def connection_error(self):
        return self._connection_error

    def reconnect(self):
        """Forces a reconnect check after .env update."""
        self._init_connection()
        return not self._is_mock

    # Collection accessors
    @property
    def users(self):
        return self._db["users"]

    @property
    def subsidiaries(self):
        return self._db["subsidiaries"]

    @property
    def mines(self):
        return self._db["mines"]

    @property
    def zones(self):
        return self._db["zones"]

    @property
    def compliance_requirements(self):
        return self._db["compliance_requirements"]

    @property
    def inspections(self):
        return self._db["inspections"]

    @property
    def field_reports(self):
        return self._db["field_reports"]

    @property
    def violations(self):
        return self._db["violations"]

    @property
    def incidents(self):
        return self._db["incidents"]

    @property
    def corrective_actions(self):
        return self._db["corrective_actions"]

    @property
    def contractors(self):
        return self._db["contractors"]

    @property
    def documents(self):
        return self._db["documents"]

    @property
    def notifications(self):
        return self._db["notifications"]

    @property
    def audit_logs(self):
        return self._db["audit_logs"]

    @property
    def rules(self):
        return self._db["rules"]

    @property
    def risk_scores(self):
        return self._db["risk_scores"]

    @property
    def analytics(self):
        return self._db["analytics"]

    @property
    def chatbot_documents(self):
        return self._db["chatbot_documents"]


# Global database accessor
mongo = MongoDB()
