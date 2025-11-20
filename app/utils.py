"""Utility functions for the application"""
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import flash, redirect, url_for, request, current_app
from flask_login import current_user
from werkzeug.utils import secure_filename
from app.models import UserSubscription, Movie


# File upload settings
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def allowed_image(filename: str) -> bool:
    """Check if image file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXT


def get_active_subscription(user):
    """Get the active subscription for a user"""
    if not user:
        return None
    now = datetime.utcnow()
    return UserSubscription.query.filter(
        UserSubscription.user_id == user.id,
        UserSubscription.end_date > now
    ).order_by(UserSubscription.end_date.desc()).first()


def is_subscribed(user):
    """Check if user has an active subscription"""
    return bool(get_active_subscription(user))


def subscription_required(f):
    """Decorator to require subscription for premium content"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If admin, always allow
        if current_user.is_authenticated and current_user.is_admin:
            return f(*args, **kwargs)
        # If not logged in, redirect to login
        if not current_user.is_authenticated:
            flash('Please login to access this content.', 'warning')
            return redirect(url_for('login'))

        # If the view has a movie object or movie_id, inspect tags
        movie_id = kwargs.get('movie_id') or request.view_args.get('movie_id')
        if movie_id:
            movie = Movie.query.get(int(movie_id))
            if movie and movie.tags and 'premium' in (movie.tags or '').lower():
                if not is_subscribed(current_user):
                    flash('This content requires a subscription. Please subscribe to view.', 'warning')
                    return redirect(url_for('subscriptions'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Access denied. Admins only.", "danger")
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function


def bootstrap_migration(app):
    """Add new columns to the Movie table if they don't exist (SQLite-safe)."""
    with app.app_context():
        from app import db
        # read existing columns
        cols = {row[1] for row in db.session.execute(db.text("PRAGMA table_info('movie')")).fetchall()}
        to_add = []

        if 'language' not in cols:
            to_add.append("ALTER TABLE movie ADD COLUMN language VARCHAR(200)")
        if 'runtime' not in cols:
            to_add.append("ALTER TABLE movie ADD COLUMN runtime INTEGER")
        if 'age_rating' not in cols:
            to_add.append("ALTER TABLE movie ADD COLUMN age_rating VARCHAR(20)")
        if 'imdb_rating' not in cols:
            to_add.append("ALTER TABLE movie ADD COLUMN imdb_rating FLOAT")
        if 'tags' not in cols:
            to_add.append("ALTER TABLE movie ADD COLUMN tags VARCHAR(300)")
        if 'poster_path' not in cols:
            to_add.append("ALTER TABLE movie ADD COLUMN poster_path VARCHAR(500)")
        if 'created_at' not in cols:
            to_add.append("ALTER TABLE movie ADD COLUMN created_at DATETIME")

        for sql in to_add:
            db.session.execute(db.text(sql))
        if to_add:
            db.session.commit()

