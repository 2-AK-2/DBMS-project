# --- app.py (V5 - Final Unified Version with All Search + Functional Routes) ---
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import mysql.connector
from PIL import Image
import os
from datetime import datetime
import requests
import base64
import io
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

# --- SEMANTIC SEARCH IMPORTS ---
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# --- CONFIGURATION ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# IMPORTANT: Use forward slashes '/' for paths even on Windows
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
semantic_model = None
def get_semantic_model():
    """Loads the model into memory ONLY on the first call, then reuses it."""
    global semantic_model
    if semantic_model is None:
        print("Loading semantic search model for the first time... (This may take a moment)")
        semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Semantic search model loaded successfully.")
    return semantic_model

# --- HELPER FUNCTIONS ---
def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def get_caption_from_gemini(file_storage) -> str:
    """Generate a caption using Gemini API for a given image."""
    print("Preparing image for direct API call...")
    try:
        file_storage.stream.seek(0)
        img = Image.open(file_storage.stream).convert('RGB')
        byte_arr = io.BytesIO()
        img.save(byte_arr, format='JPEG')
        encoded_image = base64.b64encode(byte_arr.getvalue()).decode('utf-8')

        payload = {
            "contents": [{
                "parts": [
                    {"text": "Describe this image in one descriptive sentence."},
                    {"inline_data": {"mime_type": "image/jpeg", "data": encoded_image}}
                ]
            }]
        }
        headers = {'Content-Type': 'application/json'}
        print("Sending request to Gemini API...")
        response = requests.post(API_ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"Error in get_caption_from_gemini: {e}")
        return "Caption generation failed."

# --- UI ROUTES ---

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
    cursor.execute("""
        SELECT m.memory_id, m.title, med.source_url
        FROM media med
        JOIN memories m ON med.memory_id = m.memory_id
        ORDER BY m.memory_date DESC
    """)
    media_items = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('gallery.html', media_items=media_items)

# --- ADVANCED SEARCH (TERM + TAG + DATE + SEMANTIC) ---
@app.route('/search', methods=['GET', 'POST'])
def search_page():
    search_term = ''
    search_tag = ''
    search_date = ''
    results = []

    # Handle GET (tag click) and POST (form)
    if request.method == 'POST':
        search_term = request.form.get('search', '').strip()
        search_tag = request.form.get('tag', '').strip()
        search_date = request.form.get('date', '').strip()
    elif request.method == 'GET':
        search_tag = request.args.get('tag', '').strip()

    # Proceed only if something is searched
    if search_term or search_tag or search_date:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        base_query = """
            SELECT DISTINCT m.*, anl.generated_caption, med.source_url
            FROM memories m
            LEFT JOIN media med ON m.memory_id = med.memory_id
            LEFT JOIN ai_analysis anl ON med.media_id = anl.media_id
            LEFT JOIN memory_tags mt ON m.memory_id = mt.memory_id
            LEFT JOIN tags t ON mt.tag_id = t.tag_id
        """

        query_parts = []
        params = []

        if search_tag:
            query_parts.append("t.tag_name = %s")
            params.append(search_tag)
        if search_date:
            query_parts.append("m.memory_date = %s")
            params.append(search_date)

        query = base_query
        if query_parts:
            query += " WHERE " + " AND ".join(query_parts)

        cursor.execute(query, tuple(params))
        filtered_memories = cursor.fetchall()
        cursor.close()
        conn.close()

        # --- SEMANTIC SEARCH ---
        if search_term and filtered_memories:
            model = get_semantic_model()
            captions = [mem['generated_caption'] or "" for mem in filtered_memories]
            query_embedding = model.encode([search_term])
            caption_embeddings = model.encode(captions)
            similarities = cosine_similarity(query_embedding, caption_embeddings)[0]

            for i, memory in enumerate(filtered_memories):
                memory['similarity'] = similarities[i]

            results = sorted(
                [mem for mem in filtered_memories if mem['similarity'] > 0.3],
                key=lambda x: x['similarity'],
                reverse=True
            )
        else:
            results = filtered_memories

    return render_template('search.html',
                           results=results,
                           search_term=search_term,
                           search_tag=search_tag,
                           search_date=search_date)

@app.route('/add')
def add_memory_page():
    return render_template('add_memory.html')

@app.route('/memory/<int:memory_id>')
def memory_detail_page(memory_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT m.*, med.source_url, anl.generated_caption
        FROM memories m
        LEFT JOIN media med ON m.memory_id = med.memory_id
        LEFT JOIN ai_analysis anl ON med.media_id = anl.media_id
        WHERE m.memory_id = %s
    """, (memory_id,))
    memory = cursor.fetchone()
    tags = []
    if memory:
        cursor.execute("""
            SELECT t.tag_name FROM tags t
            JOIN memory_tags mt ON t.tag_id = mt.tag_id
            WHERE mt.memory_id = %s
        """, (memory_id,))
        tags = [row['tag_name'] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return render_template('memory_detail.html', memory=memory, tags=tags)

# --- ACTION ROUTES ---
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
        tags_string = request.form.get('tags', '')
        image_file = request.files['image']
        filename = secure_filename(image_file.filename)

        conn = get_db_connection()
        cursor = conn.cursor()

        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(image_path)

        # Insert memory
        cursor.execute("""
            INSERT INTO memories (patient_id, title, description, memory_date)
            VALUES (1, %s, %s, %s)
        """, (title, description, memory_date))
        new_memory_id = cursor.lastrowid

        # Insert tags
        if tags_string:
            tags = [tag.strip().lower() for tag in tags_string.split(',') if tag.strip()]
            for tag_name in tags:
                cursor.execute("SELECT tag_id FROM tags WHERE tag_name = %s", (tag_name,))
                result = cursor.fetchone()
                if result:
                    tag_id = result[0]
                else:
                    cursor.execute("INSERT INTO tags (tag_name) VALUES (%s)", (tag_name,))
                    tag_id = cursor.lastrowid
                cursor.execute("INSERT INTO memory_tags (memory_id, tag_id) VALUES (%s, %s)", (new_memory_id, tag_id))

        # Generate caption
        caption = get_caption_from_gemini(image_file)

        # Insert media + AI analysis
        cursor.execute("""
            INSERT INTO media (memory_id, media_type, source_url, creation_time)
            VALUES (%s, 'photo', %s, NOW())
        """, (new_memory_id, filename))
        new_media_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO ai_analysis (media_id, generated_caption)
            VALUES (%s, %s)
        """, (new_media_id, caption))

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
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ai_analysis WHERE media_id IN (SELECT media_id FROM media WHERE memory_id = %s)", (memory_id,))
        cursor.execute("DELETE FROM media WHERE memory_id = %s", (memory_id,))
        cursor.execute("DELETE FROM memory_tags WHERE memory_id = %s", (memory_id,))
        cursor.execute("DELETE FROM memories WHERE memory_id = %s", (memory_id,))
        conn.commit()
    except Exception as e:
        print(f"Error deleting memory: {e}")
        if conn: conn.rollback()
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('home_page'))

# --- RUN SERVER ---
if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True, port=5000, use_reloader=False)
