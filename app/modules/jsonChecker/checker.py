import json
from typing import Any, Dict, List, Tuple


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _expect(obj: Dict[str, Any], key: str, types: Tuple[type, ...], errors: List[str], path: str):
    if key not in obj:
        errors.append(f"{path}.{key} missing")
        return None
    val = obj[key]
    if not isinstance(val, types):
        # allow int where float expected
        if float in types and isinstance(val, int):
            return val
        errors.append(
            f"{path}.{key} expected {
                ', '.join(
                    [
                        t.__name__ for t in types])} got {
                type(val).__name__}"
        )
    return val


def validate_json_file(path: str) -> Dict[str, Any]:
    """
    Valida si el archivo en `path` es JSON y sigue la estructura esperada.

    Devuelve un dict:
      {
        "is_json": bool,
        "valid": bool,
        "errors": [str, ...],
        "data": parsed_json_or_None
      }
    """
    errors: List[str] = []

    # Comprobar extensión mínima (opcional)
    if not path.lower().endswith(".json"):
        errors.append("File extension is not .json")

    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as e:
        return {"is_json": False, "valid": False, "errors": [f"JSON parse error: {e}"], "data": None}

    if not isinstance(data, dict):
        return {"is_json": True, "valid": False, "errors": ["Top-level JSON must be an object"], "data": data}

    # Top-level keys expected
    required_top = [
        "metadata",
        "instrumentation",
        "optics",
        "exposure",
        "calibration",
        "sky_conditions",
        "astrometry",
        "photometry",
        "analysis",
    ]
    for k in required_top:
        if k not in data:
            errors.append(f"Top-level key '{k}' missing")

    # metadata
    md = data.get("metadata", {})
    if isinstance(md, dict):
        for k in [
            "object_name",
            "object_type",
            "ra",
            "dec",
            "constellation",
            "observation_date_utc",
            "observer",
            "project",
        ]:
            v = md.get(k)
            if v is None or not isinstance(v, str) or not v:
                errors.append(f"metadata.{k} must be a non-empty string")
    else:
        errors.append("metadata must be an object")

    # instrumentation
    inst = data.get("instrumentation", {})
    if isinstance(inst, dict):
        for k in ["telescope", "mount", "camera"]:
            v = inst.get(k)
            if v is None or not isinstance(v, str) or not v:
                errors.append(f"instrumentation.{k} must be a non-empty string")
        if "pixel_scale_arcsec" in inst and not _is_number(inst["pixel_scale_arcsec"]):
            errors.append("instrumentation.pixel_scale_arcsec must be a number")
        for n in ["gain", "readout_noise_e", "temperature_c"]:
            if n in inst and not _is_number(inst[n]):
                errors.append(f"instrumentation.{n} must be a number")
    else:
        errors.append("instrumentation must be an object")

    # optics
    optics = data.get("optics", {})
    if isinstance(optics, dict):
        filters = optics.get("filters")
        if filters is None or not isinstance(filters, list) or len(filters) == 0:
            errors.append("optics.filters must be a non-empty list")
        else:
            for i, f in enumerate(filters):
                if not isinstance(f, dict):
                    errors.append(f"optics.filters[{i}] must be an object")
                    continue
                if not f.get("name") or not isinstance(f.get("name"), str):
                    errors.append(f"optics.filters[{i}].name must be a non-empty string")
                if "bandwidth_nm" not in f or not _is_number(f.get("bandwidth_nm")):
                    errors.append(f"optics.filters[{i}].bandwidth_nm must be a number")
        for n in ["focal_length_mm", "f_ratio"]:
            if n in optics and not _is_number(optics[n]):
                errors.append(f"optics.{n} must be a number")
        if "binning" in optics and not isinstance(optics["binning"], str):
            errors.append("optics.binning must be a string")
    else:
        errors.append("optics must be an object")

    # exposure
    exposure = data.get("exposure", {})
    if isinstance(exposure, dict):
        for n in ["sub_exposures", "exposure_time_s", "total_integration_s"]:
            if n in exposure and not isinstance(exposure[n], int):
                errors.append(f"exposure.{n} must be integer")
        for n in ["airmass", "moon_phase_percent", "sky_bortle"]:
            if n in exposure and not _is_number(exposure[n]):
                errors.append(f"exposure.{n} must be number")
    else:
        errors.append("exposure must be an object")

    # calibration
    cal = data.get("calibration", {})
    if isinstance(cal, dict):
        for n in ["darks_used", "flats_used", "bias_used", "dark_flat_used"]:
            if n in cal and not isinstance(cal[n], int):
                errors.append(f"calibration.{n} must be integer")
        if "calibration_notes" in cal and not isinstance(cal["calibration_notes"], str):
            errors.append("calibration.calibration_notes must be string")
    else:
        errors.append("calibration must be an object")

    # sky_conditions
    sky = data.get("sky_conditions", {})
    if isinstance(sky, dict):
        if "seeing_arcsec" in sky and not _is_number(sky["seeing_arcsec"]):
            errors.append("sky_conditions.seeing_arcsec must be number")
        if "transparency" in sky and not isinstance(sky["transparency"], str):
            errors.append("sky_conditions.transparency must be string")
        for n in ["humidity_percent", "temperature_c", "wind_speed_kmh"]:
            if n in sky and not _is_number(sky[n]):
                errors.append(f"sky_conditions.{n} must be number")
    else:
        errors.append("sky_conditions must be an object")

    # astrometry
    ast = data.get("astrometry", {})
    if isinstance(ast, dict):
        for n in ["field_center_ra", "field_center_dec"]:
            if n in ast and not isinstance(ast[n], str):
                errors.append(f"astrometry.{n} must be string")
        if "field_rotation_deg" in ast and not _is_number(ast["field_rotation_deg"]):
            errors.append("astrometry.field_rotation_deg must be number")
        if "plate_solved" in ast and not isinstance(ast["plate_solved"], bool):
            errors.append("astrometry.plate_solved must be boolean")
        if "catalog_used" in ast and not isinstance(ast["catalog_used"], str):
            errors.append("astrometry.catalog_used must be string")
    else:
        errors.append("astrometry must be an object")

    # photometry
    phot = data.get("photometry", {})
    if isinstance(phot, dict):
        for n in ["zero_point_mag", "limiting_magnitude", "background_noise_e", "saturation_level_adus"]:
            if n in phot and not _is_number(phot[n]):
                errors.append(f"photometry.{n} must be number")
    else:
        errors.append("photometry must be an object")

    # analysis
    anl = data.get("analysis", {})
    if isinstance(anl, dict):
        if "detected_sources" in anl and not isinstance(anl["detected_sources"], int):
            errors.append("analysis.detected_sources must be integer")
        notable = anl.get("notable_objects")
        if notable is None or not isinstance(notable, list):
            errors.append("analysis.notable_objects must be a list")
        else:
            for i, no in enumerate(notable):
                if not isinstance(no, dict):
                    errors.append(f"analysis.notable_objects[{i}] must be object")
                    continue
                if not no.get("name") or not isinstance(no.get("name"), str):
                    errors.append(f"analysis.notable_objects[{i}].name must be non-empty string")
                if not no.get("type") or not isinstance(no.get("type"), str):
                    errors.append(f"analysis.notable_objects[{i}].type must be non-empty string")
        if "signal_to_noise_ratio" in anl and not _is_number(anl["signal_to_noise_ratio"]):
            errors.append("analysis.signal_to_noise_ratio must be number")
        if "preliminary_science_value" in anl and not isinstance(anl["preliminary_science_value"], str):
            errors.append("analysis.preliminary_science_value must be string")
    else:
        errors.append("analysis must be an object")

    # notes optional but if present must be string
    if "notes" in data and not isinstance(data["notes"], str):
        errors.append("notes must be string")

    valid = len(errors) == 0
    return {"is_json": True, "valid": valid, "errors": errors, "data": data if valid else None}


if __name__ == "__main__":
    import argparse
    import pprint

    parser = argparse.ArgumentParser(description="Validate dataset JSON structure")
    parser.add_argument("file", help="Path to JSON file")
    args = parser.parse_args()
    res = validate_json_file(args.file)
    pprint.pprint(res)
