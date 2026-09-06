"""
WSGI entry point for Render deployment
SQLite version - no external database needed
"""
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import the app from app.py
from app import app, db, seed_admin

# Initialize database (creates SQLite file if not exists)
with app.app_context():
    db.create_all()
    seed_admin()
    print("Database initialized with SQLite")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)