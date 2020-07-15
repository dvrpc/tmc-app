from pathlib import Path
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from tmc_app import make_random_gradient, db

from tmc_app.models import (
    User,
    Project,
    TMCFile
)

from tmc_app.forms.upload_forms import UploadFilesForm

# Blueprint Configuration
project_bp = Blueprint(
    'project_bp', __name__,
    template_folder='templates',
    static_folder='static'
)


@project_bp.route('/project/<project_id>', methods=['GET'])
@login_required
def single_project(project_id):

    project = Project.query.filter_by(
        uid=project_id
    ).first()

    files = TMCFile.query.filter_by(
        project_id=project_id
    ).order_by(TMCFile.name).all()

    form = UploadFilesForm()

    return render_template(
        'single_project.html',
        make_random_gradient=make_random_gradient,
        project=project,
        files=files,
        form=form
    )



@project_bp.route('/project/<project_id>/save', methods=['POST'])
@login_required
def upload_file(project_id):

    form = UploadFilesForm()

    if form.validate_on_submit():

        file_list = request.files.getlist("files")

        project = Project.query.filter_by(uid=project_id).first()

        # Make a path to a subfolder for this session's uploads
        data_path = Path("data") / project.safe_folder_name()

        if not data_path.exists():
            data_path.mkdir(parents=True)

        # Upload files if the user provided any
        if file_list[0].filename != '':

            # Save each file to the app's upload folder
            for f in file_list:
                filepath = data_path / secure_filename(f.filename)
                f.save(filepath)

                tmc_file = TMCFile(
                    name=f.filename,
                    project_id=project_id,
                    uploaded_by=current_user.id
                )
                db.session.add(tmc_file)
                db.session.commit()

                flash(f"Saved {f.filename}", "success")

    else:
        for error in form.files.errors:
            flash(error, "danger")

    return redirect(url_for('project_bp.single_project', project_id=project_id))


@project_bp.route('/project/<project_id>/delete/<file_id>', methods=['POST'])
@login_required
def delete_file(project_id, file_id):

    project = Project.query.filter_by(uid=project_id).first()
    tmc_file = TMCFile.query.filter_by(uid=file_id).first()

    filepath = Path("data") / project.safe_folder_name() / tmc_file.name
    filepath.unlink()

    db.session.delete(tmc_file)
    db.session.commit()

    flash(f"Deleted {tmc_file.name}", "info")

    return redirect(url_for('project_bp.single_project', project_id=project_id))
