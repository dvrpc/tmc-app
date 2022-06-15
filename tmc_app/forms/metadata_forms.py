from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField


class UpdateMetadataForm(FlaskForm):

    title = StringField("Title")
    model_id = IntegerField("model ID")
    lat = StringField("lat")
    lng = StringField("lng")
    legs = StringField("legs")

    submit = SubmitField('Update Metadata')
