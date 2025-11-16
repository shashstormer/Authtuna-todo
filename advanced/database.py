import os

import motor.motor_asyncio
import dotenv
dotenv.load_dotenv(os.getenv("ENV_FILE_PATH"))

# Create a client to connect to MongoDB
client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGO_CONNECTION_STRING", "mongodb://localhost:27017"))

# Get our application's database
# This does not use authtuna's db_manager
db = client[os.getenv("MONGO_DATABASE_NAME", "authtuna_todo_app")]

# Get a handle to our 'todos' collection
TodoCollection = db.get_collection("todos")
