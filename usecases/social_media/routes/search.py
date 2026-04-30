from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import user as user_model

bp = Blueprint('search', __name__)

def login_required(f):
    """Decorator to require login for a route."""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@bp.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    results = []

    if query:
        results = user_model.search_users(query)

    return render_template('search.html', query=query, results=results)
