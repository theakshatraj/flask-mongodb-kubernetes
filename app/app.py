
from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime
import os

# Initialize Flask application
app = Flask(__name__)

# Read MongoDB connection string from environment
MONGODB_URI = os.environ.get(
    "MONGODB_URI",
    "mongodb://localhost:27017/"
)

# Connect to MongoDB
client = MongoClient(
    MONGODB_URI,
    serverSelectionTimeoutMS=5000
)

# Select database and collection
db = client.flask_db
collection = db.data


# Root endpoint
@app.route("/", methods=["GET"])
def index():
    return (
        f"Welcome to the Flask app! "
        f"The current time is: {datetime.now()}"
    )


# Data endpoint
@app.route("/data", methods=["GET", "POST"])
def data():

    if request.method == "POST":

        document = request.get_json(silent=True)

        if not isinstance(document, dict):
            return jsonify({
                "error": "A valid JSON object is required"
            }), 400

        collection.insert_one(document)

        return jsonify({
            "status": "Data inserted"
        }), 201

    elif request.method == "GET":

        documents = list(
            collection.find({}, {"_id": 0})
        )

        return jsonify(documents), 200


# Run Flask application
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
