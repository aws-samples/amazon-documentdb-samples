from datetime import datetime
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from models.db import get_db
import re

def create_user(username, email, password, display_name=None, bio=None):
    """Create a new user account."""
    db = get_db()

    if db.users.find_one({'username': username}):
        raise ValueError('Username already exists')

    if db.users.find_one({'email': email}):
        raise ValueError('Email already exists')

    user_doc = {
        'username': username,
        'email': email,
        'password_hash': generate_password_hash(password),
        'display_name': display_name or username,
        'bio': bio or '',
        'followers': [],
        'following': [],
        'created_at': datetime.utcnow()
    }

    result = db.users.insert_one(user_doc)
    return result.inserted_id

def find_user_by_username(username):
    """Find a user by username."""
    db = get_db()
    return db.users.find_one({'username': username})

def find_user_by_email(email):
    """Find a user by email."""
    db = get_db()
    return db.users.find_one({'email': email})

def get_user_by_id(user_id):
    """Get a user by ID."""
    db = get_db()
    if isinstance(user_id, str):
        user_id = ObjectId(user_id)
    return db.users.find_one({'_id': user_id})

def verify_password(user, password):
    """Verify a user's password."""
    return check_password_hash(user['password_hash'], password)

def follow_user(follower_id, followee_id):
    """Follow a user."""
    db = get_db()

    if isinstance(follower_id, str):
        follower_id = ObjectId(follower_id)
    if isinstance(followee_id, str):
        followee_id = ObjectId(followee_id)

    if follower_id == followee_id:
        raise ValueError('Cannot follow yourself')

    db.users.update_one(
        {'_id': follower_id},
        {'$addToSet': {'following': followee_id}}
    )

    db.users.update_one(
        {'_id': followee_id},
        {'$addToSet': {'followers': follower_id}}
    )

def unfollow_user(follower_id, followee_id):
    """Unfollow a user."""
    db = get_db()

    if isinstance(follower_id, str):
        follower_id = ObjectId(follower_id)
    if isinstance(followee_id, str):
        followee_id = ObjectId(followee_id)

    db.users.update_one(
        {'_id': follower_id},
        {'$pull': {'following': followee_id}}
    )

    db.users.update_one(
        {'_id': followee_id},
        {'$pull': {'followers': follower_id}}
    )

def get_followers(user_id):
    """Get list of followers for a user."""
    db = get_db()

    if isinstance(user_id, str):
        user_id = ObjectId(user_id)

    user = db.users.find_one({'_id': user_id})
    if not user:
        return []

    follower_ids = user.get('followers', [])
    return list(db.users.find({'_id': {'$in': follower_ids}}))

def get_following(user_id):
    """Get list of users that a user is following."""
    db = get_db()

    if isinstance(user_id, str):
        user_id = ObjectId(user_id)

    user = db.users.find_one({'_id': user_id})
    if not user:
        return []

    following_ids = user.get('following', [])
    return list(db.users.find({'_id': {'$in': following_ids}}))

def search_users(query):
    """Search for users by username."""
    db = get_db()
    return list(db.users.find({
        'username': {'$regex': query, '$options': 'i'}
    }).limit(20))

def is_following(follower_id, followee_id):
    """Check if a user is following another user."""
    db = get_db()

    if isinstance(follower_id, str):
        follower_id = ObjectId(follower_id)
    if isinstance(followee_id, str):
        followee_id = ObjectId(followee_id)

    user = db.users.find_one({'_id': follower_id})
    if not user:
        return False

    return followee_id in user.get('following', [])

def validate_password(password):
    """Validate password meets requirements."""
    if len(password) < 8:
        raise ValueError('Password must be at least 8 characters long')

    if not re.search(r'[A-Za-z]', password):
        raise ValueError('Password must contain at least one letter')

    if not re.search(r'\d', password):
        raise ValueError('Password must contain at least one number')

def change_password(user_id, current_password, new_password):
    """Change a user's password."""
    db = get_db()

    if isinstance(user_id, str):
        user_id = ObjectId(user_id)

    user = db.users.find_one({'_id': user_id})
    if not user:
        raise ValueError('User not found')

    if not check_password_hash(user['password_hash'], current_password):
        raise ValueError('Current password is incorrect')

    validate_password(new_password)

    db.users.update_one(
        {'_id': user_id},
        {'$set': {'password_hash': generate_password_hash(new_password)}}
    )
