from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from urllib.parse import urlparse
from models import post as post_model
from utils.decorators import login_required

bp = Blueprint('posts', __name__)

def _is_safe_local_redirect_target(target):
    """Allow only local in-app redirect targets (path-only)."""
    if not target:
        return False

    normalized_target = target.replace('\\', '')

    # Only allow absolute local paths (e.g. "/timeline"), never external URLs.
    if not normalized_target.startswith('/'):
        return False
    # Reject protocol-relative targets like "//evil.example".
    if normalized_target.startswith('//'):
        return False

    parsed = urlparse(normalized_target)
    return not parsed.scheme and not parsed.netloc

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

    referrer = request.referrer
    if _is_safe_local_redirect_target(referrer):
        return redirect(referrer)
    return redirect(url_for('posts.timeline'))
