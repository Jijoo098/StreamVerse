"""User-related routes (dashboard, profile, edit profile)"""
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename
from datetime import datetime
from app import db
from app.models import Watchlist
from app.utils import get_active_subscription, allowed_file

bp = Blueprint('user', __name__, url_prefix='')


@bp.route('/dashboard', endpoint='dashboard')
@login_required
def dashboard():
    """User dashboard"""
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    # Load the user's watchlist movies to display on the dashboard
    entries = Watchlist.query.options(joinedload(Watchlist.movie)).filter_by(user_id=current_user.id).all()
    movies = [e.movie for e in entries if e.movie]
    active = get_active_subscription(current_user)
    return render_template('dashboard.html', user=current_user, movies=movies, active=active)


@bp.route('/profile/<username>', endpoint='profile')
@login_required
def profile(username):
    """User profile page"""
    if current_user.username != username:
        flash("Access denied.")
        return redirect(url_for('home'))
    # Build a list of Movie objects for the profile template
    entries = Watchlist.query.options(joinedload(Watchlist.movie)).filter_by(user_id=current_user.id).all()
    movies = [e.movie for e in entries if e.movie]
    active = get_active_subscription(current_user)
    return render_template('profile.html', user=current_user, watchlist=movies, active=active)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    if request.method == 'POST':
        username = request.form.get('username', current_user.username).strip()
        file = request.files.get('profile_pic')

        if username:
            current_user.username = username

        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            _, ext = os.path.splitext(filename)
            filename = f"user_{current_user.id}_{int(datetime.utcnow().timestamp())}{ext.lower()}"
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            current_user.profile_pic = filename

        db.session.commit()
        flash('Profile updated!', 'success')
        return redirect(url_for('profile', username=current_user.username))

    return render_template('edit_profile.html', user=current_user)


@bp.route('/remove_watchlist/<int:movie_id>', methods=['POST'])
@login_required
def remove_watchlist(movie_id):
    """Remove movie from watchlist (from profile page)"""
    item = Watchlist.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('profile', username=current_user.username))

