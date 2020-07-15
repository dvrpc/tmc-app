"""Sign-up & log-in forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class AddProjectForm(FlaskForm):
    name = StringField(
        'Name',
        validators=[
            DataRequired(),
            Length(max=25)
        ]
    )
    description = StringField(
        'Description',
        validators=[
            Length(max=50),
            DataRequired()
        ]
    )
    submit = SubmitField('Add Project')
