from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField
from wtforms.validators import DataRequired


class SaveRainbowForm(FlaskForm):
    gradient = StringField(
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
