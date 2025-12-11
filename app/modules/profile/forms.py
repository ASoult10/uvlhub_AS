from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Regexp


class UserProfileForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=100)])
    surname = StringField("Surname", validators=[DataRequired(), Length(max=100)])
    orcid = StringField(
        "ORCID",
        filters=[lambda x: x.strip() if x else x],  

        validators=[
            Optional(),
            Regexp(r"^\d{4}-\d{4}-\d{4}-\d{4}$", message="Invalid ORCID format"),
        ],
    )
    affiliation = StringField("Affiliation", validators=[Optional(), Length(min=5, max=100)])
    submit = SubmitField("Save profile")
