from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from datetime import datetime

class MongoCRUD:
    def __init__(self, db_name="myDatabase", collection_name="user"):
        try:
            self.client = MongoClient("mongodb://localhost:27017/")
            self.client.admin.command('ping')
            print("Connected to MongoDB successfully")
            self.db = self.client[db_name]
            self.collection = self.db[collection_name]
        except ConnectionFailure:
            print("Failed to connect to MongoDB")
            
    # CREATE Operations
    def create_one(self, document):
        result = self.collection.insert_one(document)
        print(f"Document inserted with id: {result.inserted_id}")
        return result.inserted_id

    def create_many(self, documents):
        result = self.collection.insert_many(documents)
        print(f"{len(result.inserted_ids)} documents inserted.")
        return result.inserted_ids

    # READ Operations
    def read_all(self):
        """Return list of all documents as dictionaries"""
        documents = list(self.collection.find())
        return documents

    def read_one(self, query):
        document = self.collection.find_one(query)
        if document:
            print(f"Document Found: {document}")
        else:
            print("No Document matches the query")
        return document

    def read_many(self, query):
        documents = list(self.collection.find(query))
        print(f"{len(documents)} documents found.")
        for doc in documents:
            print(doc)
        return documents

    # UPDATE Operations
    def update_one(self, query, new_values):
        result = self.collection.update_one(query, {'$set': new_values})
        print(f"Matched {result.matched_count}, Modified {result.modified_count}")
        return result

    def update_many(self, query, new_values):
        result = self.collection.update_many(query, {'$set': new_values})
        print(f"Matched {result.matched_count}, Modified {result.modified_count}")
        return result

    # DELETE Operations
    def delete_one(self, query):
        result = self.collection.delete_one(query)
        print(f"Deleted {result.deleted_count} document.")
        return result

    def delete_many(self, query):
        result = self.collection.delete_many(query)
        print(f"Deleted {result.deleted_count} documents.")
        return result

    def delete_all(self):
        result = self.collection.delete_many({})
        print(f"Deleted {result.deleted_count} documents.")
        return result

    def close_connection(self):
        self.client.close()
        print("Connection closed successfully")


if __name__ == "__main__":
    mongo_db = MongoCRUD(db_name="testDB", collection_name="students")

    while True:
        print("\n" + "="*40)
        print(" MongoDB CRUD MENU ")
        print("="*40)
        print("1. Insert One Student")
        print("2. Insert Multiple Students")
        print("3. Read All Students")
        print("4. Read One Student")
        print("5. Update One Student")
        print("6. Delete One Student")
        print("7. Delete All Students")
        print("0. Exit")

        choice = input("Enter choice: ")

        if choice == "1":
            student = {
                "name": input("Name: "),
                "age": int(input("Age: ")),
                "city": input("City: "),
                "email": input("Email: "),
                "created_at": datetime.now()
            }
            mongo_db.create_one(student)

        elif choice == "2":
            students = [
                {"name": "Ali", "age": 22, "city": "Lahore"},
                {"name": "Sara", "age": 21, "city": "Islamabad"},
                {"name": "Bilal", "age": 22, "city": "Faisalabad"}
            ]
            mongo_db.create_many(students)

        elif choice == "3":
            students = mongo_db.read_all()
            for student in students:
                print(student)

        elif choice == "4":
            name = input("Enter name to search: ")
            student = mongo_db.read_one({"name": name})
            if student:
                print(student)

        elif choice == "5":
            name = input("Enter name to update: ")
            new_age = int(input("New Age: "))
            mongo_db.update_one({"name": name}, {"age": new_age})

        elif choice == "6":
            name = input("Enter name to delete: ")
            mongo_db.delete_one({"name": name})

        elif choice == "7":
            mongo_db.delete_all()

        elif choice == "0":
            mongo_db.close_connection()
            break

        else:
            print("❌ Invalid choice")
