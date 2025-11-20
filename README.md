# StreamVerse - Modular Structure

The application has been refactored into a modular, organized structure following Flask best practices.

## Project Structure

```
Streamverse/
├── app/                      # Main application package
│   ├── __init__.py          # App factory and configuration
│   ├── models.py            # Database models
│   ├── utils.py             # Helper functions and decorators
│   ├── db_init.py           # Database initialization and seeding
│   └── routes/              # Route blueprints
│       ├── __init__.py
│       ├── main.py          # Landing, home/browse
│       ├── auth.py          # Login, register, logout
│       ├── movies.py        # Movie detail, reviews, watchlist
│       ├── user.py          # Dashboard, profile, edit profile
│       ├── admin.py         # Admin dashboard, movie management
│       └── subscriptions.py # Subscription management
├── templates/                # Jinja2 templates
├── static/                   # Static files (CSS, images, uploads)
├── app.py                    # Backward compatible entry point
└── run.py                    # Recommended entry point
```

## Key Features

### 1. Application Factory Pattern
- `app/__init__.py` uses the factory pattern for better testability and configuration management
- Extensions (db, login_manager) are initialized separately

### 2. Modular Routes
Routes are organized into logical blueprints:
- **main**: Landing page, home/browse
- **auth**: Authentication (login, register, logout)
- **movies**: Movie-related (detail, reviews, watchlist)
- **user**: User dashboard, profile management
- **admin**: Admin panel and movie management
- **subscriptions**: Subscription plans and management

### 3. Separated Concerns
- **models.py**: All database models in one place
- **utils.py**: Helper functions, decorators, file validation
- **db_init.py**: Database initialization and seeding logic

## Running the Application

### Option 1: Using run.py (Recommended)
```bash
python run.py
```

### Option 2: Using app.py (Backward Compatible)
```bash
python app.py
```

## Environment Variables

Optional configuration via environment variables:
- `SECRET_KEY`: Flask secret key (default: 'streamverse_secret_key')
- `DATABASE_URL`: Database URI (default: 'sqlite:///streamverse.db')
- `STRIPE_SECRET_KEY`: Stripe API secret key
- `STRIPE_WEBHOOK_SECRET`: Stripe webhook secret
- `STRIPE_PUBLISHABLE_KEY`: Stripe publishable key
- `STREAMVERSE_CREATE_ADMIN`: Set to '1' to create default admin user

## Benefits of Modular Structure

1. **Maintainability**: Code is organized by functionality
2. **Scalability**: Easy to add new features and routes
3. **Testability**: Each module can be tested independently
4. **Reusability**: Utils and models can be imported where needed
5. **Clarity**: Clear separation of concerns

## Migration Notes

- All existing templates continue to work without changes
- Route names remain the same for backward compatibility
- Database structure unchanged
- All functionality preserved

