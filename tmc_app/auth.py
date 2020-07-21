"""Routes for user authentication."""
from flask import Blueprint, redirect, render_template, flash, request, session, url_for
from flask_login import login_required, logout_user, current_user, login_user


from tmc_app.models import db, User
from tmc_app.forms.auth_forms import LoginForm, SignupForm

from . import login_manager


# Blueprint Configuration
auth_bp = Blueprint(
    'auth_bp', __name__,
    template_folder='templates',
    static_folder='static'
)


@auth_bp.route('/', methods=['GET', 'POST'])
def get_started():
    """
    """
    # Bypass if user is logged in
    if current_user.is_authenticated:
        return redirect(url_for('main_bp.dashboard'))  

    login_form = LoginForm()
    signup_form = SignupForm()

    if request.method == 'POST':

        if request.form['submit'] == 'login':


            if login_form.validate_on_submit() and login_form.email.data:
                user = User.query.filter_by(email=login_form.email.data).first()
                if user and user.check_password(password=login_form.password.data):
                    login_user(user)
                    return redirect(url_for('main_bp.dashboard'))

            flash(r'Invalid username/password combination', "danger")

        if request.form['submit'] == 'signup':

            # Validate login attempt
            email_domain = request.form["email"].split("@")[-1]
            if email_domain != "dvrpc.org":
                flash('This application is only accessible to DVRPC employees.', "danger")


            elif signup_form.validate_on_submit() and signup_form.email.data:
                existing_user = User.query.filter_by(email=signup_form.email.data).first()
                if existing_user is None:
                    user = User(
                        name=signup_form.name.data,
                        email=signup_form.email.data
                    )
                    user.set_password(signup_form.password.data)
                    db.session.add(user)
                    db.session.commit()  # Create new user
                    login_user(user)  # Log in as newly created user
                    return redirect(url_for('main_bp.dashboard'))

                flash('A user already exists with that email address.', "danger")

    return render_template(
        'home.html',
        login_form=login_form,
        signup_form=signup_form,
    )


@login_manager.user_loader
def load_user(user_id):
    """Check if user is logged-in on every page load."""
    if user_id is not None:
        return User.query.get(user_id)
    return None


@login_manager.unauthorized_handler
def unauthorized():
    """Redirect unauthorized users to Login page."""
    flash('You must be logged in to view that page.')
    return redirect(url_for('auth_bp.get_started'))


@auth_bp.route('/logout', methods=['GET'])
def logout():
    logout_user()
    return redirect("/")