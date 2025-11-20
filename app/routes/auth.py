"""Authentication routes (login, register, logout)"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models import User

bp = Blueprint('auth', __name__, url_prefix='')


@bp.route('/register', methods=['GET', 'POST'], endpoint='register')
def register():
    """User registration"""
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


@bp.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    """User login"""
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


@bp.route('/logout', endpoint='logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

