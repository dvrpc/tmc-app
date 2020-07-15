from flask_wtf import FlaskForm
from wtforms import SubmitField, TextField, StringField
from wtforms.validators import DataRequired


class SaveRainbowForm(FlaskForm):
    gradient = TextField(
        'Gradient',
        validators=[
            DataRequired(),
        ]
    )
    location = StringField(
        "Where to save this gradient",
        validators=[
            DataRequired()
        ]
    )

    submit = SubmitField('Add Project')
