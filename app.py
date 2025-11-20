from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import stripe
from functools import wraps
import os
from sqlalchemy.orm import joinedload

# ------------------------------------------------------
# APP CONFIGURATION
# ------------------------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'streamverse_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///streamverse.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# File upload settings
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Posters upload (separate from profile pics)
POSTER_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'posters')
os.makedirs(POSTER_FOLDER, exist_ok=True)
app.config['POSTER_FOLDER'] = POSTER_FOLDER

# Stripe configuration (optional — configure STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET as env vars)
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', None)
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', None)
STRIPE_PUBLISHABLE = os.environ.get('STRIPE_PUBLISHABLE_KEY', None)
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXT


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT



# ------------------------------------------------------
# MODELS
# ------------------------------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    profile_pic = db.Column(db.String(300), nullable=True)

    # relationships
    reviews = db.relationship('Review', backref='user', lazy=True, cascade="all, delete-orphan")
    # watchlist relationship - holds Watchlist entries for this user
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

# Subscription Plan Model
class SubscriptionPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)  # Duration in days
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# User Subscription Model
class UserSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plan.id'), nullable=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    # Relationships
    plan = db.relationship('SubscriptionPlan', lazy=True)

# Payment Model
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False)  # e.g., 'Completed', 'Failed'


# ------------------------------------------------------
# LOGIN MANAGER
# ------------------------------------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ------------------- SUBSCRIPTIONS HELPERS -------------------------
def get_active_subscription(user):
    if not user:
        return None
    now = datetime.utcnow()
    return UserSubscription.query.filter(UserSubscription.user_id == user.id, UserSubscription.end_date > now).order_by(UserSubscription.end_date.desc()).first()


def is_subscribed(user):
    return bool(get_active_subscription(user))


def subscription_required(f):
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

def bootstrap_migration():
    """Add new columns to the Movie table if they don't exist (SQLite-safe)."""
    with app.app_context():
        # read existing columns
        cols = {row[1] for row in db.session.execute(db.text("PRAGMA table_info('movie')")).fetchall()}
        to_add = []

        if 'language' not in cols:    to_add.append("ALTER TABLE movie ADD COLUMN language VARCHAR(200)")
        if 'runtime' not in cols:     to_add.append("ALTER TABLE movie ADD COLUMN runtime INTEGER")
        if 'age_rating' not in cols:  to_add.append("ALTER TABLE movie ADD COLUMN age_rating VARCHAR(20)")
        if 'imdb_rating' not in cols: to_add.append("ALTER TABLE movie ADD COLUMN imdb_rating FLOAT")
        if 'tags' not in cols:        to_add.append("ALTER TABLE movie ADD COLUMN tags VARCHAR(300)")
        if 'poster_path' not in cols: to_add.append("ALTER TABLE movie ADD COLUMN poster_path VARCHAR(500)")
        if 'created_at' not in cols:  to_add.append("ALTER TABLE movie ADD COLUMN created_at DATETIME")

        for sql in to_add:
            db.session.execute(db.text(sql))
        if to_add:
            db.session.commit()


# ------------------------------------------------------
# DATABASE INITIALIZATION
# ------------------------------------------------------
def initialize_db():
    with app.app_context():
        db.create_all()
        bootstrap_migration()  # <— add this line
        # (admin seeding stays the same)

        # Create a default admin user if not exists ONLY when explicitly requested via env var.
        # This avoids accidentally seeding a known admin password in production.
        # To create the seeded admin, set environment variable STREAMVERSE_CREATE_ADMIN=1
        # before running initialize_db(). Example (PowerShell):
        #   $env:STREAMVERSE_CREATE_ADMIN = '1'; python app.py
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
            # Helpful note for developers who expect a seeded admin
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


# ------------------------------------------------------
# ROUTES
# ------------------------------------------------------
@app.route('/')
def landing():
    return render_template('landing.html')


@app.route('/home')
def home():
    q = request.args.get('q', '').strip()
    genre = request.args.get('genre', '').strip()

    query = Movie.query
    if q:
        query = query.filter(Movie.title.ilike(f"%{q}%"))
    if genre:
        query = query.filter(Movie.genre.ilike(f"%{genre}%"))

    movies = query.order_by(Movie.created_at.desc()).all()
    return render_template('browse.html', movies=movies, q=q, genre=genre)



