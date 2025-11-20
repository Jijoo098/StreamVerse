"""Database initialization and seeding"""
import os
from werkzeug.security import generate_password_hash
from app import db
from app.models import User, SubscriptionPlan
from app.utils import bootstrap_migration


def initialize_db(app):
    """Initialize database and seed default data"""
    with app.app_context():
        db.create_all()
        bootstrap_migration(app)

        # Create a default admin user if not exists ONLY when explicitly requested via env var.
        if os.environ.get('STREAMVERSE_CREATE_ADMIN', '0') == '1':
            if not User.query.filter_by(email='admin@streamverse.com').first():
                admin = User(
                    email='admin@streamverse.com',
                    username='Admin',
                    password=generate_password_hash('admin123'),
                    is_admin=True
                )
                db.session.add(admin)
                db.session.commit()
                print("✅ Created default admin (admin@streamverse.com / admin123)")
        else:
            print("Note: default admin seeding is disabled. To enable, set STREAMVERSE_CREATE_ADMIN=1")
        
        # Seed default subscription plans (if none exist)
        if not SubscriptionPlan.query.count():
            plans = [
                SubscriptionPlan(name='Free', price=0.0, duration_days=36500),
                SubscriptionPlan(name='Premium', price=5.99, duration_days=30),
                SubscriptionPlan(name='Premium+', price=9.99, duration_days=30),
            ]
            db.session.bulk_save_objects(plans)
            db.session.commit()
            print("✅ Seeded default subscription plans")

