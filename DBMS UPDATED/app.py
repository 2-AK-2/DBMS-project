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

LOCAL_IMAGE_DIRECTORY = 'C:/Users/User/Desktop/AK DOCUMENTS'

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Aasma1306',
    'database': 'memory_vault_db'
}

GOOGLE_API_KEY = "AIzaSyBO4qx31mCuWZaNwZiInGkK6dvUUZFCAEs"
MODEL_NAME = "models/gemini-2.5-flash"
API_ENDPOINT = f"https://generativelanguage.googleapis.com/v1/{MODEL_NAME}:generateContent?key={GOOGLE_API_KEY}"

# --- SEMANTIC MODEL (Lazy Load) ---
semantic_model = None
def get_semantic_model():
    global semantic_model
    if semantic_model is None:
        print("Loading semantic search model for the first time...")
        semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Semantic model loaded.")
    return semantic_model

# --- HELPER FUNCTIONS ---
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

        payload = {
            "contents": [{
                "parts": [
                    {"text": "Describe this image in one descriptive sentence."},
                    {"inline_data": {"mime_type": "image/jpeg", "data": encoded_image}}
                ]
            }]
        }
        headers = {'Content-Type': 'application/json'}
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
    stats = None
    memories = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get recent memories first
        cursor.execute("SELECT * FROM memories WHERE patient_id = 1 ORDER BY memory_date DESC LIMIT 5")
        memories = cursor.fetchall()
        
        # Close this cursor
        cursor.close()
        
        # Create a new cursor for the procedure call
        cursor = conn.cursor(dictionary=True)
        cursor.execute("CALL GetPatientDashboardStats(1)")
        stats = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if stats:
            print(f"Dashboard Stats - Memories: {stats['total_memories']}, Tags: {stats['total_tags']}, Media: {stats['total_media']}")
        
        return render_template('index.html', memories=memories, stats=stats)
    except Exception as e:
        print(f"Error in home_page: {e}")
        import traceback
        traceback.print_exc()
        return render_template('index.html', memories=memories, stats=stats)

@app.route('/gallery')
def gallery_page():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT m.memory_id, m.title, med.source_url
            FROM media med
            JOIN memories m ON med.memory_id = m.memory_id
            WHERE m.patient_id = 1
            ORDER BY med.creation_time DESC
        """)
        media_items = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('gallery.html', media_items=media_items)
    except Exception as e:
        print(f"Error in gallery_page: {e}")
        return render_template('gallery.html', media_items=[])

# --- SEARCH ---
@app.route('/search', methods=['GET', 'POST'])
def search_page():
    search_term, search_tag, search_date, results = '', '', '', []

    try:
        if request.method == 'POST':
            search_term = request.form.get('search', '').strip()
            search_tag = request.form.get('tag', '').strip()
            search_date = request.form.get('date', '').strip()
        elif request.method == 'GET':
            search_tag = request.args.get('tag', '').strip()

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
                WHERE m.patient_id = 1
            """

            query_parts, params = [], []
            if search_tag:
                query_parts.append("t.tag_name = %s")
                params.append(search_tag)
            if search_date:
                query_parts.append("m.memory_date = %s")
                params.append(search_date)

            query = base_query + (" AND " + " AND ".join(query_parts) if query_parts else "")
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
    except Exception as e:
        print(f"Error in search: {e}")

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
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT m.*, med.source_url, anl.generated_caption
            FROM memories m
            LEFT JOIN media med ON m.memory_id = med.memory_id
            LEFT JOIN ai_analysis anl ON med.media_id = anl.media_id
            WHERE m.memory_id = %s AND m.patient_id = 1
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
    except Exception as e:
        print(f"Error in memory_detail_page: {e}")
        return "Memory not found", 404

# --- EDIT PAGE ---
@app.route('/edit/<int:memory_id>')
def edit_memory_page(memory_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM memories WHERE memory_id = %s AND patient_id = 1", (memory_id,))
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
        
        if not memory:
            return "Memory not found", 404
        
        return render_template('edit_memory.html', memory=memory, tags=tags)
    except Exception as e:
        print(f"Error in edit_memory_page: {e}")
        return "Error loading memory", 404

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
        
        # Save image to filesystem
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(image_path)

        # Generate caption from Gemini
        image_file.stream.seek(0)
        caption = get_caption_from_gemini(image_file)

        # Call stored procedure AddMemoryWithTags
        cursor = conn.cursor()
        cursor.execute("""
            CALL AddMemoryWithTags(%s, %s, %s, %s, %s, %s, %s, @new_memory_id, @new_media_id)
        """, (1, title, description, memory_date, filename, caption, tags_string))
        
        conn.commit()
        print(f"✅ Memory added successfully with title: {title}")
        
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('home_page'))

# --- UPDATE MEMORY ---
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

        # Call stored procedure UpdateMemoryWithTags
        cursor.execute("""
            CALL UpdateMemoryWithTags(%s, %s, %s, %s, %s)
        """, (memory_id, title, description, memory_date, tags_string))

        conn.commit()
        print(f"✅ Memory {memory_id} updated successfully")
        
    except Exception as e:
        print(f"❌ An error occurred during update: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

    return redirect(url_for('memory_detail_page', memory_id=memory_id))

# --- DELETE MEMORY ---
@app.route('/delete_memory/<int:memory_id>', methods=['POST'])
def delete_memory(memory_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Call stored procedure DeleteMemoryWithAudit
        # This procedure automatically logs to audit_log table (trigger)
        cursor.execute("""
            CALL DeleteMemoryWithAudit(%s, %s)
        """, (memory_id, 'web_application'))
        
        conn.commit()
        print(f"✅ Memory {memory_id} deleted successfully with audit log (via trigger)")
        
    except Exception as e:
        print(f"❌ Error deleting memory: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('home_page'))

# --- AUDIT LOG ROUTES ---
@app.route('/audit_log')
def audit_log_page():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT * FROM audit_log
            ORDER BY action_timestamp DESC
            LIMIT 100
        """)
        logs = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('audit_log.html', logs=logs)
    except Exception as e:
        print(f"Error fetching audit logs: {e}")
        return render_template('audit_log.html', logs=[])

# --- RUN SERVER ---
if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True, port=5000, use_reloader=False)