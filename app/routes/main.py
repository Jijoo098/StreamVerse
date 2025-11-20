"""Main routes (landing, home/browse)"""
from flask import Blueprint, render_template, request, jsonify, url_for
from flask_login import current_user
from app.models import Movie, Watchlist
from app import db
from sqlalchemy.orm import joinedload

bp = Blueprint('main', __name__, url_prefix='')


@bp.route('/', endpoint='landing')
def landing():
    """Landing page"""
    return render_template('landing.html')


@bp.route('/home', endpoint='home')
def home():
    """Home/Browse page with search and filtering - Crunchyroll-style"""
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
    
    # Crunchyroll-style content sections (only if not searching/filtering)
    continue_watching = []
    recently_added = []
    top_picks = []
    genre_sections = {}
    popular_this_week = []
    
    if not q and not genre:
        # Continue Watching (user's watchlist)
        if current_user.is_authenticated:
            watchlist_entries = Watchlist.query.options(joinedload(Watchlist.movie)).filter_by(
                user_id=current_user.id
            ).order_by(Watchlist.id.desc()).limit(10).all()
            continue_watching = [entry.movie for entry in watchlist_entries if entry.movie]
        
        # Recently Added (latest movies)
        recently_added = Movie.query.order_by(Movie.created_at.desc()).limit(10).all()
        
        # Popular This Week (high-rated movies)
        popular_this_week = Movie.query.filter(
            Movie.imdb_rating.isnot(None)
        ).order_by(Movie.imdb_rating.desc()).limit(10).all()
        
        # Top Picks for You (based on user's watchlist genres or popular movies)
        if current_user.is_authenticated and continue_watching:
            # Get genres from user's watchlist
            user_genres = set()
            for movie in continue_watching:
                if movie.genre:
                    user_genres.update([g.strip() for g in movie.genre.split('/')])
            
            if user_genres:
                # Find movies in user's preferred genres
                genre_filter = Movie.genre.ilike('%' + '%'.join(list(user_genres)[:2]) + '%')
                top_picks = Movie.query.filter(genre_filter).order_by(
                    Movie.imdb_rating.desc()
                ).limit(10).all()
        
        if not top_picks:
            # Fallback: high-rated recent movies
            top_picks = Movie.query.filter(
                Movie.imdb_rating.isnot(None)
            ).order_by(Movie.imdb_rating.desc(), Movie.created_at.desc()).limit(10).all()
        
        # Genre-based sections
        all_genres = db.session.query(Movie.genre).distinct().all()
        genres_list = [g[0] for g in all_genres if g[0]]
        
        for genre_name in genres_list[:6]:  # Top 6 genres
            genre_movies = Movie.query.filter(
                Movie.genre.ilike(f'%{genre_name}%')
            ).order_by(Movie.imdb_rating.desc(), Movie.created_at.desc()).limit(10).all()
            if genre_movies:
                genre_sections[genre_name] = genre_movies
    
    return render_template('browse.html', 
                         movies=movies, 
                         featured_movies=featured_movies, 
                         q=q, 
                         genre=genre,
                         continue_watching=continue_watching,
                         recently_added=recently_added,
                         top_picks=top_picks,
                         genre_sections=genre_sections,
                         popular_this_week=popular_this_week)


@bp.route('/api/search', endpoint='api_search')
def api_search():
    """API endpoint for real-time search"""
    q = request.args.get('q', '').strip()
    genre = request.args.get('genre', '').strip()
    limit = request.args.get('limit', 20, type=int)
    
    query = Movie.query
    if q:
        query = query.filter(
            (Movie.title.ilike(f"%{q}%")) |
            (Movie.description.ilike(f"%{q}%")) |
            (Movie.genre.ilike(f"%{q}%"))
        )
    if genre:
        query = query.filter(Movie.genre.ilike(f"%{genre}%"))
    
    movies = query.order_by(Movie.created_at.desc()).limit(limit).all()
    
    # Get popular searches (most searched genres)
    popular_genres = db.session.query(Movie.genre).distinct().limit(8).all()
    popular_genres = [g[0] for g in popular_genres if g[0]]
    
    results = {
        'movies': [{
            'id': m.id,
            'title': m.title,
            'genre': m.genre,
            'poster_url': m.poster_url or url_for('static', filename='images/default_poster.jpg'),
            'imdb_rating': float(m.imdb_rating) if m.imdb_rating else None,
            'description': m.description[:150] + '...' if m.description and len(m.description) > 150 else (m.description or '')
        } for m in movies],
        'count': len(movies),
        'popular_genres': popular_genres
    }
    
    return jsonify(results)

