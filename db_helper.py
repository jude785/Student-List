import sqlite3
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'school.db')

def db_helper():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
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
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_idno ON students(idno)
    ''')
    
    conn.commit()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='students'")
    table_exists = cursor.fetchone()
    
    if table_exists:
        print(f"✓ Database created successfully at: {DB_PATH}")
        print("✓ Table 'students' created successfully")
        
        cursor.execute("PRAGMA table_info(students)")
        columns = cursor.fetchall()
        print("\nTable structure:")
        print("-" * 60)
        for col in columns:
            print(f"  {col[1]:15} {col[2]:15} {'NOT NULL' if col[3] else 'NULL':10} {'PRIMARY KEY' if col[5] else ''}")
        print("-" * 60)
    else:
        print("✗ Error: Table was not created")
    
    conn.close()

if __name__ == '__main__':
    print("Creating SQLite database for Student Management System...")
    print("=" * 60)
    db_helper()
    print("\nDatabase setup complete!")

