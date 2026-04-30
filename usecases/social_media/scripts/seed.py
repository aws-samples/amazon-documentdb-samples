#!/usr/bin/env python3
"""Seed the database with sample data and create indexes."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.db import get_db
from models.user import create_user, follow_user
from models.post import create_post

def create_indexes():
    """Create required database indexes."""
    db = get_db()

    print("Creating indexes...")

    db.users.create_index('username', unique=True)
    db.users.create_index('email', unique=True)

    db.posts.create_index([('author_id', 1), ('created_at', -1)])
    db.posts.create_index([('created_at', -1)])

    print("Indexes created successfully")

def seed_data():
    """Seed the database with sample users and posts."""
    db = get_db()

    db.users.delete_many({})
    db.posts.delete_many({})
    print("Cleared existing data")

    print("Creating users...")
    alice_id = create_user(
        username='alice',
        email='alice@example.com',
        password='password123',
        display_name='Alice Johnson',
        bio='Software developer and coffee enthusiast'
    )

    bob_id = create_user(
        username='bob',
        email='bob@example.com',
        password='password123',
        display_name='Bob Smith',
        bio='Tech blogger and open source contributor'
    )

    charlie_id = create_user(
        username='charlie',
        email='charlie@example.com',
        password='password123',
        display_name='Charlie Brown',
        bio='Designer and creative thinker'
    )

    diana_id = create_user(
        username='diana',
        email='diana@example.com',
        password='password123',
        display_name='Diana Prince',
        bio='Product manager and tech enthusiast'
    )

    print(f"Created 4 users")

    print("Creating follow relationships...")
    follow_user(alice_id, bob_id)
    follow_user(alice_id, charlie_id)
    follow_user(bob_id, alice_id)
    follow_user(bob_id, diana_id)
    follow_user(charlie_id, alice_id)
    follow_user(charlie_id, bob_id)
    follow_user(diana_id, alice_id)

    print("Follow relationships created")

    print("Creating posts...")
    posts_data = [
        (alice_id, "Just deployed my first Flask app! So excited to share it with everyone."),
        (bob_id, "Working on a new blog post about Python best practices. Stay tuned!"),
        (charlie_id, "Design is not just what it looks like. Design is how it works."),
        (diana_id, "Product management tip: Always listen to your users."),
        (alice_id, "Coffee break! Anyone else need a caffeine boost?"),
        (bob_id, "Open source contribution of the day: Fixed a bug in a popular library."),
        (charlie_id, "New UI mockups are ready for review. Feedback welcome!"),
        (alice_id, "Learning DocumentDB today. The MongoDB compatibility is amazing!"),
        (diana_id, "Roadmap planning session went well. Exciting features coming soon!"),
        (bob_id, "Published my latest article on microservices architecture."),
        (charlie_id, "Typography matters. Small details make a big difference."),
        (alice_id, "Debugging is like being a detective in a crime movie where you're also the murderer."),
        (diana_id, "User research findings are in. Time to prioritize features!"),
        (bob_id, "Code review time. Quality over speed, always."),
        (charlie_id, "Color theory and accessibility - why they should always go together."),
    ]

    for author_id, content in posts_data:
        create_post(author_id, content)

    print(f"Created {len(posts_data)} posts")

if __name__ == '__main__':
    print("Starting database seed...")
    create_indexes()
    seed_data()
    print("\nDatabase seeded successfully!")
    print("\nSample users (all with password 'password123'):")
    print("  - alice@example.com (@alice)")
    print("  - bob@example.com (@bob)")
    print("  - charlie@example.com (@charlie)")
    print("  - diana@example.com (@diana)")
