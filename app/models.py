from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson import ObjectId
import os
from dotenv import load_dotenv

# Load env variables
load_dotenv()

class MongoCRUD:
    def __init__(self):
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGO_DB", "testDB")
        collection_name = os.getenv("MONGO_COLLECTION", "students")

        try:
            self.client = MongoClient(mongo_uri)
            self.client.admin.command('ping')
            print("Connected to MongoDB successfully")
            self.db = self.client[db_name]
            self.collection = self.db[collection_name]
            self.user_collection = self.db["users"]
        except ConnectionFailure:
            print("Failed to connect to MongoDB")

    # --- STUDENT CRUD ---
    def create_one(self, document):
        return self.collection.insert_one(document).inserted_id

    def create_many(self, documents):
        return self.collection.insert_many(documents).inserted_ids

    def read_all(self):
        return list(self.collection.find())

    def read_one(self, query):
        return self.collection.find_one(query)

    def read_many(self, query):
        return list(self.collection.find(query))

    def update_one(self, query, new_values):
        return self.collection.update_one(query, {'$set': new_values})

    def delete_one(self, query):
        return self.collection.delete_one(query)

    def delete_many(self, query):
        return self.collection.delete_many(query)

    def delete_all(self):
        return self.collection.delete_many({})

    # --- USER AUTH ---
    def create_user(self, user_doc):
        return self.user_collection.insert_one(user_doc).inserted_id

    def find_user(self, query):
        return self.user_collection.find_one(query)
