#!/usr/bin/env python3
"""
Database initialization script for Alumni Platform
Run this script to set up the database tables and create the default admin user.
"""

import sqlite3
from config import Config
from models import init_database

def create_database():
    """Create the database if it doesn't exist"""
    try:
        # For SQLite, the database file is created automatically
        print("Using SQLite database: alumni_platform.db")
        return True
        
    except Exception as err:
        print(f"Error creating database: {err}")
        return False
    
    return True

def main():
    print("Initializing Alumni Platform Database...")
    print("=" * 50)
    
    # Create database
    if create_database():
        # Initialize tables and default data
        try:
            init_database()
            print("\nDatabase initialization completed successfully!")
            print("\nDefault admin credentials:")
            print("Email: admin@college.edu")
            print("Password: admin123")
            print("\nYou can now run the application with: python app.py")
            
        except Exception as e:
            print(f"Error initializing database: {e}")
    else:
        print("Failed to create database. Please check your SQLite configuration.")

if __name__ == "__main__":
    main()