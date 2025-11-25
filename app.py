import os
import base64 
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from datetime import datetime

# --- Initialization & Configuration ---
app = Flask(__name__)
# IMPORTANT: Use a strong secret key for session management
app.secret_key = "a_strong_secret_key_for_session_management_2024" 
app.config['ENV'] = 'development'
app.config['DEBUG'] = True

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# Database configuration: using SQLite directly
DB_PATH = os.path.join(BASE_DIR, 'school.db')
# Upload folder configuration: images go into static/uploads
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16MB max upload

# --- Database Helper Functions ---
def get_db_connection():
    """Creates and returns a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # This allows column access by name
    return conn

def init_database():
    """Initializes the database and creates tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idno VARCHAR(10) NOT NULL UNIQUE,
            lastname VARCHAR(25) NOT NULL,
            firstname VARCHAR(25) NOT NULL,
            course VARCHAR(10) NOT NULL,
            level VARCHAR(5) NOT NULL,
            image_file VARCHAR(100) DEFAULT 'default_user.png'
        )
    ''')
    
    # Create index on idno for faster lookups
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_idno ON students(idno)
    ''')
    
    conn.commit()
    conn.close()

# Initialize database and upload folder
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
init_database()

# --- Routes ---

@app.route('/')
def index():
    """Renders the main page and fetches all student data."""
    conn = get_db_connection()
    # Order by ID descending so newly added students appear at the top
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    # Convert Row objects to dictionaries for template compatibility
    students = [dict(row) for row in rows]
    return render_template('index.html', students=students)

