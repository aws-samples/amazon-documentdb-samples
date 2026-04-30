# Social Network Application

A simple social network application built with Flask and Amazon DocumentDB. Users can create profiles, make posts, follow other users, and view a timeline of posts from users they follow.

## Features

- User authentication (register, login, logout)
- User profiles with bio and display name
- Follow/unfollow functionality
- Create and delete posts
- Timeline view showing posts from followed users
- User search by username
- Server-side rendered UI with Jinja2 templates

## Tech Stack

- **Backend**: Python 3.x with Flask
- **Frontend**: Jinja2 templates with vanilla CSS
- **Database**: Amazon DocumentDB or any MongoDB API compatible database
- **Driver**: PyMongo

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and configure your DocumentDB connection:

```bash
cp .env.example .env
```

Edit `.env` and set your DocumentDB connection string and session secret:

```
DOCDB_URI=mongodb://<user>:<pass>@<endpoint>:27017/?tls=true&tlsCAFile=global-bundle.pem&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false
SESSION_SECRET=<random-string-change-this-in-production>
FLASK_APP=app.py
FLASK_PORT=3000
```

**Important**: If you need to use TLS with a CA bundle, download the Amazon RDS CA certificate:

```bash
wget https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
```

### 3. Seed the Database

Create indexes and populate sample data:

```bash
python scripts/seed.py
```

This will create 4 sample users and some posts. All sample users have the password `password123`.

### 4. Run the Application

```bash
flask run
```

Or directly:

```bash
python app.py
```

The application will be available at `http://localhost:3000`

## Sample Users

After seeding, you can login with any of these accounts (password: `password123`):

- alice@example.com (@alice)
- bob@example.com (@bob)
- charlie@example.com (@charlie)
- diana@example.com (@diana)

## Project Structure

```
social/
├── app.py                 # Flask app entry point
├── requirements.txt       # Python dependencies
├── .env                   # Environment configuration (not committed)
├── routes/
│   ├── auth.py            # Login, register, logout
│   ├── users.py           # Profile, follow/unfollow
│   ├── posts.py           # Create, delete, timeline
│   └── search.py          # User search
├── models/
│   ├── db.py              # DocumentDB connection management
│   ├── user.py            # User data access
│   └── post.py            # Post data access
├── templates/
│   ├── layout.html        # Base layout
│   ├── login.html
│   ├── register.html
│   ├── timeline.html
│   ├── profile.html
│   └── search.html
├── static/
│   └── css/
│       └── style.css
└── scripts/
    └── seed.py            # Seed data for development
```

## Development

The application runs in debug mode by default when using `python app.py`. For production deployment:

1. Set a strong `SESSION_SECRET` value
2. Disable debug mode
3. Use a production WSGI server (gunicorn, uwsgi)
4. Configure proper TLS certificates
5. Set up appropriate security groups and network access controls
