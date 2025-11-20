from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()


def create_app(config_name='default'):
    """Application factory pattern"""
    # Get the root directory (parent of app/)
    root_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    template_dir = os.path.join(root_dir, 'templates')
    static_dir = os.path.join(root_dir, 'static')
    
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'streamverse_secret_key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///streamverse.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Stripe configuration
    app.config['STRIPE_SECRET_KEY'] = os.environ.get('STRIPE_SECRET_KEY', None)
    app.config['STRIPE_WEBHOOK_SECRET'] = os.environ.get('STRIPE_WEBHOOK_SECRET', None)
    app.config['STRIPE_PUBLISHABLE_KEY'] = os.environ.get('STRIPE_PUBLISHABLE_KEY', None)
    
    # File upload settings
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'static', 'uploads')
    POSTER_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'static', 'posters')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(POSTER_FOLDER, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['POSTER_FOLDER'] = POSTER_FOLDER
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please login to access this page.'
    
    # Import models
    from app.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.routes.main import bp as main_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.movies import bp as movies_bp
    from app.routes.user import bp as user_bp
    from app.routes.admin import bp as admin_bp
    from app.routes.subscriptions import bp as subscriptions_bp
    
    # Register routes directly on app (bypassing blueprint prefixing for backward compatibility)
    from app.routes import auth, main, movies, user, admin, subscriptions
    
    # Main routes
    app.add_url_rule('/', 'landing', main.landing)
    app.add_url_rule('/home', 'home', main.home)
    
    # Auth routes
    app.add_url_rule('/login', 'login', auth.login, methods=['GET', 'POST'])
    app.add_url_rule('/register', 'register', auth.register, methods=['GET', 'POST'])
    app.add_url_rule('/logout', 'logout', auth.logout)
    
    # Movie routes
    app.add_url_rule('/movie/<int:movie_id>', 'movie_detail', movies.movie_detail)
    app.add_url_rule('/add_review/<int:movie_id>', 'add_review', movies.add_review, methods=['GET', 'POST'])
    app.add_url_rule('/watchlist/add/<int:movie_id>', 'add_to_watchlist', movies.add_to_watchlist, methods=['POST'])
    app.add_url_rule('/watchlist/remove/<int:movie_id>', 'remove_from_watchlist', movies.remove_from_watchlist, methods=['GET', 'POST'])
    app.add_url_rule('/watchlist', 'watchlist', movies.watchlist)
    
    # User routes
    app.add_url_rule('/dashboard', 'dashboard', user.dashboard)
    app.add_url_rule('/profile/<username>', 'profile', user.profile)
    app.add_url_rule('/edit_profile', 'edit_profile', user.edit_profile, methods=['GET', 'POST'])
    app.add_url_rule('/remove_watchlist/<int:movie_id>', 'remove_watchlist', user.remove_watchlist, methods=['POST'])
    
    # Admin routes
    app.add_url_rule('/admin', 'admin_dashboard', admin.admin_dashboard)
    app.add_url_rule('/admin/subscription_plans', 'admin_subscription_plans', admin.admin_subscription_plans)
    app.add_url_rule('/admin/subscription_plans/add', 'admin_subscription_plans_add', admin.admin_subscription_plans_add, methods=['GET', 'POST'])
    app.add_url_rule('/admin/subscription_users', 'admin_subscription_users', admin.admin_subscription_users)
    app.add_url_rule('/admin/edit/<int:movie_id>', 'admin_edit', admin.admin_edit, methods=['GET'])
    app.add_url_rule('/edit_movie/<int:movie_id>', 'edit_movie', admin.edit_movie, methods=['POST'])
    app.add_url_rule('/delete_movie/<int:movie_id>', 'delete_movie', admin.delete_movie, methods=['POST'])
    app.add_url_rule('/add_movie', 'add_movie', admin.add_movie, methods=['GET', 'POST'])
    
    # Subscription routes
    app.add_url_rule('/subscriptions', 'subscriptions', subscriptions.subscriptions)
    app.add_url_rule('/subscribe/<int:plan_id>', 'subscribe', subscriptions.subscribe, methods=['GET', 'POST'])
    app.add_url_rule('/subscription/cancel', 'cancel_subscription', subscriptions.cancel_subscription, methods=['POST'])
    app.add_url_rule('/stripe/webhook', 'stripe_webhook', subscriptions.stripe_webhook, methods=['POST'])
    
    return app

