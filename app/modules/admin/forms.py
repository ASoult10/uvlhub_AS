from flask_wtf import FlaskForm
from wtforms import SelectMultipleField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, Regexp


class DeleteUserForm(FlaskForm):
    pass


class EditUserForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    name = StringField("Name", validators=[DataRequired(), Length(max=100)])
    surname = StringField("Surname", validators=[DataRequired(), Length(max=100)])

    orcid = StringField(
        "ORCID",
        validators=[
            Optional(),
            Length(min=19, max=19, message="ORCID must be 19 characters long."),
            Regexp(r"^\d{4}-\d{4}-\d{4}-\d{4}$", message="ORCID must be in the format XXXX-XXXX-XXXX-XXXX."),
        ],
    )

    affiliation = StringField("Affiliation", validators=[Optional(), Length(min=5, max=100)])

    roles = SelectMultipleField("Roles", coerce=int, validators=[])

    submit = SubmitField("Save Changes")
