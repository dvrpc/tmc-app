from pathlib import Path
from flask import Blueprint, redirect, url_for, flash, request, send_file
from flask_login import login_required
import zipfile
from os import environ
from tmc_app import db
from datetime import datetime
from dotenv import load_dotenv, find_dotenv

from tmc_app.models import (
    OutputFile,
    TMCFile,
    Project
)

load_dotenv(find_dotenv())
SUMMARY_FILE_FOLDER = environ.get("SUMMARY_FILE_FOLDER")
RAW_DATA_FOLDER = environ.get("RAW_DATA_FOLDER")


# Blueprint Configuration
download_bp = Blueprint(
    'download_bp', __name__,
    template_folder='templates',
    static_folder='static'
)


@download_bp.route('/download/output/<outputfile_id>', methods=['GET'])
@login_required
def download_output(outputfile_id):

    output_file = OutputFile.query.filter_by(
        uid=outputfile_id
    ).first()

    file_to_send = Path(SUMMARY_FILE_FOLDER) / output_file.filename

    return send_file(file_to_send, as_attachment=True)



@download_bp.route('/download/raw-tmc/<tmc_id>', methods=['GET'])
@login_required
def download_tmc(tmc_id):

    tmc_file = TMCFile.query.filter_by(
        uid=tmc_id
    ).first()
    
    project = Project.query.filter_by(
        uid=tmc_file.project_id
    ).first()

    file_to_send = Path(RAW_DATA_FOLDER) / project.safe_folder_name() / tmc_file.name

    return send_file(file_to_send, as_attachment=True)
