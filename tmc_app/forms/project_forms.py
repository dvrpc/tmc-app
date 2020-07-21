"""Sign-up & log-in forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class AddProjectForm(FlaskForm):
    name = StringField(
        'Name',
        validators=[
            DataRequired(message="Please provide a project name"),
            Length(max=25, message="Project name must be less than 25 characters")
        ]
    )
    description = StringField(
        'Description',
        validators=[
            Length(max=50, message="Description must be less than 50 characters"),
            DataRequired(message="Please provide a description for the project")
        ]
    )
    submit = SubmitField('Add Project')
