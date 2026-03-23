"""WSGI entry point for gunicorn.

Usage: gunicorn --bind 127.0.0.1:3000 --workers 1 wsgi:app
"""
from server import app, init_db

init_db()
