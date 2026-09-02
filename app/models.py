from app import db
from datetime import datetime
import enum


class Upload(db.Model):
    """Audit record for each file upload / ingest session."""
    __tablename__ = "uploads"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.Text, nullable=False)
    upload_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    total_records_in_file = db.Column(db.Integer, default=0)
    new_satellites = db.Column(db.Integer, default=0)
    updated_satellites = db.Column(db.Integer, default=0)
    duplicate_epochs = db.Column(db.Integer, default=0)
    # Provenance fields
    source = db.Column(db.Text, default="user_upload")   # 'seed' | 'user_upload'
    is_seed = db.Column(db.Boolean, default=False, nullable=False)
    label = db.Column(db.Text)                            # Optional human-readable session label

    tle_elements = db.relationship("TLEElement", back_populates="upload",
                                   lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Upload {self.filename} @ {self.upload_time}>"


class Satellite(db.Model):
    """One row per unique satellite (identified by NORAD catalog number)."""
    __tablename__ = "satellites"

    id = db.Column(db.Integer, primary_key=True)
    norad_cat_id = db.Column(db.Integer, unique=True, nullable=False, index=True)
    name = db.Column(db.Text, nullable=False)
    classification = db.Column(db.String(1))          # U=Unclassified, C=Classified, S=Secret
    int_designator = db.Column(db.Text)               # e.g. "98067A" = ISS launch 1998
    first_seen = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tle_elements = db.relationship("TLEElement", back_populates="satellite", lazy="dynamic",
                                   cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Satellite {self.norad_cat_id} {self.name}>"


class TLEElement(db.Model):
    """
    One row per unique (satellite, epoch) combination.
    Stores every parsed field from TLE Line 1 and Line 2.
    """
    __tablename__ = "tle_elements"
    __table_args__ = (
        db.UniqueConstraint("satellite_id", "epoch_datetime", name="uq_sat_epoch"),
    )

    id = db.Column(db.Integer, primary_key=True)
    satellite_id = db.Column(db.Integer, db.ForeignKey("satellites.id"), nullable=False, index=True)
    upload_id = db.Column(db.Integer, db.ForeignKey("uploads.id"), nullable=True)

    # ── Epoch ────────────────────────────────────────────────────────────────
    epoch_year = db.Column(db.Integer)          # 2-digit year (e.g. 98 = 1998)
    epoch_day = db.Column(db.Float)             # Day of year + fractional day
    epoch_datetime = db.Column(db.DateTime, nullable=False)   # Derived full UTC datetime

    # ── Line 1 fields ────────────────────────────────────────────────────────
    mean_motion_dot = db.Column(db.Float)       # 1st time derivative of mean motion (rev/day²)
    mean_motion_ddot = db.Column(db.Float)      # 2nd time derivative of mean motion (rev/day³)
    bstar_drag = db.Column(db.Float)            # BSTAR drag term (1/earth-radii) — atmospheric drag proxy
    element_set_number = db.Column(db.Integer)  # TLE set version counter
    checksum_l1 = db.Column(db.Integer)         # Modulo-10 checksum of line 1

    # ── Line 2 fields ────────────────────────────────────────────────────────
    inclination_deg = db.Column(db.Float)       # Orbital inclination (degrees, 0–180)
    raan_deg = db.Column(db.Float)              # Right Ascension of Ascending Node (degrees)
    eccentricity = db.Column(db.Float)          # Orbital eccentricity (0 = circular, 1 = parabolic)
    arg_of_perigee_deg = db.Column(db.Float)    # Argument of perigee (degrees)
    mean_anomaly_deg = db.Column(db.Float)      # Mean anomaly at epoch (degrees)
    mean_motion_rev_day = db.Column(db.Float)   # Mean motion (revolutions per day)
    rev_number = db.Column(db.Integer)          # Revolution number at epoch
    checksum_l2 = db.Column(db.Integer)         # Modulo-10 checksum of line 2

    # ── Raw data ─────────────────────────────────────────────────────────────
    raw_line1 = db.Column(db.Text)
    raw_line2 = db.Column(db.Text)

    # ── Relationships ─────────────────────────────────────────────────────────
    satellite = db.relationship("Satellite", back_populates="tle_elements")
    upload = db.relationship("Upload", back_populates="tle_elements")

    def __repr__(self):
        return f"<TLEElement sat={self.satellite_id} epoch={self.epoch_datetime}>"


class SystemSetting(db.Model):
    """
    Simple key-value store for application-level settings.
    Used to persist flags like whether the seed data has been imported.
    """
    __tablename__ = "system_settings"

    key = db.Column(db.Text, primary_key=True)
    value = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<SystemSetting {self.key}={self.value}>"
