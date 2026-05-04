from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import user as user_model
from utils.decorators import login_required

bp = Blueprint('search', __name__)

@bp.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    results = []

    if query:
        results = user_model.search_users(query)

    return render_template('search.html', query=query, results=results)
