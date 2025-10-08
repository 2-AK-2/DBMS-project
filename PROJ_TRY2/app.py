# --- app.py (With Tagging and Advanced Search) ---
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import mysql.connector
from PIL import Image
import os
from datetime import datetime
import requests
import base64
import io
from werkzeug.utils import secure_filename

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
    search_term = ''
    search_tag = ''
    search_date = ''
    results = []

    if request.method == 'POST':
        search_term = request.form.get('search', '')
        search_tag = request.form.get('tag', '')
        search_date = request.form.get('date', '')
    elif request.method == 'GET':
        search_tag = request.args.get('tag', '')

    if search_term or search_tag or search_date:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query_parts = []
        params = []
        
        base_query = """
            SELECT DISTINCT m.* FROM memories m
            LEFT JOIN media med ON m.memory_id = med.memory_id
            LEFT JOIN ai_analysis anl ON med.media_id = anl.media_id
            LEFT JOIN memory_tags mt ON m.memory_id = mt.memory_id
            LEFT JOIN tags t ON mt.tag_id = t.tag_id
        """
        
        if search_term:
            query_parts.append("(m.title LIKE %s OR m.description LIKE %s OR anl.generated_caption LIKE %s)")
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern, search_pattern, search_pattern])
            
        if search_tag:
            query_parts.append("t.name = %s")
            params.append(search_tag)
            
        if search_date:
            query_parts.append("m.memory_date = %s")
            params.append(search_date)
            
        if query_parts:
            query = base_query + " WHERE " + " AND ".join(query_parts)
            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            
        cursor.close()
        conn.close()
        
    return render_template('search.html', results=results, search_term=search_term, search_tag=search_tag, search_date=search_date)


@app.route('/add')
def add_memory_page():
    return render_template('add_memory.html')

@app.route('/memory/<int:memory_id>')
def memory_detail_page(memory_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Fetch memory details
    cursor.execute("""
        SELECT m.*, med.source_url, anl.generated_caption 
        FROM memories m 
        LEFT JOIN media med ON m.memory_id = med.memory_id 
        LEFT JOIN ai_analysis anl ON med.media_id = anl.media_id 
        WHERE m.memory_id = %s
    """, (memory_id,))
    memory = cursor.fetchone()
    
    # Fetch tags for the memory
    tags = []
    if memory:
        cursor.execute("""
            SELECT t.name FROM tags t
            JOIN memory_tags mt ON t.tag_id = mt.tag_id
            WHERE mt.memory_id = %s
        """, (memory_id,))
        tags = [row['name'] for row in cursor.fetchall()]
        
    cursor.close()
    conn.close()
    return render_template('memory_detail.html', memory=memory, tags=tags)


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
        tags_string = request.form.get('tags', '') # Get tags from form
        image_file = request.files['image']
        
        filename = secure_filename(image_file.filename)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(image_path)
        
        cursor.execute("INSERT INTO memories (patient_id, title, description, memory_date) VALUES (1, %s, %s, %s)", (title, description, memory_date))
        new_memory_id = cursor.lastrowid
        
        # --- TAG HANDLING ---
        if tags_string:
            tags = [tag.strip() for tag in tags_string.split(',') if tag.strip()]
            for tag_name in tags:
                # Check if tag exists
                cursor.execute("SELECT tag_id FROM tags WHERE name = %s", (tag_name,))
                result = cursor.fetchone()
                if result:
                    tag_id = result[0]
                else:
                    # Insert new tag
                    cursor.execute("INSERT INTO tags (name) VALUES (%s)", (tag_name,))
                    tag_id = cursor.lastrowid
                # Link tag to memory
                cursor.execute("INSERT INTO memory_tags (memory_id, tag_id) VALUES (%s, %s)", (new_memory_id, tag_id))

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
    cursor.execute("SELECT source_url FROM media WHERE memory_id = %s", (memory_id,))
    result = cursor.fetchone()
    if result:
        filename = result[0]
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(image_path):
            os.remove(image_path)
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