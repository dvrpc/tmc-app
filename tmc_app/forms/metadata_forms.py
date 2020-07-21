from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextField, IntegerField


class UpdateMetadataForm(FlaskForm):

    title = StringField("Title")
    model_id = IntegerField("model ID")
    lat = StringField("lat")
    lng = StringField("lng")
    legs = TextField("legs")

    submit = SubmitField('Update Metadata')
