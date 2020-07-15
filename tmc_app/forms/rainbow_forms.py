from flask_wtf import FlaskForm
from wtforms import SubmitField, TextField
from wtforms.validators import DataRequired


class SaveRainbowForm(FlaskForm):
    gradient = TextField(
        'Gradient',
        validators=[
            DataRequired(),
        ]
    )
    submit = SubmitField('Add Project')
