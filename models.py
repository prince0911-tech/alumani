import sqlite3
from config import Config
import hashlib
from datetime import datetime
import os

class Database:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        try:
            db_path = Config.DATABASE_PATH
            self.connection = sqlite3.connect(db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # This makes rows behave like dictionaries
        except sqlite3.Error as err:
            print(f"Error connecting to SQLite: {err}")
    
    def execute_query(self, query, params=None):
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or [])
            self.connection.commit()
            # Convert Row objects to dictionaries and handle datetime conversion
            rows = cursor.fetchall()
            result = []
            for row in rows:
                row_dict = dict(row)
                # Convert datetime strings to datetime objects
                for key, value in row_dict.items():
                    if key.endswith('_at') or key.endswith('_date') or key == 'event_date':
                        if value and isinstance(value, str):
                            try:
                                row_dict[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                            except:
                                pass  # Keep as string if conversion fails
                result.append(row_dict)
            return result
        except sqlite3.Error as err:
            print(f"Error executing query: {err}")
            self.connection.rollback()
            return None
        finally:
            cursor.close()
    
    def execute_single(self, query, params=None):
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or [])
            self.connection.commit()
            row = cursor.fetchone()
            if row:
                row_dict = dict(row)
                # Convert datetime strings to datetime objects
                for key, value in row_dict.items():
                    if key.endswith('_at') or key.endswith('_date') or key == 'event_date':
                        if value and isinstance(value, str):
                            try:
                                row_dict[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                            except:
                                pass  # Keep as string if conversion fails
                return row_dict
            return None
        except sqlite3.Error as err:
            print(f"Error executing query: {err}")
            self.connection.rollback()
            return None
        finally:
            cursor.close()

def init_database():
    """Initialize database tables"""
    db = Database()
    
    # Users table
    db.execute_query("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'alumni' CHECK(role IN ('alumni', 'admin')),
            is_verified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Alumni profiles table
    db.execute_query("""
        CREATE TABLE IF NOT EXISTS alumni_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            batch_year INTEGER,
            department TEXT,
            current_job TEXT,
            company TEXT,
            location TEXT,
            achievements TEXT,
            profile_picture TEXT,
            cv_file TEXT,
            linkedin_url TEXT,
            privacy_level TEXT DEFAULT 'public' CHECK(privacy_level IN ('public', 'private')),
            available_for_mentorship INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Events table
    db.execute_query("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            event_date DATETIME,
            location TEXT,
            capacity INTEGER,
            event_type TEXT DEFAULT 'general',
            require_approval INTEGER DEFAULT 0,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    """)
    
    # Event registrations table
    db.execute_query("""
        CREATE TABLE IF NOT EXISTS event_registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            user_id INTEGER,
            status TEXT DEFAULT 'approved',
            admin_notes TEXT,
            attended INTEGER DEFAULT 0,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Forum posts table
    db.execute_query("""
        CREATE TABLE IF NOT EXISTS forum_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            author_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (author_id) REFERENCES users(id)
        )
    """)
    
    # Forum comments table
    db.execute_query("""
        CREATE TABLE IF NOT EXISTS forum_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            author_id INTEGER,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES forum_posts(id),
            FOREIGN KEY (author_id) REFERENCES users(id)
        )
    """)
    
    # Messages table
    db.execute_query("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            recipient_id INTEGER,
            subject TEXT,
            content TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (recipient_id) REFERENCES users(id)
        )
    """)
    
    # Job postings table
    db.execute_query("""
        CREATE TABLE IF NOT EXISTS job_postings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT,
            location TEXT,
            job_type TEXT CHECK(job_type IN ('full-time', 'part-time', 'internship', 'contract')),
            description TEXT,
            requirements TEXT,
            posted_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (posted_by) REFERENCES users(id)
        )
    """)
    
    # Mentorship requests table
    db.execute_query("""
        CREATE TABLE IF NOT EXISTS mentorship_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mentor_id INTEGER,
            mentee_id INTEGER,
            message TEXT,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'accepted', 'rejected')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mentor_id) REFERENCES users(id),
            FOREIGN KEY (mentee_id) REFERENCES users(id)
        )
    """)
    

    
    # Announcements table
    db.execute_query("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            created_by INTEGER,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    """)
    
    # Create default admin user
    admin_password = hashlib.sha256('admin123'.encode('utf-8')).hexdigest()
    db.execute_query("""
        INSERT OR IGNORE INTO users (email, password, role, is_verified) 
        VALUES (?, ?, ?, ?)
    """, ('admin@college.edu', admin_password, 'admin', 1))
    
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_database()