# --- app.py (Final Version with All Features) ---
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
import mysql.connector
from PIL import Image
import os
from datetime import datetime
import requests
import base64
import io
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

# --- CONFIGURATION ---
app = Flask(__name__)
app.secret_key = 'a_super_secret_key_for_flash_messages'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

DB_CONFIG = {
    'host': 'localhost', 'user': 'root',
    'password': 'krishna22', 'database': 'memory_vault_db'
}
GOOGLE_API_KEY = "AIzaSyBO4qx31mCuWZaNwZiInGkK6dvUUZFCAEs"
MODEL_NAME = "models/gemini-2.5-flash"
API_ENDPOINT = f"https://generativelanguage.googleapis.com/v1/{MODEL_NAME}:generateContent?key={GOOGLE_API_KEY}"

## --- HELPER FUNCTIONS ---
def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def get_caption_from_gemini(file_storage) -> str:
    """Generate caption using Gemini API for a given image."""
    try:
        file_storage.stream.seek(0)
        img = Image.open(file_storage.stream).convert('RGB')
        byte_arr = io.BytesIO()
        img.save(byte_arr, format='JPEG')
        encoded_image = base64.b64encode(byte_arr.getvalue()).decode('utf-8')
        payload = {"contents": [{"parts": [{"text": "Describe this image in one descriptive sentence."}, {"inline_data": {"mime_type": "image/jpeg", "data": encoded_image}}]}]}
        headers = {'Content-Type': 'application/json'}
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
    # Get recent memories
    cursor.execute("SELECT * FROM memories ORDER BY memory_date DESC LIMIT 3")
    memories = cursor.fetchall()
    # USE THE FUNCTION: Get total memory count for the dashboard
    cursor.execute("SELECT CountPatientMemories(1) AS total_memories")
    stats = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('index.html', memories=memories, stats=stats)

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
    search_term = request.form.get('search', request.args.get('tag', '')).strip()
    results = []
    if search_term:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT DISTINCT m.* FROM memories m
            LEFT JOIN media med ON m.memory_id = med.memory_id
            LEFT JOIN ai_analysis anl ON med.media_id = anl.media_id
            LEFT JOIN memory_tags mt ON m.memory_id = mt.memory_id
            LEFT JOIN tags t ON mt.tag_id = t.tag_id
            WHERE m.title LIKE %s OR m.description LIKE %s OR anl.generated_caption LIKE %s OR t.tag_name LIKE %s
        """
        search_pattern = f"%{search_term}%"
        cursor.execute(query, (search_pattern, search_pattern, search_pattern, search_pattern))
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
    tags = []
    if memory:
        cursor.execute("SELECT t.tag_name FROM tags t JOIN memory_tags mt ON t.tag_id = mt.tag_id WHERE mt.memory_id = %s", (memory_id,))
        tags = [row['tag_name'] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return render_template('memory_detail.html', memory=memory, tags=tags)

@app.route('/edit/<int:memory_id>')
def edit_memory_page(memory_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM memories WHERE memory_id = %s", (memory_id,))
    memory = cursor.fetchone()
    tags = []
    if memory:
        cursor.execute("SELECT t.tag_name FROM tags t JOIN memory_tags mt ON t.tag_id = mt.tag_id WHERE mt.memory_id = %s", (memory_id,))
        tags = [row['tag_name'] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return render_template('edit_memory.html', memory=memory, tags=tags)


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
        tags_string = request.form.get('tags', '')
        image_file = request.files['image']
        filename = secure_filename(image_file.filename)
        
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(image_path)
        
        caption = get_caption_from_gemini(image_file)
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # USE THE STORED PROCEDURE
        result_args = cursor.callproc('AddFullMemory', (1, title, description, memory_date, filename, caption, 0))
        new_memory_id = result_args[6]
        
        # Handle tags
        if tags_string:
            tags = [tag.strip().lower() for tag in tags_string.split(',') if tag.strip()]
            for tag_name in tags:
                cursor.execute("SELECT tag_id FROM tags WHERE tag_name = %s", (tag_name,))
                tag_result = cursor.fetchone()
                if tag_result:
                    tag_id = tag_result['tag_id']
                else:
                    cursor.execute("INSERT INTO tags (tag_name) VALUES (%s)", (tag_name,))
                    tag_id = cursor.lastrowid
                cursor.execute("INSERT INTO memory_tags (memory_id, tag_id) VALUES (%s, %s)", (new_memory_id, tag_id))

        conn.commit()
        flash("Memory added successfully using Stored Procedure!", "success")
    except Exception as e:
        print(f"An error occurred: {e}")
        if conn: conn.rollback()
        flash("An error occurred while adding the memory.", "error")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('home_page'))

@app.route('/update_memory_action/<int:memory_id>', methods=['POST'])
def update_memory_action(memory_id):
    conn = None
    try:
        title = request.form['title']
        description = request.form['description']
        memory_date = request.form['date']
        tags_string = request.form.get('tags', '')

        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE memories SET title = %s, description = %s, memory_date = %s WHERE memory_id = %s", (title, description, memory_date, memory_id))
        
        cursor.execute("DELETE FROM memory_tags WHERE memory_id = %s", (memory_id,))
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
                cursor.execute("INSERT INTO memory_tags (memory_id, tag_id) VALUES (%s, %s)", (memory_id, tag_id))
        
        conn.commit()
        flash("Memory updated successfully!", "success")
    except Exception as e:
        print(f"An error occurred during update: {e}")
        if conn: conn.rollback()
        flash("Failed to update memory.", "error")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('memory_detail_page', memory_id=memory_id))

@app.route('/delete_memory/<int:memory_id>', methods=['POST'])
def delete_memory(memory_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT source_url FROM media WHERE memory_id = %s", (memory_id,))
    result = cursor.fetchone()
    if result and result['source_url']:
        filename = result['source_url']
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(image_path):
            os.remove(image_path)
            
    # The Trigger will automatically log this deletion
    cursor.execute("DELETE FROM memories WHERE memory_id = %s", (memory_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Memory deleted successfully!", "success")
    return redirect(url_for('home_page'))

# --- Run the Server ---
if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True, port=5000)
