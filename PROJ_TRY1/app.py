# --- app.py (Rewritten & Completed) ---
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import mysql.connector
from PIL import Image
import os
from datetime import datetime
import requests
import base64
import io

# Import libraries for semantic search
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# --- Initialize Flask App ---
app = Flask(__name__)

# --- CONFIGURATION ---
# IMPORTANT: Use forward slashes '/' for the path, even on Windows.
LOCAL_IMAGE_DIRECTORY = 'C:/Users/User/Desktop/AK DOCUMENTS'

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'krishna22',
    'database': 'memory_vault_db'
}
GOOGLE_API_KEY = "AIzaSyBO4qx31mCuWZaNwZiInGkK6dvUUZFCAEs"
MODEL_NAME = "models/gemini-2.5-flash"
API_ENDPOINT = f"https://generativelanguage.googleapis.com/v1/{MODEL_NAME}:generateContent?key={GOOGLE_API_KEY}"

# --- LAZY LOADING FOR SEMANTIC MODEL ---
# This global variable will hold the model after it's loaded.
semantic_model = None

def get_semantic_model():
    """Loads the model if it hasn't been loaded yet, then returns it."""
    global semantic_model
    if semantic_model is None:
        print("Loading semantic search model for the first time...")
        # This line downloads the model when first called
        semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Semantic search model loaded.")
    return semantic_model

## --- HELPER FUNCTIONS ---
def get_db_connection():
    """Establishes a connection to the database."""
    return mysql.connector.connect(**DB_CONFIG)

def get_caption_from_gemini(file_storage) -> str:
    """Sends an image to the Google Gemini API and returns a caption."""
    print("Preparing image for direct API call...")
    try:
        img = Image.open(file_storage.stream)
        byte_arr = io.BytesIO()
        # Convert to RGB to ensure compatibility
        rgb_img = img.convert('RGB')
        rgb_img.save(byte_arr, format='JPEG')
        encoded_image = base64.b64encode(byte_arr.getvalue()).decode('utf-8')

        payload = { "contents": [{"parts": [{"text": "Describe this image in one descriptive sentence."}, {"inline_data": {"mime_type": "image/jpeg", "data": encoded_image}}]}]}
        headers = {'Content-Type': 'application/json'}
        
        print("Sending request to Gemini API...")
        response = requests.post(API_ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"Error in get_caption_from_gemini: {e}")
        return "Could not generate a caption for this image."

## --- UI ROUTES (Pages) ---

@app.route('/')
def login_page():
    return render_template('login.html')

@app.route('/home')
def home_page():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT memory_id, title, description, memory_date FROM memories ORDER BY memory_date DESC LIMIT 3")
    memories = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', memories=memories)

@app.route('/gallery')
def gallery_page():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT m.memory_id, m.title, med.source_url
        FROM media med JOIN memories m ON med.memory_id = m.memory_id
        ORDER BY m.memory_date DESC
    """)
    media_items = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('gallery.html', media_items=media_items, search_term='')

@app.route('/add')
def add_memory_page():
    return render_template('add_memory.html')

@app.route('/image_proxy/<path:filename>')
def image_proxy(filename):
    """Safely serves an image from your configured local directory."""
    return send_from_directory(LOCAL_IMAGE_DIRECTORY, filename)

@app.route('/memory/<int:memory_id>')
def memory_detail_page(memory_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT m.memory_id, m.title, m.description, m.memory_date, med.source_url, anl.generated_caption
        FROM memories m
        LEFT JOIN media med ON m.memory_id = med.memory_id
        LEFT JOIN ai_analysis anl ON med.media_id = anl.media_id
        WHERE m.memory_id = %s
    """, (memory_id,))
    memory = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('memory_detail.html', memory=memory)

@app.route('/search', methods=['GET', 'POST'])
def search_page():
    search_term = ''
    results = []
    if request.method == 'POST':
        search_term = request.form.get('search', '')
        if search_term:
            model = get_semantic_model() # Lazy-load the model
            
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT m.memory_id, m.title, m.description, m.memory_date, anl.generated_caption
                FROM memories m
                JOIN media med ON m.memory_id = med.memory_id
                JOIN ai_analysis anl ON med.media_id = anl.media_id
            """)
            all_memories = cursor.fetchall()
            cursor.close()
            conn.close()

            if all_memories:
                captions = [mem['generated_caption'] for mem in all_memories]
                query_embedding = model.encode([search_term])
                caption_embeddings = model.encode(captions)
                similarities = cosine_similarity(query_embedding, caption_embeddings)[0]
                
                for i, memory in enumerate(all_memories):
                    memory['similarity'] = similarities[i]
                
                results = sorted(all_memories, key=lambda x: x['similarity'], reverse=True)
                results = [mem for mem in results if mem['similarity'] > 0.3]

    return render_template('search.html', results=results, search_term=search_term)

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
        local_image_path = request.form['image_path']
        filename = os.path.basename(local_image_path)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("INSERT INTO memories (patient_id, title, description, memory_date) VALUES (%s, %s, %s, %s)", (1, title, description, memory_date))
        new_memory_id = cursor.lastrowid

        with open(local_image_path, 'rb') as f:
            from werkzeug.datastructures import FileStorage
            file_storage = FileStorage(f)
            caption = get_caption_from_gemini(file_storage)
        
        cursor.execute("INSERT INTO media (memory_id, media_type, source_url, creation_time) VALUES (%s, %s, %s, %s)", (new_memory_id, 'photo', filename, datetime.now()))
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
    cursor.execute("DELETE FROM memories WHERE memory_id = %s", (memory_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('home_page'))

# --- Run the Server ---
if __name__ == '__main__':
    # We use use_reloader=False to prevent the infinite loop issue with large models
    app.run(debug=True, port=5000, use_reloader=False)