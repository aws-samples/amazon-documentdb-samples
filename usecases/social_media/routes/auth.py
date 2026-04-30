from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import user as user_model

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form.get('username')
        password = request.form.get('password')

        user = user_model.find_user_by_username(username_or_email)
        if not user:
            user = user_model.find_user_by_email(username_or_email)

        if user and user_model.verify_password(user, password):
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            flash('Successfully logged in!', 'success')
            return redirect(url_for('posts.timeline'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        display_name = request.form.get('display_name')
        bio = request.form.get('bio')

        try:
            user_id = user_model.create_user(
                username=username,
                email=email,
                password=password,
                display_name=display_name,
                bio=bio
            )
            session['user_id'] = str(user_id)
            session['username'] = username
            flash('Account created successfully!', 'success')
            return redirect(url_for('posts.timeline'))
        except ValueError as e:
            flash(str(e), 'error')

    return render_template('register.html')

@bp.route('/logout')
def logout():
    session.clear()
    flash('Successfully logged out', 'success')
    return redirect(url_for('auth.login'))

@bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        flash('Please log in to change your password', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return render_template('change_password.html')

        try:
            user_model.change_password(session['user_id'], current_password, new_password)
            flash('Password changed successfully!', 'success')
            return redirect(url_for('posts.timeline'))
        except ValueError as e:
            flash(str(e), 'error')

    return render_template('change_password.html')
