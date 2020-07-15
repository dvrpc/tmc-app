from wtforms import MultipleFileField
from flask_wtf import FlaskForm


class UploadFilesForm(FlaskForm):
    files = MultipleFileField()
