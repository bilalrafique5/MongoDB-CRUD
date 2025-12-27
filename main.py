from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from datetime import datetime
from bson import ObjectId

class MongoCRUD:
    def __init__(self, db_name="myDatabase", collection_name="students"):
        try:
            self.client = MongoClient("mongodb://localhost:27017/")
            self.client.admin.command('ping')
            print("Connected to MongoDB successfully")
            self.db = self.client[db_name]
            self.collection = self.db[collection_name]
            self.user_collection = self.db["users"]  # separate collection for auth users
        except ConnectionFailure:
            print("Failed to connect to MongoDB")

    # --- STUDENT CRUD ---
    def create_one(self, document):
        result = self.collection.insert_one(document)
        return result.inserted_id

    def create_many(self, documents):
        result = self.collection.insert_many(documents)
        return result.inserted_ids

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

    def delete_all(self):
        return self.collection.delete_many({})

    # --- USER AUTH ---
    def create_user(self, user_doc):
        """user_doc: {username, email, password}"""
        return self.user_collection.insert_one(user_doc).inserted_id

    def find_user(self, query):
        return self.user_collection.find_one(query)
    
    def close_connection(self):
        self.client.close()
