from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import post as post_model

bp = Blueprint('posts', __name__)

def login_required(f):
    """Decorator to require login for a route."""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@bp.route('/')
@bp.route('/timeline')
@login_required
def timeline():
    user_id = session.get('user_id')
    posts = post_model.get_timeline_posts(user_id)
    return render_template('timeline.html', posts=posts)

@bp.route('/post', methods=['POST'])
@login_required
def create_post():
    content = request.form.get('content')

    if not content or not content.strip():
        flash('Post content cannot be empty', 'error')
        return redirect(url_for('posts.timeline'))

    user_id = session.get('user_id')
    post_model.create_post(user_id, content)
    flash('Post created!', 'success')
    return redirect(url_for('posts.timeline'))

@bp.route('/delete/<post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    user_id = session.get('user_id')
    deleted = post_model.delete_post(post_id, user_id)

    if deleted:
        flash('Post deleted', 'success')
    else:
        flash('Could not delete post', 'error')

    return redirect(request.referrer or url_for('posts.timeline'))