# ------------------- REGISTER -------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        username = request.form['username'].strip()
        password = request.form['password']

        if not email or not username or not password:
            flash("All fields are required.", "warning")
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already exists!", "danger")
            return redirect(url_for('register'))

        new_user = User(
            email=email,
            username=username,
            password=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()
        flash("Account created successfully! Please login.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')


# ------------------- LOGIN -------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Logged in successfully!", "success")
            return redirect(url_for('admin_dashboard') if user.is_admin else url_for('dashboard'))
        else:
            flash("Invalid credentials", "danger")
            return redirect(url_for('login'))
    return render_template('login.html')


# ------------------- LOGOUT -------------------------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))


# ------------------- USER DASHBOARD -------------------------
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    # Load the user's watchlist movies to display on the dashboard
    entries = Watchlist.query.options(joinedload(Watchlist.movie)).filter_by(user_id=current_user.id).all()
    movies = [e.movie for e in entries if e.movie]
    active = get_active_subscription(current_user)
    return render_template('dashboard.html', user=current_user, movies=movies, active=active)


# ------------------- ADMIN DASHBOARD -------------------------
@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('home'))
    movies = Movie.query.all()
    return render_template('admin_dashboard.html', movies=movies)


@app.route('/admin/subscription_plans')
@login_required
def admin_subscription_plans():
    if not current_user.is_admin:
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('home'))
    plans = SubscriptionPlan.query.order_by(SubscriptionPlan.price.asc()).all()
    return render_template('admin_subscription_plans.html', plans=plans)


@app.route('/admin/subscription_plans/add', methods=['GET', 'POST'])
@login_required
def admin_subscription_plans_add():
    if not current_user.is_admin:
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('home'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price = float(request.form.get('price', 0.0))
        duration = int(request.form.get('duration', 30))
        plan = SubscriptionPlan(name=name, price=price, duration_days=duration)
        db.session.add(plan)
        db.session.commit()
        flash('Subscription plan added!', 'success')
        return redirect(url_for('admin_subscription_plans'))
    return render_template('admin_subscription_plans_add.html')


@app.route('/admin/subscription_users')
@login_required
def admin_subscription_users():
    if not current_user.is_admin:
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('home'))
    subscriptions = UserSubscription.query.options(joinedload(UserSubscription.user), joinedload(UserSubscription.plan_id)).all()
    # joinedload(UserSubscription.plan) doesn't work because plan relationship not defined; we'll join manually
    subs = db.session.query(UserSubscription, SubscriptionPlan, User).join(SubscriptionPlan, UserSubscription.plan_id == SubscriptionPlan.id).join(User, UserSubscription.user_id == User.id).order_by(UserSubscription.end_date.desc()).all()
    return render_template('admin_subscription_users.html', subscriptions=subs)


@app.route('/admin/edit/<int:movie_id>', methods=['GET'])
@login_required
def admin_edit(movie_id):
    if not current_user.is_admin:
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('home'))
    movie = Movie.query.get_or_404(movie_id)
    return render_template('admin_edit.html', movie=movie)

@app.route('/edit_movie/<int:movie_id>', methods=['POST'])
@login_required
def edit_movie(movie_id):
    if not current_user.is_admin:
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('home'))

    movie = Movie.query.get_or_404(movie_id)

    # Read updated fields from the modal form
    movie.title        = request.form.get('title', movie.title).strip()
    movie.genre        = request.form.get('genre', movie.genre)
    movie.release_date = request.form.get('release_date', movie.release_date)
    movie.trailer_url  = request.form.get('trailer_url', movie.trailer_url)
    movie.poster_url   = request.form.get('poster_url', movie.poster_url)
    movie.description  = request.form.get('description', movie.description)

    db.session.commit()
    flash("Movie updated successfully ✅", "success")
    return redirect(url_for('movie_detail', movie_id=movie.id))


@app.route('/delete_movie/<int:movie_id>', methods=['POST'])
@login_required
def delete_movie(movie_id):
    if not current_user.is_admin:
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('home'))

    movie = Movie.query.get_or_404(movie_id)

    # 🧩 Remove uploaded poster file if exists
    if movie.poster_path:
        try:
            abs_path = os.path.join(app.static_folder, movie.poster_path)
            if os.path.isfile(abs_path):
                os.remove(abs_path)
        except Exception:
            pass

    db.session.delete(movie)
    db.session.commit()
    flash("Movie deleted successfully 🗑️", "success")
    return redirect(url_for('admin_dashboard'))


