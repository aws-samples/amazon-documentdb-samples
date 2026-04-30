from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import user as user_model
from models import post as post_model

bp = Blueprint('users', __name__)

def login_required(f):
    """Decorator to require login for a route."""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@bp.route('/profile/<username>')
@login_required
def profile(username):
    user = user_model.find_user_by_username(username)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('posts.timeline'))

    posts = post_model.get_user_posts(user['_id'])
    current_user_id = session.get('user_id')
    is_own_profile = str(user['_id']) == current_user_id
    is_following = user_model.is_following(current_user_id, user['_id']) if not is_own_profile else False

    return render_template('profile.html',
                          user=user,
                          posts=posts,
                          is_own_profile=is_own_profile,
                          is_following=is_following,
                          follower_count=len(user.get('followers', [])),
                          following_count=len(user.get('following', [])))

@bp.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    user = user_model.find_user_by_username(username)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('posts.timeline'))

    try:
        user_model.follow_user(session['user_id'], user['_id'])
        flash(f'Now following {username}', 'success')
    except ValueError as e:
        flash(str(e), 'error')

    return redirect(url_for('users.profile', username=username))

@bp.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    user = user_model.find_user_by_username(username)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('posts.timeline'))

    user_model.unfollow_user(session['user_id'], user['_id'])
    flash(f'Unfollowed {username}', 'success')
    return redirect(url_for('users.profile', username=username))
