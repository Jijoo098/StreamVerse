"""
Utility script to inspect or reset the default admin account.
Usage:
  python check_or_reset_admin.py            # show admin info (creates DB schema)
  python check_or_reset_admin.py --set-pass NEWPASSWORD

This script runs within the Flask app context and uses the same database.
"""

from app import app, db, User, initialize_db
from werkzeug.security import generate_password_hash
import sys


def print_admin_info():
    admin = User.query.filter_by(email='admin@streamverse.com').first()
    if not admin:
        print("Admin user not found.")
        return
    print("Admin user:")
    print(f"  id: {admin.id}")
    print(f"  email: {admin.email}")
    print(f"  username: {admin.username}")
    print(f"  is_admin: {admin.is_admin}")


if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == '--set-pass':
        if len(sys.argv) < 3:
            print("Usage: python check_or_reset_admin.py --set-pass NEWPASSWORD")
            sys.exit(1)
        new_pw = sys.argv[2]

        with app.app_context():
            initialize_db()
            admin = User.query.filter_by(email='admin@streamverse.com').first()
            if not admin:
                print("Admin user not found. You can seed one by setting STREAMVERSE_CREATE_ADMIN=1 before running the app.")
                sys.exit(1)
            admin.password = generate_password_hash(new_pw)
            db.session.commit()
            print("Admin password updated.")
            print_admin_info()
    else:
        with app.app_context():
            initialize_db()
            print_admin_info()