@app.route('/movie/<int:movie_id>')
@subscription_required
def movie_detail(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    reviews = Review.query.filter_by(movie_id=movie.id).order_by(Review.timestamp.desc()).all()
    return render_template('movie_detail.html', movie=movie, reviews=reviews)


# ------------------- ADD MOVIE (ADMIN) -------------------------

@app.route('/add_movie', methods=['GET', 'POST'])
@login_required
def add_movie():
    if not current_user.is_admin:
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('home'))

    if request.method == 'POST':
        title        = request.form['title'].strip()
        genre        = request.form.get('genre', '').strip()
        release_date = request.form.get('release_date', '').strip()
        trailer_url  = request.form.get('trailer_url', '').strip()
        poster_url   = request.form.get('poster_url', '').strip()  # optional fallback
        description  = request.form['description'].strip()

        # NEW metadata
        language_vals = request.form.getlist('language')  # multi-select
        language = ", ".join([v for v in language_vals if v]) or None
        runtime      = request.form.get('runtime', '').strip()
        imdb_rating  = request.form.get('imdb_rating', '').strip()
        age_rating   = request.form.get('age_rating', '').strip()
        tags         = request.form.get('tags', '').strip()

        # Handle poster file upload (optional)
        poster_file = request.files.get('poster_file')
        poster_path = None
        if poster_file and poster_file.filename and allowed_image(poster_file.filename):
            filename = secure_filename(poster_file.filename)
            name, ext = os.path.splitext(filename)
            safe_name = f"poster_{int(datetime.utcnow().timestamp())}{ext.lower()}"
            save_path = os.path.join(app.config['POSTER_FOLDER'], safe_name)
            poster_file.save(save_path)
            poster_path = f"posters/{safe_name}"  # relative to /static/

        # Parse numbers safely
        runtime_val = int(runtime) if runtime.isdigit() else None
        try:
            imdb_val = float(imdb_rating) if imdb_rating else None
        except:
            imdb_val = None

        new_movie = Movie(
            title=title,
            genre=genre or None,
            release_date=release_date or None,
            trailer_url=trailer_url or None,
            poster_url=poster_url or None,
            poster_path=poster_path,            # new
            description=description,
            language=language,
            runtime=runtime_val,
            age_rating=age_rating or None,
            imdb_rating=imdb_val,
            tags=tags or None,
            created_at=datetime.utcnow()
        )
        db.session.add(new_movie)
        db.session.commit()
        flash("Movie added successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('admin_add.html')



# ------------------- ADD REVIEW -------------------------
@app.route('/add_review/<int:movie_id>', methods=['GET', 'POST'])
@login_required
def add_review(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    if request.method == 'POST':
        content = request.form['content'].strip()
        rating = request.form['rating']

        if not content or not rating:
            flash('Please provide both review and rating.', 'warning')
            return redirect(url_for('add_review', movie_id=movie.id))

        try:
            rating_val = int(rating)
        except ValueError:
            flash('Rating must be a number between 1 and 10.', 'warning')
            return redirect(url_for('add_review', movie_id=movie.id))

        if rating_val < 1 or rating_val > 10:
            flash('Rating must be between 1 and 10.', 'warning')
            return redirect(url_for('add_review', movie_id=movie.id))

        new_review = Review(content=content, rating=rating_val, user_id=current_user.id, movie_id=movie.id)
        db.session.add(new_review)
        db.session.commit()
        flash('Your review has been added!', 'success')
        return redirect(url_for('movie_detail', movie_id=movie.id))

    return render_template('add_review.html', movie=movie)


# ------------------- PROFILE PAGE -------------------------
@app.route('/profile/<username>')
@login_required
def profile(username):
    if current_user.username != username:
        flash("Access denied.")
        return redirect(url_for('home'))
    # Build a list of Movie objects for the profile template
    entries = Watchlist.query.options(joinedload(Watchlist.movie)).filter_by(user_id=current_user.id).all()
    movies = [e.movie for e in entries if e.movie]
    active = get_active_subscription(current_user)
    return render_template('profile.html', user=current_user, watchlist=movies, active=active)



# ------------------- EDIT PROFILE -------------------------
@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        username = request.form.get('username', current_user.username).strip()
        file = request.files.get('profile_pic')

        if username:
            current_user.username = username

        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            _, ext = os.path.splitext(filename)
            filename = f"user_{current_user.id}_{int(datetime.utcnow().timestamp())}{ext.lower()}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            current_user.profile_pic = filename

        db.session.commit()
        flash('Profile updated!', 'success')
        return redirect(url_for('profile', username=current_user.username))

    return render_template('edit_profile.html', user=current_user)

@app.route('/watchlist/add/<int:movie_id>', methods=['POST'])
@login_required
def add_to_watchlist(movie_id):
    movie = Movie.query.get_or_404(movie_id)

    exists = Watchlist.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()
    if not exists:
        entry = Watchlist(user_id=current_user.id, movie_id=movie_id)
        db.session.add(entry)
        db.session.commit()
        flash("Added to Watchlist!", "success")
    else:
        flash("Already in watchlist!", "info")

    return redirect(url_for('movie_detail', movie_id=movie_id))


@app.route('/remove_watchlist/<int:movie_id>', methods=['POST'])
@login_required
def remove_watchlist(movie_id):
    item = Watchlist.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('profile', username=current_user.username))


# View current user's watchlist (template expects `items` where each has .movie)
@app.route('/watchlist')
@login_required
def watchlist():
    entries = Watchlist.query.options(joinedload(Watchlist.movie)).filter_by(user_id=current_user.id).all()
    return render_template('watchlist.html', items=entries)


# ------------------- SUBSCRIPTIONS -------------------------
def get_active_subscription(user):
    if not user:
        return None
    now = datetime.utcnow()
    return UserSubscription.query.filter(UserSubscription.user_id == user.id, UserSubscription.end_date > now).order_by(UserSubscription.end_date.desc()).first()


def is_subscribed(user):
    return bool(get_active_subscription(user))


def subscription_required(f):
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


@app.route('/subscriptions')
@login_required
def subscriptions():
    plans = SubscriptionPlan.query.order_by(SubscriptionPlan.price.asc()).all()
    active = get_active_subscription(current_user)
    return render_template('subscriptions.html', plans=plans, active=active)


@app.route('/subscribe/<int:plan_id>', methods=['GET', 'POST'])
@login_required
def subscribe(plan_id):
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    if request.method == 'POST':
        # If Stripe is configured, start checkout
        if STRIPE_SECRET_KEY:
            # Build a Stripe Checkout Session and redirect the user
            try:
                # Create a Stripe Checkout Session with plan price information
                session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': plan.name
                            },
                            'unit_amount': int(plan.price * 100)
                        },
                        'quantity': 1
                    }],
                    mode='payment',
                    success_url=url_for('subscriptions', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
                    cancel_url=url_for('subscriptions', _external=True),
                    metadata={'user_id': current_user.id, 'plan_id': plan.id}
                )
                return redirect(session.url)
            except Exception as e:
                # Fall back to mock processing if something goes wrong
                print('Stripe error:', e)

        # Fallback (mock) subscription mode if stripe not configured
        now = datetime.utcnow()
        end = now + timedelta(days=plan.duration_days)
        sub = UserSubscription(user_id=current_user.id, plan_id=plan.id, start_date=now, end_date=end)
        db.session.add(sub)
        # Record a simple payment record (mock)
        payment = Payment(user_id=current_user.id, amount=plan.price, status='Completed')
        db.session.add(payment)
        db.session.commit()
        flash(f'Subscribed to {plan.name} successfully! 🎉', 'success')
        return redirect(url_for('dashboard'))
    return render_template('subscribe_confirm.html', plan=plan)


