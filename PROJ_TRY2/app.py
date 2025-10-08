# --- app.py (Stable Version) ---
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import mysql.connector
from PIL import Image
import os
from datetime import datetime
import requests
import base64
import io
from werkzeug.datastructures import FileStorage

# --- CONFIGURATION ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

DB_CONFIG = {
    'host': 'localhost', 'user': 'root',
    'password': 'krishna22', 'database': 'memory_vault_db'
}
# NOTE: AI Captioning is kept, as it does not slow down the server.
GOOGLE_API_KEY = "AIzaSyBO4qx31mCuWZaNwZiInGkK6dvUUZFCAEs"
MODEL_NAME = "models/gemini-2.5-flash"
API_ENDPOINT = f"https://generativelanguage.googleapis.com/v1/{MODEL_NAME}:generateContent?key={GOOGLE_API_KEY}"

## --- HELPER FUNCTIONS ---
def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def get_caption_from_gemini(file_storage) -> str:
    print("Preparing image for direct API call...")
    try:
        file_storage.stream.seek(0)
        img = Image.open(file_storage.stream).convert('RGB')
        byte_arr = io.BytesIO()
        img.save(byte_arr, format='JPEG')
        encoded_image = base64.b64encode(byte_arr.getvalue()).decode('utf-8')
        payload = {"contents": [{"parts": [{"text": "Describe this image in one descriptive sentence."}, {"inline_data": {"mime_type": "image/jpeg", "data": encoded_image}}]}]}
        headers = {'Content-Type': 'application/json'}
        print("Sending request to Gemini API...")
        response = requests.post(API_ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"Error in get_caption_from_gemini: {e}")
        return "Caption generation failed."

## --- UI ROUTES (Pages) ---

@app.route('/')
def login_page():
    return render_template('login.html')

@app.route('/home')
def home_page():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM memories ORDER BY memory_date DESC LIMIT 5")
    memories = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', memories=memories)

@app.route('/gallery')
def gallery_page():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT m.memory_id, m.title, med.source_url FROM media med JOIN memories m ON med.memory_id = m.memory_id ORDER BY m.memory_date DESC")
    media_items = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('gallery.html', media_items=media_items)

@app.route('/search', methods=['GET', 'POST'])
def search_page():
    search_term = request.form.get('search', '') if request.method == 'POST' else ''
    results = []
    if search_term:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT DISTINCT m.* FROM memories m
            LEFT JOIN media med ON m.memory_id = med.memory_id
            LEFT JOIN ai_analysis anl ON med.media_id = anl.media_id
            WHERE m.title LIKE %s OR m.description LIKE %s OR anl.generated_caption LIKE %s
        """
        search_pattern = f"%{search_term}%"
        cursor.execute(query, (search_pattern, search_pattern, search_pattern))
        results = cursor.fetchall()
        cursor.close()
        conn.close()
    return render_template('search.html', results=results, search_term=search_term)

@app.route('/add')
def add_memory_page():
    return render_template('add_memory.html')

@app.route('/memory/<int:memory_id>')
def memory_detail_page(memory_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT m.*, med.source_url, anl.generated_caption FROM memories m LEFT JOIN media med ON m.memory_id = med.memory_id LEFT JOIN ai_analysis anl ON med.media_id = anl.media_id WHERE m.memory_id = %s", (memory_id,))
    memory = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('memory_detail.html', memory=memory)

## --- ACTION ROUTES (Handle Forms) ---

@app.route('/login_action', methods=['POST'])
def login_action():
    return redirect(url_for('home_page'))

@app.route('/add_memory_action', methods=['POST'])
def add_memory_action():
    conn = None
    try:
        title = request.form['title']
        description = request.form['description']
        memory_date = request.form['date']
        image_file = request.files['image']
        
        # Secure the filename before saving
        from werkzeug.utils import secure_filename
        filename = secure_filename(image_file.filename)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Save file to the filesystem
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(image_path)
        
        cursor.execute("INSERT INTO memories (patient_id, title, description, memory_date) VALUES (1, %s, %s, %s)", (title, description, memory_date))
        new_memory_id = cursor.lastrowid
        
        caption = get_caption_from_gemini(image_file)
        
        cursor.execute("INSERT INTO media (memory_id, media_type, source_url, creation_time) VALUES (%s, 'photo', %s, NOW())", (new_memory_id, filename))
        new_media_id = cursor.lastrowid
        
        cursor.execute("INSERT INTO ai_analysis (media_id, generated_caption) VALUES (%s, %s)", (new_media_id, caption))
        conn.commit()
    except Exception as e:
        print(f"An error occurred: {e}")
        if conn: conn.rollback()
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('home_page'))

@app.route('/delete_memory/<int:memory_id>', methods=['POST'])
def delete_memory(memory_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # First, get the filename to delete it from the filesystem
    cursor.execute("SELECT source_url FROM media WHERE memory_id = %s", (memory_id,))
    result = cursor.fetchone()
    if result:
        filename = result[0]
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(image_path):
            os.remove(image_path)
    # The database will cascade delete the media and ai_analysis rows
    cursor.execute("DELETE FROM memories WHERE memory_id = %s", (memory_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('home_page'))

# --- Run the Server ---
if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True, port=5000)