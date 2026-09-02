"""
TLE (Two-Line Element Set) Parser
==================================
Parses the standard 3-line TLE format into structured Python dicts.

TLE Format reference: https://en.wikipedia.org/wiki/Two-line_element_set
"""

import re
import math
from datetime import datetime, timedelta


def _parse_decimal_packed(s: str) -> float:
    """
    Decode TLE's compacted decimal notation.
    e.g. '-11606-4' → -0.11606e-4 = -1.1606e-5
         ' 00000-0' → 0.0
    """
    s = s.strip()
    # Find the sign of the mantissa
    if s.startswith("-"):
        mantissa_sign = -1
        s = s[1:]
    else:
        mantissa_sign = 1
        if s.startswith("+"):
            s = s[1:]

    # The exponent sign and value are at the end; split on + or -
    match = re.fullmatch(r"(\d+)([+-]\d+)", s)
    if not match:
        return 0.0

    mantissa_str, exp_str = match.group(1), match.group(2)
    mantissa = float("0." + mantissa_str) if mantissa_str else 0.0
    exponent = int(exp_str)
    return mantissa_sign * mantissa * (10 ** exponent)


def _epoch_to_datetime(epoch_year_2d: int, epoch_day: float) -> datetime:
    """Convert 2-digit year + day-of-year fraction to a UTC datetime."""
    year = epoch_year_2d + (2000 if epoch_year_2d < 57 else 1900)
    # epoch_day is 1-based (day 1.0 = Jan 1 00:00 UTC)
    start_of_year = datetime(year, 1, 1)
    delta = timedelta(days=epoch_day - 1)
    return start_of_year + delta


def _compute_checksum(line: str) -> int:
    """Modulo-10 checksum: sum digits + count '-' signs, mod 10."""
    total = 0
    for ch in line[:-1]:  # exclude last char (the checksum digit itself)
        if ch.isdigit():
            total += int(ch)
        elif ch == "-":
            total += 1
    return total % 10


def validate_checksum(line: str) -> bool:
    """Return True if the TLE line checksum is valid."""
    try:
        expected = int(line[-1])
        return _compute_checksum(line) == expected
    except (ValueError, IndexError):
        return False


def parse_tle_file(content: str) -> list[dict]:
    """
    Parse a TLE file content string.
    Returns a list of dicts, one per TLE record.
    Handles both 3-line (name + L1 + L2) and 2-line (L1 + L2) formats.
    """
    lines = [l.rstrip() for l in content.splitlines() if l.strip()]
    records = []
    i = 0

    while i < len(lines):
        # Detect line type
        line = lines[i]

        if line.startswith("1 ") and len(line) >= 69:
            # 2-line format (no name line)
            name = f"NORAD-{line[2:7].strip()}"
            l1 = line
            i += 1
            if i < len(lines) and lines[i].startswith("2 "):
                l2 = lines[i]
                i += 1
                record = _parse_tle_pair(name, l1, l2)
                if record:
                    records.append(record)
        elif not line.startswith("1 ") and not line.startswith("2 "):
            # Name line
            name = line.strip()
            i += 1
            if i < len(lines) and lines[i].startswith("1 "):
                l1 = lines[i]
                i += 1
                if i < len(lines) and lines[i].startswith("2 "):
                    l2 = lines[i]
                    i += 1
                    record = _parse_tle_pair(name, l1, l2)
                    if record:
                        records.append(record)
                else:
                    pass  # malformed, skip
            else:
                pass  # malformed, skip
        else:
            i += 1  # skip orphan line 2

    return records


def _parse_tle_pair(name: str, l1: str, l2: str) -> dict | None:
    """Parse a single TLE name + line1 + line2 into a dict."""
    try:
        # ── Line 1 ────────────────────────────────────────────────────────────
        # Positions are 1-indexed per TLE spec, Python is 0-indexed → subtract 1
        norad_cat_id = int(l1[2:7].strip())
        classification = l1[7].strip() or "U"
        int_designator = l1[9:17].strip()

        epoch_year_2d = int(l1[18:20].strip())
        epoch_day = float(l1[20:32].strip())
        epoch_dt = _epoch_to_datetime(epoch_year_2d, epoch_day)

        # Mean motion first derivative — straightforward decimal
        mm_dot_str = l1[33:43].strip()
        mean_motion_dot = float(mm_dot_str)

        # Mean motion second derivative — packed format
        mean_motion_ddot = _parse_decimal_packed(l1[44:52].strip())

        # BSTAR drag term — packed format
        bstar_drag = _parse_decimal_packed(l1[53:61].strip())

        element_set_number = int(l1[64:68].strip() or "0")
        checksum_l1 = int(l1[68].strip()) if len(l1) > 68 else 0

        # ── Line 2 ────────────────────────────────────────────────────────────
        inclination = float(l2[8:16].strip())
        raan = float(l2[17:25].strip())

        # Eccentricity has no leading decimal point in TLE
        ecc_str = l2[26:33].strip()
        eccentricity = float("0." + ecc_str)

        arg_of_perigee = float(l2[34:42].strip())
        mean_anomaly = float(l2[43:51].strip())
        mean_motion = float(l2[52:63].strip())

        rev_number_str = l2[63:68].strip()
        rev_number = int(rev_number_str) if rev_number_str else 0

        checksum_l2 = int(l2[68].strip()) if len(l2) > 68 else 0

        return {
            "name": name,
            "norad_cat_id": norad_cat_id,
            "classification": classification,
            "int_designator": int_designator,
            "epoch_year": epoch_year_2d,
            "epoch_day": epoch_day,
            "epoch_datetime": epoch_dt,
            "mean_motion_dot": mean_motion_dot,
            "mean_motion_ddot": mean_motion_ddot,
            "bstar_drag": bstar_drag,
            "element_set_number": element_set_number,
            "checksum_l1": checksum_l1,
            "inclination_deg": inclination,
            "raan_deg": raan,
            "eccentricity": eccentricity,
            "arg_of_perigee_deg": arg_of_perigee,
            "mean_anomaly_deg": mean_anomaly,
            "mean_motion_rev_day": mean_motion,
            "rev_number": rev_number,
            "checksum_l2": checksum_l2,
            "raw_line1": l1,
            "raw_line2": l2,
            "checksum_l1_valid": validate_checksum(l1),
            "checksum_l2_valid": validate_checksum(l2),
        }
    except Exception as e:
        # Return None to signal a parse failure; caller will skip it
        return None
