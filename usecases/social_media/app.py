import os
from flask import Flask, redirect, url_for
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SESSION_SECRET', 'dev-secret-key-change-in-production')

from routes import auth, users, posts, search

app.register_blueprint(auth.bp)
app.register_blueprint(users.bp)
app.register_blueprint(posts.bp)
app.register_blueprint(search.bp)

@app.errorhandler(404)
def not_found(e):
    return 'Page not found', 404

@app.errorhandler(500)
def server_error(e):
    return 'Internal server error', 500

if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=True)
