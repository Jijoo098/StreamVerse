from datetime import datetime
from flask_login import UserMixin
from app import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    profile_pic = db.Column(db.String(300), nullable=True)

    # relationships
    reviews = db.relationship('Review', backref='user', lazy=True, cascade="all, delete-orphan")
    watchlist = db.relationship('Watchlist', backref='user', lazy=True, cascade="all, delete-orphan")
    subscriptions = db.relationship('UserSubscription', backref='user', lazy=True, cascade="all, delete-orphan")


class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    genre = db.Column(db.String(100), nullable=True)
    trailer_url = db.Column(db.String(500), nullable=True)
    release_date = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=False)
    poster_url = db.Column(db.String(500))
    # New OTT metadata (all nullable to keep old rows valid)
    language = db.Column(db.String(200))      # comma-separated: "Hindi, English"
    runtime = db.Column(db.Integer)           # in minutes
    age_rating = db.Column(db.String(20))     # "U", "U/A", "A"
    imdb_rating = db.Column(db.Float)         # 0.0 - 10.0
    tags = db.Column(db.String(300))          # free text: "Trending, Popular"
    poster_path = db.Column(db.String(500))   # uploaded file relative path
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relationships
    reviews = db.relationship('Review', backref='movie', lazy=True, cascade="all, delete-orphan")


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class Watchlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False)
    # relationship to movie for convenient access in templates
    movie = db.relationship('Movie', lazy=True)


class SubscriptionPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)  # Duration in days
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UserSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plan.id'), nullable=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    # Relationships
    plan = db.relationship('SubscriptionPlan', lazy=True)


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False)  # e.g., 'Completed', 'Failed'

