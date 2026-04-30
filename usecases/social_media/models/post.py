from datetime import datetime
from bson import ObjectId
from models.db import get_db

def create_post(author_id, content):
    """Create a new post."""
    db = get_db()

    if isinstance(author_id, str):
        author_id = ObjectId(author_id)

    post_doc = {
        'author_id': author_id,
        'content': content,
        'created_at': datetime.utcnow()
    }

    result = db.posts.insert_one(post_doc)
    return result.inserted_id

def delete_post(post_id, author_id):
    """Delete a post (only if owned by author)."""
    db = get_db()

    if isinstance(post_id, str):
        post_id = ObjectId(post_id)
    if isinstance(author_id, str):
        author_id = ObjectId(author_id)

    result = db.posts.delete_one({
        '_id': post_id,
        'author_id': author_id
    })

    return result.deleted_count > 0

def get_user_posts(user_id, limit=50):
    """Get posts by a specific user."""
    db = get_db()

    if isinstance(user_id, str):
        user_id = ObjectId(user_id)

    posts = list(db.posts.find(
        {'author_id': user_id}
    ).sort('created_at', -1).limit(limit))

    author = db.users.find_one({'_id': user_id})

    for post in posts:
        post['author'] = author

    return posts

def get_timeline_posts(user_id, limit=50):
    """Get posts from users that the current user is following."""
    db = get_db()

    if isinstance(user_id, str):
        user_id = ObjectId(user_id)

    user = db.users.find_one({'_id': user_id})
    if not user:
        return []

    following_ids = user.get('following', [])
    following_ids.append(user_id)

    posts = list(db.posts.find(
        {'author_id': {'$in': following_ids}}
    ).sort('created_at', -1).limit(limit))

    for post in posts:
        author = db.users.find_one({'_id': post['author_id']})
        post['author'] = author

    return posts
