"""Main routes (landing, home/browse)"""
from flask import Blueprint, render_template, request
from app.models import Movie

bp = Blueprint('main', __name__, url_prefix='')


@bp.route('/', endpoint='landing')
def landing():
    """Landing page"""
    return render_template('landing.html')


@bp.route('/home', endpoint='home')
def home():
    """Home/Browse page with search and filtering"""
    q = request.args.get('q', '').strip()
    genre = request.args.get('genre', '').strip()

    query = Movie.query
    if q:
        # Search in title, description, and genre
        query = query.filter(
            (Movie.title.ilike(f"%{q}%")) |
            (Movie.description.ilike(f"%{q}%")) |
            (Movie.genre.ilike(f"%{q}%"))
        )
    if genre:
        # Exact genre match or partial match
        query = query.filter(Movie.genre.ilike(f"%{genre}%"))

    movies = query.order_by(Movie.created_at.desc()).all()
    
    # Get featured movies for carousel (movies with "Trending" or "Featured" tags, or latest 5)
    featured_query = Movie.query
    featured_movies = featured_query.filter(
        (Movie.tags.ilike('%Trending%')) | 
        (Movie.tags.ilike('%Featured%')) |
        (Movie.tags.ilike('%Popular%'))
    ).order_by(Movie.created_at.desc()).limit(5).all()
    
    # If no tagged movies or less than 3, use latest 5 movies
    if not featured_movies or len(featured_movies) < 3:
        featured_movies = Movie.query.order_by(Movie.created_at.desc()).limit(5).all()
    
    return render_template('browse.html', movies=movies, featured_movies=featured_movies, q=q, genre=genre)

