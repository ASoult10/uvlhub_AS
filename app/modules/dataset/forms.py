from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed

from wtforms import (
    DateField,
    FieldList,
    FloatField,
    FormField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import URL, DataRequired, Optional
import re

from app.modules.dataset.models import PublicationType


class AuthorForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    affiliation = StringField("Affiliation")
    orcid = StringField("ORCID")
    gnd = StringField("GND")

    class Meta:
        csrf = False  # disable CSRF because is subform

    def get_author(self):
        return {
            "name": self.name.data,
            "affiliation": self.affiliation.data,
            "orcid": self.orcid.data,
        }


class ObservationForm(FlaskForm):
    """Formulario para una observación asociada a un dataset."""
    object_name = StringField("Object name", validators=[Optional()])
    ra = StringField("RA (hh:mm:ss.sss)", validators=[Optional()])
    dec = StringField("DEC (+/-dd:mm:ss.sss)", validators=[Optional()])
    magnitude = FloatField("Magnitude", validators=[Optional()])
    observation_date = DateField("Observation date", validators=[Optional()])
    filter_used = StringField("Filter used", validators=[Optional()])
    notes = TextAreaField("Notes", validators=[Optional()])

    class Meta:
        csrf = False 

    def is_empty(self):
        """Devuelve True si todos los campos están vacíos."""
        return not (
            (self.object_name.data and self.object_name.data.strip()) or
            (self.ra.data and self.ra.data.strip()) or
            (self.dec.data and self.dec.data.strip()) or
            self.observation_date.data or
            self.magnitude.data is not None or
            (self.filter_used.data and self.filter_used.data.strip()) or
            (self.notes.data and self.notes.data.strip())
        )    

    def get_observation(self):
        """Devuelve un dict con los datos de la observación."""
        return {
            "object_name": (self.object_name.data or "").strip(),
            "ra": (self.ra.data or "").strip(),
            "dec": (self.dec.data or "").strip(),
            "magnitude": self.magnitude.data,
            "observation_date": self.observation_date.data,
            "filter_used": (self.filter_used.data or "").strip(),
            "notes": (self.notes.data or "").strip(),
        }

    def validate(self, extra_validators=None):
        rv = super().validate(extra_validators=extra_validators)

        if self.is_empty():
            return True

        has_error = False

        if not (self.object_name.data and self.object_name.data.strip()):
            self.object_name.errors.append("Object name is required for an observation.")
            has_error = True

        if not (self.ra.data and self.ra.data.strip()):
            self.ra.errors.append("RA is required for an observation.")
            has_error = True

        if not (self.dec.data and self.dec.data.strip()):
            self.dec.errors.append("DEC is required for an observation.")
            has_error = True

        ra_val = (self.ra.data or "").strip()
        dec_val = (self.dec.data or "").strip()

        ra_regex = re.compile(r"^([01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?$")
        dec_regex = re.compile(r"^[+-]?(?:[0-8]?\d|90):[0-5]\d:[0-5]\d(?:\.\d+)?$")

        if ra_val and not ra_regex.match(ra_val):
            self.ra.errors.append("Invalid RA format. Expected hh:mm:ss(.sss) with valid ranges.")
            has_error = True

        if dec_val and not dec_regex.match(dec_val):
            self.dec.errors.append("Invalid DEC format. Expected [+/-]dd:mm:ss(.sss) with valid ranges.")
            has_error = True

        return (rv and not has_error)


class DataSetForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    desc = TextAreaField("Description", validators=[DataRequired()])
    publication_type = SelectField(
        "Publication type",
        choices=[(pt.value, pt.name.replace("_", " ").title()) for pt in PublicationType],
        validators=[DataRequired()],
    )
    publication_doi = StringField("Publication DOI", validators=[Optional(), URL()])
    dataset_doi = StringField("Dataset DOI", validators=[Optional(), URL()])
    tags = StringField("Tags (separated by commas)")
    authors = FieldList(FormField(AuthorForm))
    observation = FormField(ObservationForm)
    #Archivos JSON asociados al dataset
    json_files = FileField("JSON Files",validators=[Optional(), FileAllowed(['json'], "Only JSON files allowed")],render_kw={"multiple": True}
)


    submit = SubmitField("Submit")

    def get_dsmetadata(self):

        publication_type_converted = self.convert_publication_type(self.publication_type.data)

        return {
            "title": self.title.data,
            "description": self.desc.data,
            "publication_type": publication_type_converted,
            "publication_doi": self.publication_doi.data,
            "dataset_doi": self.dataset_doi.data,
            "tags": self.tags.data,
        }

    def convert_publication_type(self, value):
        for pt in PublicationType:
            if pt.value == value:
                return pt.name
        return "NONE"

    def get_authors(self):
        return [author.get_author() for author in self.authors]

    def get_observation(self):
        if self.observation.form.is_empty():
            return None
        return self.observation.form.get_observation()