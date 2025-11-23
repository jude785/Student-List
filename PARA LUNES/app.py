import os
import base64 
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime

# --- Initialization & Configuration ---
app = Flask(__name__)
# IMPORTANT: Use a strong secret key for session management
app.secret_key = "a_strong_secret_key_for_session_management_2024" 
app.config['ENV'] = 'development'
app.config['DEBUG'] = True

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# Database configuration: using SQLite for simplicity
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'school.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Upload folder configuration: images go into static/uploads
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16MB max upload

db = SQLAlchemy(app)

# --- Database Model ---
class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    idno = db.Column(db.String(10), unique=True, nullable=False)
    lastname = db.Column(db.String(25), nullable=False)
    firstname = db.Column(db.String(25), nullable=False)
    course = db.Column(db.String(10), nullable=False)
    level = db.Column(db.String(5), nullable=False)
    # Stores the filename of the picture
    image_file = db.Column(db.String(100), nullable=True, default='default_user.png')

# Create DB and table if they don't exist
with app.app_context():
    # Ensure the upload folder exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    db.create_all()

# --- Routes ---

@app.route('/')
def index():
    """Renders the main page and fetches all student data."""
    # Order by ID descending so newly added students appear at the top
    students = Student.query.order_by(Student.id.desc()).all()
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
        if Student.query.filter_by(idno=idno).first():
            return "Error: ID Number already exists. Use a unique ID.", 409

        # 3. Get and decode the image data (sent in the POST request body)
        image_data_b64 = request.data.decode('utf-8')
        
        if not image_data_b64 or 'base64,' not in image_data_b64:
            return "Error: No valid image data received. Please take a picture.", 400

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
        new_student = Student(
            idno=idno, 
            lastname=lastname, 
            firstname=firstname, 
            course=course,
            level=level, 
            image_file=filename
        )
        db.session.add(new_student)
        db.session.commit()
        
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
        student = Student.query.get_or_404(id)
        
        # Delete the image file from the disk
        if student.image_file and student.image_file != 'default_user.png':
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], student.image_file)
            if os.path.exists(file_path):
                os.remove(file_path)

        db.session.delete(student)
        db.session.commit()
        # Use flash for success message on redirect
        flash(f"Student {student.firstname} {student.lastname} Deleted Successfully", "warning")
    except Exception as e:
        # Use flash for error message on redirect
        flash(f"Error deleting student: {e}", "danger")
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)