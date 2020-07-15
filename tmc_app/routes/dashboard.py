"""Logged-in page routes."""
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import current_user, login_required

from tmc_app import make_random_gradient, db

from tmc_app.models import (
    User,
    Project,
    TMCFile
)

from tmc_app.forms import AddProjectForm, SaveRainbowForm

# Blueprint Configuration
main_bp = Blueprint(
    'main_bp', __name__,
    template_folder='templates',
    static_folder='static'
)


@main_bp.route('/my-projects', methods=['GET'])
@login_required
def dashboard():
    """Logged-in User landing page"""

    form = AddProjectForm()

    your_projects = Project.query.filter_by(
        created_by=current_user.id
    ).all()

    other_projects = Project.query.filter(
        Project.created_by != current_user.id
    ).all()

    return render_template(
        'dashboard.html',
        make_random_gradient=make_random_gradient,
        form=form,
        your_projects=your_projects,
        other_projects=other_projects
    )


@main_bp.route('/my-projects/add', methods=['POST'])
@login_required
def add_project():
    """Logged-in User landing page"""

    # Add the project if inputs are valid
    form = AddProjectForm()
    if form.validate_on_submit():
        project = Project(
            name=form.name.data,
            description=form.description.data,
            created_by=current_user.id
        )

        db.session.add(project)
        db.session.commit()

        flash(f"Added Project: {form.name.data}", "success")

        return redirect(url_for('main_bp.dashboard'))

    else:
        for error in form.name.errors:
            flash(error, "danger")
        for error in form.description.errors:
            flash(error, "danger")

        return redirect(url_for('main_bp.dashboard'))


@main_bp.route('/rainbows', methods=['GET'])
@login_required
def rainbows():
    return render_template(
        'rubens_rainbows.html',
        this_gradient=make_random_gradient(),
        form=SaveRainbowForm()
    )


@main_bp.route('/save/rainbow', methods=['POST'])
@login_required
def save_rainbow():

    form = SaveRainbowForm()

    current_user.background = form.gradient.data
    db.session.commit()

    return redirect(url_for('main_bp.dashboard'))