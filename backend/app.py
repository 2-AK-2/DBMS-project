# --- app.py ---
from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
from PIL import Image
import os
from datetime import datetime
import requests
import base64
import io

# --- Initialize Flask App ---
app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing

# --- CONFIGURATION (Copy from your other script) ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'krishna22',  # Make sure this is your correct password
    'database': 'memory_vault_db'
}

GOOGLE_API_KEY = "AIzaSyBO4qx31mCuWZaNwZiInGkK6dvUUZFCAEs" # Your API Key
MODEL_NAME = "models/gemini-2.5-flash"
API_ENDPOINT = f"https://generativelanguage.googleapis.com/v1/{MODEL_NAME}:generateContent?key={GOOGLE_API_KEY}"


## --- Re-usable Functions (from your previous script) ---

def get_caption_from_gemini(file_path: str) -> str:
    # (This function is the same as before)
    # ... (code omitted for brevity, but it's the same logic)
    # ... It should handle the image analysis and return a caption.
    pass # Placeholder

def analyze_and_store_media(file_path: str, memory_id: int):
    # (This function is the same as before)
    # ... (code omitted for brevity, but it's the same logic)
    # ... It should store media and analysis in the DB.
    pass # Placeholder


## --- API Endpoints ---

@app.route('/login', methods=['POST'])
def login():
    # Note: This is a placeholder for actual login logic.
    # In a real app, you would verify email/password against the 'users' table.
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    print(f"Login attempt for: {email}") # For debugging
    # For now, we'll just return success.
    return jsonify({"message": "Login successful"}), 200


@app.route('/memories', methods=['GET'])
def get_memories():
    # This endpoint fetches all memories from the database.
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor(dictionary=True) # dictionary=True returns rows as dicts
        
        query = "SELECT memory_id as id, title, memory_date as date FROM memories ORDER BY memory_date DESC"
        cursor.execute(query)
        memories = cursor.fetchall()
        
        return jsonify(memories), 200
        
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    finally:
        if 'db_connection' in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


@app.route('/memories', methods=['POST'])
def add_memory():
    # This endpoint handles creating a new memory.
    # It expects form data with title, description, date, etc.
    # and an uploaded file.
    try:
        # 1. Save the uploaded file temporarily
        file = request.files['image']
        temp_path = os.path.join("temp_uploads", file.filename)
        file.save(temp_path)

        # 2. Get other form data
        memory_data = request.form
        title = memory_data.get('title')
        description = memory_data.get('description')
        memory_date = memory_data.get('date')
        
        # 3. Insert the main memory record first
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()
        
        memory_sql = "INSERT INTO memories (patient_id, title, description, memory_date) VALUES (%s, %s, %s, %s)"
        # Assuming patient_id 1 for now
        cursor.execute(memory_sql, (1, title, description, memory_date))
        new_memory_id = cursor.lastrowid
        
        db_connection.commit() # Commit this first to get the ID

        # 4. Now, call your existing function to analyze and store the media
        # This will link the media to the new_memory_id
        analyze_and_store_media(temp_path, new_memory_id)
        
        return jsonify({"message": "Memory added successfully", "memory_id": new_memory_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Clean up the temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if 'db_connection' in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


# --- Run the Server ---
if __name__ == '__main__':
    # Create a temporary folder for uploads if it doesn't exist
    if not os.path.exists("temp_uploads"):
        os.makedirs("temp_uploads")
    app.run(debug=True, port=5000)