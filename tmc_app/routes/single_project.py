# Environment variables
from os import environ
from dotenv import load_dotenv, find_dotenv

# Flask stuff
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

# General helpers
from pathlib import Path

# Plotting
import json
import plotly
import plotly.graph_objects as go

# Project imports
from tmc_app import make_random_gradient, db
from tmc_app.models.upload_model import SQLUpload
from tmc_app.models import Project, TMCFile, OutputFile


from tmc_app.forms.upload_forms import UploadFilesForm
from tmc_app.forms.metadata_forms import UpdateMetadataForm

load_dotenv(find_dotenv())
SQLALCHEMY_DATABASE_URI = environ.get("SQLALCHEMY_DATABASE_URI")
MAPBOX_TOKEN = environ.get("MAPBOX_TOKEN")
RAW_DATA_FOLDER = environ.get("RAW_DATA_FOLDER")


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
    ).order_by(TMCFile.filename).all()

    summary_files = OutputFile.query.filter_by(
        project_id=project_id
    ).order_by(OutputFile.created_on.desc()).all()

    form = UploadFilesForm()

    if len(project.files) == 0:
        data = [
            go.Bar(
                name="Placeholder data",
                x=[6,7,8,9,10,11,12,13,14,15,16,17,18,19,20],
                y=[10,12,15,14,13,11,9,4,7,8,12,14,18,17,16])
        ]
        plot_title = "No data yet! Upload TMC files and this graph will refresh itself."

    else:
        plot_title = f"{project.name}: data from {len(project.files)} files"
        # Get the full timeseries dataset for this project
        df_timeseries = project.generate_timeseries_data().sort_index()

        # Add a sum column for each row
        df_timeseries["total_15_min"] = df_timeseries.iloc[:, 1:].sum(axis=1)
        
        # Make a bar plot of the counts in this project
        # This is a stacked bar graph, so we're making a list of go.Bar() objects
        # This gets turned into JSON, and styled  JS directly in the HTML tempalte
        data = []
        for location in df_timeseries.location.unique():
            filtered_df = df_timeseries[df_timeseries.location == location]
            data.append(go.Bar(name=location, x=filtered_df.index, y=filtered_df["total_15_min"]))

    graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)

    # Get lat lngs if they exist
    latlng_data = [[f.lat, f.lng, f.name()] for f in project.files if f.lat]

    return render_template(
        'single_project.html',
        make_random_gradient=make_random_gradient,
        project=project,
        files=files,
        form=form,
        summary_files=summary_files,
        fig=graphJSON,
        graph_title=plot_title,
        latlngs=json.dumps(latlng_data)
    )


@project_bp.route('/project/<project_id>/save-raw-data', methods=['POST'])
@login_required
def upload_file(project_id):

    form = UploadFilesForm()

    if form.validate_on_submit():

        file_list = request.files.getlist("files")

        project = Project.query.filter_by(uid=project_id).first()

        # Make a path to a subfolder for this session's uploads
        data_path = Path(RAW_DATA_FOLDER) / project.safe_folder_name()

        if not data_path.exists():
            data_path.mkdir(parents=True)

        # Upload files if the user provided any
        if file_list[0].filename != '':

            # Save each file to the app's upload folder
            for f in file_list:
                filepath = data_path / secure_filename(f.filename)
                f.save(filepath)
                print("Saved", filepath)

                tmc_file = TMCFile(
                    filename=f.filename,
                    project_id=project_id,
                    uploaded_by=current_user.id
                )
                db.session.add(tmc_file)
                db.session.commit()

                # Import the data into SQL
                tmc_uploader = SQLUpload(project_id, tmc_file.uid, filepath)
                tmc_uploader.publish_to_database()

                # Extract the metadata from the Excel file
                metadata = tmc_file.extract_metadata()

                tmc_file.title = metadata["title"]
                tmc_file.legs = str(metadata["legs"])
                tmc_file.data_date = metadata["data_date"]
                tmc_file.start_time = metadata["start_time"]
                tmc_file.end_time = metadata["end_time"]

                db.session.commit()

            flash(f"Saved {len(file_list)} files to server", "success")


            # After importing all files, recreate the project table
            project.create_project_table()
            flash(f"Updated project-wide SQL table with new files", "info")

    else:
        for error in form.files.errors:
            flash(error, "danger")

    return redirect(url_for('project_bp.single_project', project_id=project_id))


@project_bp.route('/project/<project_id>/delete/<file_id>', methods=['GET'])
@login_required
def delete_file(project_id, file_id):

    project = Project.query.filter_by(uid=project_id).first()
    tmc_file = TMCFile.query.filter_by(uid=file_id).first()

    filepath = Path("data") / project.safe_folder_name() / tmc_file.filename
    filepath.unlink()

    db.session.delete(tmc_file)
    db.session.commit()

    flash(f"Deleted {tmc_file.name() }", "warning")

    return redirect(url_for('project_bp.single_project', project_id=project_id))


@project_bp.route('/project/<project_id>/summarize', methods=['GET'])
@login_required
def summarize_files(project_id):

    project = Project.query.filter_by(uid=project_id).first()

    src_data_path = Path("data") / project.safe_folder_name()

    # # Execute the analysis code from the pure-python repository
    # xlsx_path, geojson_path = write_summary_file(
    #     src_data_path,
    #     output_folder=Path("data-outputs")
    # )

    # # Log the two output files in the DB
    # xlsx = OutputFile(
    #     filename=str(xlsx_path.name),
    #     analysis_type="Excel File",
    #     project_id=project_id,
    #     created_by=current_user.id
    # )

    # geojson = OutputFile(
    #     filename=str(geojson_path.name),
    #     analysis_type="GeoJSON File",
    #     project_id=project_id,
    #     created_by=current_user.id
    # )

    # db.session.add(xlsx)
    # db.session.add(geojson)
    # db.session.commit()

    flash("Summary files are ready for download", "success")

    return redirect(url_for('project_bp.single_project', project_id=project_id))


@project_bp.route('/project/<project_id>/metadata/<file_id>', methods=['GET'])
@login_required
def metadata(project_id, file_id):

    project = Project.query.filter_by(
        uid=project_id
    ).first()

    this_file = TMCFile.query.filter_by(
        uid=file_id,
        project_id=project_id
    ).first()

    if this_file.lat:
        latlng = [this_file.lat, this_file.lng]
    else:
        latlng = [39.952297, -75.163743]

    form = UpdateMetadataForm()

    return render_template(
        'metadata.html',
        this_file=this_file,
        project=project,
        form=form,
        latlng=json.dumps(latlng),
        MAPBOX_TOKEN=MAPBOX_TOKEN
    )


@project_bp.route('/project/<project_id>/metadata/<file_id>/update', methods=['POST'])
@login_required
def update_metadata(project_id, file_id):

    this_file = TMCFile.query.filter_by(
        uid=file_id,
        project_id=project_id
    ).first()

    form = UpdateMetadataForm()

    this_file.title = str(form.title.data)
    if form.model_id.data:
        if type(form.model_id.data) == int:
            this_file.model_id = int(form.model_id.data)

    this_file.lat = str(form.lat.data)
    this_file.lng = str(form.lng.data)
    this_file.legs = str(form.legs.data)

    db.session.commit()

    flash(f"Updated metadata for {this_file.name()}", "success")

    return redirect(url_for('project_bp.single_project', project_id=project_id))