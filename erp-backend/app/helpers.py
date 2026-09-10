"""Utilidades de parse/serializacao compartilhadas pelos blueprints."""
from datetime import date, datetime, time


def parse_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    s = str(value).strip()
    if "T" in s:
        s = s.split("T")[0]
    return date.fromisoformat(s[:10])


def parse_time(value):
    if value is None or value == "":
        return None
    if isinstance(value, time):
        return value
    s = str(value).strip()
    if len(s) == 5:
        s += ":00"
    return time.fromisoformat(s[:8])


def parse_datetime(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    s = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return datetime.combine(parse_date(s), datetime.min.time())


def iso(value):
    if value is None:
        return None
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    return value


def num(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def body_json():
    from flask import request

    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}
