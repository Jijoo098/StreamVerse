"""Admin routes (dashboard, movie management, subscription management)"""
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename
from datetime import datetime
from app import db
from app.models import Movie, SubscriptionPlan, UserSubscription, User
from app.utils import admin_required, allowed_image

bp = Blueprint('admin', __name__, url_prefix='')


@bp.route('/admin', endpoint='admin_dashboard')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    movies = Movie.query.all()
    return render_template('admin_dashboard.html', movies=movies)


@bp.route('/admin/subscription_plans', endpoint='admin_subscription_plans')
@login_required
@admin_required
def admin_subscription_plans():
    """View all subscription plans"""
    plans = SubscriptionPlan.query.order_by(SubscriptionPlan.price.asc()).all()
    return render_template('admin_subscription_plans.html', plans=plans)


@bp.route('/admin/subscription_plans/add', methods=['GET', 'POST'], endpoint='admin_subscription_plans_add')
@login_required
@admin_required
def admin_subscription_plans_add():
    """Add a new subscription plan"""
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


@bp.route('/admin/subscription_users', endpoint='admin_subscription_users')
@login_required
@admin_required
def admin_subscription_users():
    """View all user subscriptions"""
    subs = db.session.query(UserSubscription, SubscriptionPlan, User).join(
        SubscriptionPlan, UserSubscription.plan_id == SubscriptionPlan.id
    ).join(
        User, UserSubscription.user_id == User.id
    ).order_by(UserSubscription.end_date.desc()).all()
    return render_template('admin_subscription_users.html', subscriptions=subs)


@bp.route('/admin/edit/<int:movie_id>', methods=['GET'], endpoint='admin_edit')
@login_required
@admin_required
def admin_edit(movie_id):
    """Edit movie page (GET)"""
    movie = Movie.query.get_or_404(movie_id)
    return render_template('admin_edit.html', movie=movie)


@bp.route('/edit_movie/<int:movie_id>', methods=['POST'], endpoint='edit_movie')
@login_required
@admin_required
def edit_movie(movie_id):
    """Edit movie (POST)"""
    movie = Movie.query.get_or_404(movie_id)

    # Read updated fields from the modal form
    movie.title = request.form.get('title', movie.title).strip()
    movie.genre = request.form.get('genre', movie.genre)
    movie.release_date = request.form.get('release_date', movie.release_date)
    movie.trailer_url = request.form.get('trailer_url', movie.trailer_url)
    movie.poster_url = request.form.get('poster_url', movie.poster_url)
    movie.description = request.form.get('description', movie.description)

    db.session.commit()
    flash("Movie updated successfully ✅", "success")
    return redirect(url_for('movie_detail', movie_id=movie.id))


@bp.route('/delete_movie/<int:movie_id>', methods=['POST'], endpoint='delete_movie')
@login_required
@admin_required
def delete_movie(movie_id):
    """Delete a movie"""
    movie = Movie.query.get_or_404(movie_id)

    # Remove uploaded poster file if exists
    if movie.poster_path:
        try:
            abs_path = os.path.join(current_app.static_folder, movie.poster_path)
            if os.path.isfile(abs_path):
                os.remove(abs_path)
        except Exception:
            pass

    db.session.delete(movie)
    db.session.commit()
    flash("Movie deleted successfully 🗑️", "success")
    return redirect(url_for('admin_dashboard'))


@bp.route('/add_movie', methods=['GET', 'POST'], endpoint='add_movie')
@login_required
@admin_required
def add_movie():
    """Add a new movie"""
    if request.method == 'POST':
        title = request.form['title'].strip()
        genre = request.form.get('genre', '').strip()
        release_date = request.form.get('release_date', '').strip()
        trailer_url = request.form.get('trailer_url', '').strip()
        poster_url = request.form.get('poster_url', '').strip()  # optional fallback
        description = request.form['description'].strip()

        # NEW metadata
        language_vals = request.form.getlist('language')  # multi-select
        language = ", ".join([v for v in language_vals if v]) or None
        runtime = request.form.get('runtime', '').strip()
        imdb_rating = request.form.get('imdb_rating', '').strip()
        age_rating = request.form.get('age_rating', '').strip()
        tags = request.form.get('tags', '').strip()

        # Handle poster file upload (optional)
        poster_file = request.files.get('poster_file')
        poster_path = None
        if poster_file and poster_file.filename and allowed_image(poster_file.filename):
            filename = secure_filename(poster_file.filename)
            name, ext = os.path.splitext(filename)
            safe_name = f"poster_{int(datetime.utcnow().timestamp())}{ext.lower()}"
            save_path = os.path.join(current_app.config['POSTER_FOLDER'], safe_name)
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
            poster_path=poster_path,
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

