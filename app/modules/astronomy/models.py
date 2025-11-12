from datetime import datetime
from app import db

class AstronomyObservation(db.Model):
    __tablename__ = "astronomy_observation"
    id = db.Column(db.Integer, primary_key=True)
    data_set_id = db.Column(db.Integer, db.ForeignKey("data_set.id"), nullable=False)

    object_name = db.Column(db.String(255), nullable=False)
    ra = db.Column(db.String(64), nullable=False)   # hh:mm:ss.sss
    dec = db.Column(db.String(64), nullable=False)  # +/-dd:mm:ss.sss
    magnitude = db.Column(db.Float, nullable=True)
    observation_date = db.Column(db.Date, nullable=False)
    filter_used = db.Column(db.String(16), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    dataset = db.relationship(
        "DataSet",
        backref=db.backref("astronomy_observations", lazy=True, cascade="all, delete"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "object_name": self.object_name,
            "ra": self.ra,
            "dec": self.dec,
            "magnitude": self.magnitude,
            "observation_date": self.observation_date.isoformat() if self.observation_date else None,
            "filter_used": self.filter_used,
            "notes": self.notes or "",
        }


class AstronomyAttachment(db.Model):
    __tablename__ = "astronomy_attachment"
    id = db.Column(db.Integer, primary_key=True)
    data_set_id = db.Column(db.Integer, db.ForeignKey("data_set.id"), nullable=False)

    file_name = db.Column(db.String(512), nullable=False)
    type = db.Column(db.String(64), nullable=False)  # image, spectrum, video, csv, etc.
    description = db.Column(db.Text, nullable=True)
    size_mb = db.Column(db.Float, nullable=True)

    dataset = db.relationship(
        "DataSet",
        backref=db.backref("astronomy_attachments", lazy=True, cascade="all, delete"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "file_name": self.file_name,
            "type": self.type,
            "description": self.description or "",
            "size_mb": self.size_mb,
        }
