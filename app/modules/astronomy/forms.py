from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, DateField, TextAreaField
from wtforms.validators import DataRequired, Optional

class ObservationForm(FlaskForm):
    object_name = StringField("Object name", validators=[DataRequired()])
    ra = StringField("RA (hh:mm:ss.sss)", validators=[DataRequired()])
    dec = StringField("DEC (+/-dd:mm:ss.sss)", validators=[DataRequired()])
    magnitude = FloatField("Magnitude", validators=[Optional()])
    observation_date = DateField("Observation date", validators=[DataRequired()])
    filter_used = StringField("Filter used", validators=[Optional()])
    notes = TextAreaField("Notes", validators=[Optional()])

class AttachmentForm(FlaskForm):
    file_name = StringField("File name", validators=[DataRequired()])
    type = StringField("Type", validators=[DataRequired()])
    description = TextAreaField("Description", validators=[Optional()])
    size_mb = FloatField("Size (MB)", validators=[Optional()])