# ---------------------------------------------------------------------
# PRIMARY SAVE ROUTE FOR WEBCAM (Handles Base64 data from JS)
# ---------------------------------------------------------------------
@app.route('/savestudent', methods=['POST'])
def save_student_from_webcam():
    """
    Receives base64 image data via POST body and student details via URL query.
    Saves the image and creates a new student record.
    Returns status codes and text for JavaScript handling.
    """
    try:
        # 1. Get student data from URL query parameters (sent by Webcam.upload)
        idno = request.args.get('idno')
        lastname = request.args.get('lastname')
        firstname = request.args.get('firstname')
        course = request.args.get('course')
        level = request.args.get('level')
        
        # 2. Basic Validation & Uniqueness Check
        if not all([idno, lastname, firstname, course, level]):
            return "Error: All student fields are required.", 400

        # Check for existing student ID before proceeding with image saving
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM students WHERE idno = ?', (idno,))
        if cursor.fetchone():
            conn.close()
            return "Error: ID Number already exists. Use a unique ID.", 409

        # 3. Get and decode the image data (sent in the POST request body)
        # Webcam.upload sends the base64 data URI directly in the POST body
        image_data_b64 = None
        
        try:
            # Webcam.js sends data as raw POST body, but we need to read it before Flask processes it
            # Try multiple methods to get the image data
            
            # Method 1: Check request.data (raw bytes)
            if request.data and len(request.data) > 0:
                try:
                    image_data_b64 = request.data.decode('utf-8')
                    if app.config['DEBUG']:
                        print(f"DEBUG: Got image from request.data, length: {len(image_data_b64)}")
                except UnicodeDecodeError:
                    pass
            
            # Method 2: Check request.form (if sent as form field)
            if not image_data_b64 and request.form:
                # Webcam.js might send it with different field names
                for field_name in ['file', 'image', 'webcam', 'data']:
                    if field_name in request.form:
                        image_data_b64 = request.form[field_name]
                        if app.config['DEBUG']:
                            print(f"DEBUG: Got image from request.form['{field_name}']")
                        break
            
            # Method 3: Check request.get_data() - get raw data stream
            if not image_data_b64:
                try:
                    raw_data = request.get_data(as_text=True)
                    if raw_data and len(raw_data) > 0 and 'data:image' in raw_data:
                        image_data_b64 = raw_data
                        if app.config['DEBUG']:
                            print(f"DEBUG: Got image from request.get_data(), length: {len(image_data_b64)}")
                except Exception as e:
                    if app.config['DEBUG']:
                        print(f"DEBUG: Error getting raw data: {e}")
            
            # Method 4: Check JSON if content-type is application/json
            if not image_data_b64 and request.is_json and request.json:
                image_data_b64 = request.json.get('image') or request.json.get('file') or request.json.get('data')
                if image_data_b64 and app.config['DEBUG']:
                    print("DEBUG: Got image from JSON")
                    
        except Exception as e:
            print(f"Error decoding request data: {e}")
            import traceback
            traceback.print_exc()
        
        # Debug information (remove in production)
        if app.config['DEBUG']:
            print(f"DEBUG: Request method: {request.method}")
            print(f"DEBUG: Request data length: {len(request.data) if request.data else 0}")
            print(f"DEBUG: Content-Type: {request.content_type}")
            print(f"DEBUG: Has form data: {bool(request.form)}")
            if request.form:
                print(f"DEBUG: Form keys: {list(request.form.keys())}")
                for key in request.form.keys():
                    val = request.form[key]
                    print(f"DEBUG: Form[{key}] = {str(val)[:50]}... (length: {len(str(val))})")
            if image_data_b64:
                print(f"DEBUG: Image data preview: {image_data_b64[:100]}...")
                print(f"DEBUG: Image data total length: {len(image_data_b64)}")
            else:
                print("DEBUG: No image data found in request")
                print(f"DEBUG: request.data type: {type(request.data)}")
                print(f"DEBUG: request.data content (first 200 chars): {str(request.data)[:200] if request.data else 'None'}")
        
        if not image_data_b64:
            return "Error: No image data received. Please take a picture using the TAKE PHOTO button first.", 400
        
        if 'base64,' not in image_data_b64:
            return "Error: Invalid image format. Please take a new picture using the TAKE PHOTO button.", 400

        # Split header from actual base64 data
        header, base64_data = image_data_b64.split('base64,', 1)
        extension = '.jpeg' 

        # Decode the base64 string to binary image data
        image_binary = base64.b64decode(base64_data)

        # 4. Create a unique filename using secure_filename for safety
        filename = f"{secure_filename(idno)}_{datetime.now().strftime('%Y%m%d%H%M%S')}{extension}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # 5. Save the file
        with open(file_path, 'wb') as f:
            f.write(image_binary)
        
        # 6. Create and commit the new student record
        cursor.execute('''
            INSERT INTO students (idno, lastname, firstname, course, level, image_file)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (idno, lastname, firstname, course, level, filename))
        conn.commit()
        conn.close()
        
        # Return success message for JS
        return "Student Saved Successfully", 200

    except Exception as e:
        # Log the error for debugging
        print(f"An unexpected error occurred during save: {e}")
        return f"Internal Server Error: Failed to process request due to: {e}", 500

# ---------------------------------------------------------------------
# DELETE ROUTE 
# ---------------------------------------------------------------------
@app.route('/delete/<int:id>', methods=['POST'])
def delete_student(id):
    """Deletes a student record and its associated image file."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get student data before deleting
        cursor.execute('SELECT * FROM students WHERE id = ?', (id,))
        student = cursor.fetchone()
        
        if not student:
            conn.close()
            flash(f"Student with ID {id} not found", "danger")
            return redirect(url_for('index'))
        
        # Delete the image file from the disk
        image_file = student['image_file']
        if image_file and image_file != 'default_user.png':
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], image_file)
            if os.path.exists(file_path):
                os.remove(file_path)

        # Delete the student record
        cursor.execute('DELETE FROM students WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        
        # Use flash for success message on redirect
        flash(f"Student {student['firstname']} {student['lastname']} Deleted Successfully", "warning")
    except Exception as e:
        # Use flash for error message on redirect
        flash(f"Error deleting student: {e}", "danger")
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)