@app.route('/subscription/cancel', methods=['POST'])
@login_required
def cancel_subscription():
    active = get_active_subscription(current_user)
    if active:
        active.end_date = datetime.utcnow()
        db.session.commit()
        flash('Subscription canceled. You will continue to have access until the period ends.', 'info')
    else:
        flash('No active subscription found.', 'warning')
    return redirect(url_for('subscriptions'))


@app.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    if not STRIPE_WEBHOOK_SECRET:
        return 'Webhook not configured', 400
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError as e:
        # Invalid payload
        return '', 400
    except stripe.error.SignatureVerificationError:
        return '', 400

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata = session.get('metadata', {}) or {}
        user_id = int(metadata.get('user_id', 0))
        plan_id = int(metadata.get('plan_id', 0))
        # Create the UserSubscription and Payment records
        try:
            plan = SubscriptionPlan.query.get(plan_id)
            if plan and user_id:
                now = datetime.utcnow()
                end = now + timedelta(days=plan.duration_days)
                s = UserSubscription(user_id=user_id, plan_id=plan.id, start_date=now, end_date=end)
                db.session.add(s)
                p = Payment(user_id=user_id, amount=plan.price, status='Completed')
                db.session.add(p)
                db.session.commit()
        except Exception as e:
            print('Error creating subscription from webhook:', e)

    return '', 200


# Removal endpoint used by some templates (accepts GET/POST for convenience)
@app.route('/watchlist/remove/<int:movie_id>', methods=['GET', 'POST'])
@login_required
def remove_from_watchlist(movie_id):
    item = Watchlist.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()
    if item:
        db.session.delete(item)
        db.session.commit()

    # If called from profile/dashboard, redirect back to watchlist page for clarity
    return redirect(url_for('watchlist'))


# ------------------------------------------------------
# MAIN EXECUTION
# ------------------------------------------------------
if __name__ == '__main__':
    initialize_db()
    app.run(debug=True)
