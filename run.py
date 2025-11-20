"""Main entry point for the application"""
from app import create_app
from app.db_init import initialize_db

app = create_app()

if __name__ == '__main__':
    initialize_db(app)
    app.run(debug=True)

