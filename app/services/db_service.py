"""
Database service — upsert / deduplication logic.
"""

from datetime import datetime
from app import db
from app.models import Satellite, TLEElement, Upload


def upsert_tle_records(
    parsed_records: list[dict],
    filename: str,
    source: str = "user_upload",
    is_seed: bool = False,
    label: str | None = None,
) -> dict:
    """
    Persist a list of parsed TLE dicts into the database.
    Deduplicates on (norad_cat_id, epoch_datetime).

    Returns a summary dict with counts for the upload report.
    """
    new_satellites = 0
    updated_satellites = 0
    duplicate_epochs = 0
    new_elements = 0
    parse_errors = 0

    # Create the upload audit record first
    upload = Upload(
        filename=filename,
        upload_time=datetime.utcnow(),
        total_records_in_file=len(parsed_records),
        source=source,
        is_seed=is_seed,
        label=label,
    )
    db.session.add(upload)
    db.session.flush()  # get upload.id

    for rec in parsed_records:
        if rec is None:
            parse_errors += 1
            continue

        norad_id = rec["norad_cat_id"]

        # ── Upsert satellite ──────────────────────────────────────────────────
        satellite = Satellite.query.filter_by(norad_cat_id=norad_id).first()
        is_new_satellite = satellite is None

        if satellite is None:
            satellite = Satellite(
                norad_cat_id=norad_id,
                name=rec["name"],
                classification=rec.get("classification", "U"),
                int_designator=rec.get("int_designator", ""),
                first_seen=datetime.utcnow(),
                last_updated=datetime.utcnow(),
            )
            db.session.add(satellite)
            db.session.flush()  # get satellite.id
            new_satellites += 1
        else:
            # Update mutable metadata
            satellite.name = rec["name"]
            satellite.last_updated = datetime.utcnow()
            updated_satellites += 1

        # ── Dedup on epoch ────────────────────────────────────────────────────
        epoch_dt = rec["epoch_datetime"]
        existing_element = TLEElement.query.filter_by(
            satellite_id=satellite.id,
            epoch_datetime=epoch_dt,
        ).first()

        if existing_element is not None:
            duplicate_epochs += 1
            continue

        # ── Insert TLE element ────────────────────────────────────────────────
        element = TLEElement(
            satellite_id=satellite.id,
            upload_id=upload.id,
            epoch_year=rec.get("epoch_year"),
            epoch_day=rec.get("epoch_day"),
            epoch_datetime=epoch_dt,
            mean_motion_dot=rec.get("mean_motion_dot"),
            mean_motion_ddot=rec.get("mean_motion_ddot"),
            bstar_drag=rec.get("bstar_drag"),
            element_set_number=rec.get("element_set_number"),
            checksum_l1=rec.get("checksum_l1"),
            inclination_deg=rec.get("inclination_deg"),
            raan_deg=rec.get("raan_deg"),
            eccentricity=rec.get("eccentricity"),
            arg_of_perigee_deg=rec.get("arg_of_perigee_deg"),
            mean_anomaly_deg=rec.get("mean_anomaly_deg"),
            mean_motion_rev_day=rec.get("mean_motion_rev_day"),
            rev_number=rec.get("rev_number"),
            checksum_l2=rec.get("checksum_l2"),
            raw_line1=rec.get("raw_line1"),
            raw_line2=rec.get("raw_line2"),
        )
        db.session.add(element)
        new_elements += 1

    # Update upload audit record
    upload.new_satellites = new_satellites
    upload.updated_satellites = updated_satellites
    upload.duplicate_epochs = duplicate_epochs

    db.session.commit()

    return {
        "upload_id": upload.id,
        "filename": filename,
        "total_in_file": len(parsed_records),
        "new_satellites": new_satellites,
        "updated_satellites": updated_satellites,
        "new_elements": new_elements,
        "duplicate_epochs": duplicate_epochs,
        "parse_errors": parse_errors,
    }
