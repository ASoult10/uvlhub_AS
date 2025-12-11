from flask_wtf import FlaskForm
from wtforms import DateTimeLocalField, SelectMultipleField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


class ApiKeyForm(FlaskForm):
    name = StringField(
        "Name",
        validators=[DataRequired(), Length(min=3, max=100)],
        render_kw={"placeholder": "e.g., My Research Project"},
    )

    scopes = SelectMultipleField(
        "Permissions",
        choices=[
            ("read:datasets", "Read Datasets"),
            ("write:datasets", "Write Datasets"),
            ("delete:datasets", "Delete Datasets"),
            ("read:stats", "Read Stats"),
        ],
        default=["read:datasets"],
        validators=[DataRequired()],
    )

    expires_at = DateTimeLocalField(
        "Expiration Date (Optional)",
        validators=[Optional()],
        render_kw={"class": "form-control"},
        format="%Y-%m-%dT%H:%M",
    )

    submit = SubmitField("Generate API Key")


class RevokeApiKeyForm(FlaskForm):
    submit = SubmitField("Revoke Key")
