"""Movie-related routes (detail, reviews, watchlist)"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from app import db
from app.models import Movie, Review, Watchlist
from app.utils import subscription_required

bp = Blueprint('movies', __name__, url_prefix='')


@bp.route('/movie/<int:movie_id>', endpoint='movie_detail')
@subscription_required
def movie_detail(movie_id):
    """Movie detail page"""
    movie = Movie.query.get_or_404(movie_id)
    reviews = Review.query.filter_by(movie_id=movie.id).order_by(Review.timestamp.desc()).all()
    return render_template('movie_detail.html', movie=movie, reviews=reviews)


@bp.route('/add_review/<int:movie_id>', methods=['GET', 'POST'], endpoint='add_review')
@login_required
def add_review(movie_id):
    """Add a review to a movie"""
    movie = Movie.query.get_or_404(movie_id)
    if request.method == 'POST':
        content = request.form['content'].strip()
        rating = request.form['rating']

        if not content or not rating:
            flash('Please provide both review and rating.', 'warning')
            return redirect(url_for('movies.add_review', movie_id=movie.id))

        try:
            rating_val = int(rating)
        except ValueError:
            flash('Rating must be a number between 1 and 10.', 'warning')
            return redirect(url_for('movies.add_review', movie_id=movie.id))

        if rating_val < 1 or rating_val > 10:
            flash('Rating must be between 1 and 10.', 'warning')
            return redirect(url_for('movies.add_review', movie_id=movie.id))

        new_review = Review(content=content, rating=rating_val, user_id=current_user.id, movie_id=movie.id)
        db.session.add(new_review)
        db.session.commit()
        flash('Your review has been added!', 'success')
        return redirect(url_for('movie_detail', movie_id=movie.id))

    return render_template('add_review.html', movie=movie)


@bp.route('/watchlist/add/<int:movie_id>', methods=['POST'])
@login_required
def add_to_watchlist(movie_id):
    """Add movie to user's watchlist"""
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


@bp.route('/watchlist/remove/<int:movie_id>', methods=['GET', 'POST'])
@login_required
def remove_from_watchlist(movie_id):
    """Remove movie from user's watchlist"""
    item = Watchlist.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
        flash("Removed from watchlist!", "success")

    return redirect(url_for('watchlist'))


@bp.route('/watchlist')
@login_required
def watchlist():
    """View current user's watchlist"""
    entries = Watchlist.query.options(joinedload(Watchlist.movie)).filter_by(user_id=current_user.id).all()
    return render_template('watchlist.html', items=entries)

