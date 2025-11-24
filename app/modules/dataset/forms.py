from flask_wtf import FlaskForm
from wtforms import DateField, FieldList, FloatField, FormField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import URL, DataRequired, Optional

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


class FeatureModelForm(FlaskForm):
    # TODO: quitar FeatureModelForm
    uvl_filename = StringField("UVL Filename", validators=[DataRequired()])
    title = StringField("Title", validators=[Optional()])
    desc = TextAreaField("Description", validators=[Optional()])
    publication_type = SelectField(
        "Publication type",
        choices=[(pt.value, pt.name.replace("_", " ").title()) for pt in PublicationType],
        validators=[Optional()],
    )
    publication_doi = StringField("Publication DOI", validators=[Optional(), URL()])
    tags = StringField("Tags (separated by commas)")
    version = StringField("UVL Version")
    authors = FieldList(FormField(AuthorForm))

    class Meta:
        csrf = False  # disable CSRF because is subform

    def get_authors(self):
        return [author.get_author() for author in self.authors]

    def get_fmmetadata(self):
        return {
            "uvl_filename": self.uvl_filename.data,
            "title": self.title.data,
            "description": self.desc.data,
            "publication_type": self.publication_type.data,
            "publication_doi": self.publication_doi.data,
            "tags": self.tags.data,
            "uvl_version": self.version.data,
        }


class ObservationForm(FlaskForm):
    """ Formulario para una observación asociada a un dataset. """
    object_name = StringField("Object name", validators=[DataRequired()])
    ra = StringField("RA (hh:mm:ss.sss)", validators=[DataRequired()])
    dec = StringField("DEC (+/-dd:mm:ss.sss)", validators=[DataRequired()])
    magnitude = FloatField("Magnitude", validators=[Optional()])
    observation_date = DateField("Observation date", validators=[DataRequired()])
    filter_used = StringField("Filter used", validators=[Optional()])
    notes = TextAreaField("Notes", validators=[Optional()])


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
    feature_models = FieldList(FormField(FeatureModelForm), min_entries=1)  # TODO: quitar feature_models de DataSetForm
    observations = FieldList(FormField(ObservationForm), min_entries=1)

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

    def get_feature_models(self):
        # TODO: quitar feature_models de DataSetForm
        return [fm.get_feature_model() for fm in self.feature_models]

    def get_observations(self):
        """ Devuelve una lista de diccionarios con los datos de las observaciones. """
        return [obs.get_observation() for obs in self.observations]
