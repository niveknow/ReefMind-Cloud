from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from app.config import get_settings
import logging

settings = get_settings()
log = logging.getLogger(__name__)

_client = None


def get_influx_client():
    global _client
    if _client is None:
        _client = InfluxDBClient(
            url=settings.influx_url,
            token=settings.influx_token,
            org=settings.influx_org,
        )
    return _client


def ensure_tenant_bucket(tenant_id: str) -> str:
    bucket_name = f"reefmind_{tenant_id}"
    client = get_influx_client()
    buckets_api = client.buckets_api()
    org_api = client.organizations_api()

    existing = buckets_api.find_bucket_by_name(bucket_name)
    if existing:
        return bucket_name

    org = org_api.find_organizations(org=settings.influx_org)[0]
    buckets_api.create_bucket(bucket_name=bucket_name, org_id=org.id)
    return bucket_name


def write_telemetry(tenant_id: str, readings: list[dict], apex_id: str = "") -> int:
    bucket = ensure_tenant_bucket(tenant_id)
    client = get_influx_client()
    write_api = client.write_api(write_type=SYNCHRONOUS)

    points = []
    for r in readings:
        point = (
            Point("apex_telemetry")
            .tag("tenant_id", tenant_id)
            .tag("apex_id", apex_id)
            .tag("probe_name", r["probe_name"])
            .tag("probe_type", r["probe_type"])
            .tag("unit", r["unit"])
            .tag("did", r.get("did", ""))
            .field("value", float(r["value"]))
        )
        if r.get("timestamp"):
            point.time(r["timestamp"])
        points.append(point)

    try:
        write_api.write(bucket=bucket, record=points)
    except Exception as e:
        log.error("write_telemetry failed for tenant %s: %s", tenant_id[:8], e)
        return 0
    return len(points)


def write_outlets(tenant_id: str, outlets: list[dict], apex_id: str = "") -> int:
    bucket = ensure_tenant_bucket(tenant_id)
    client = get_influx_client()
    write_api = client.write_api(write_type=SYNCHRONOUS)

    points = []
    for o in outlets:
        point = (
            Point("apex_outlet_states")
            .tag("tenant_id", tenant_id)
            .tag("apex_id", apex_id)
            .tag("outlet_name", o["outlet_name"])
            .tag("outlet_type", o.get("outlet_type", ""))
            .tag("device_id", o.get("device_id", ""))
            .tag("device_group", o.get("device_group", ""))
            .field("state", int(o["state"]))
            .field("state_display", str(o["state_display"]))
        )
        if o.get("timestamp"):
            point.time(o["timestamp"])
        points.append(point)

    try:
        write_api.write(bucket=bucket, record=points)
    except Exception as e:
        log.error("write_outlets failed for tenant %s: %s", tenant_id[:8], e)
        return 0
    return len(points)


def write_power(tenant_id: str, readings: list[dict], apex_id: str = "") -> int:
    bucket = ensure_tenant_bucket(tenant_id)
    client = get_influx_client()
    write_api = client.write_api(write_type=SYNCHRONOUS)

    points = []
    for r in readings:
        point = (
            Point("apex_power")
            .tag("tenant_id", tenant_id)
            .tag("apex_id", apex_id)
            .tag("outlet_name", r["outlet_name"])
            .tag("channel", r.get("channel", "main"))
            .field("watts", float(r["watts"]))
            .field("amps", float(r.get("amps", 0)))
        )
        if r.get("timestamp"):
            point.time(r["timestamp"])
        points.append(point)

    try:
        write_api.write(bucket=bucket, record=points)
    except Exception as e:
        log.error("write_power failed for tenant %s: %s", tenant_id[:8], e)
        return 0
    return len(points)


def query_telemetry(tenant_id: str, probe_name: str = "", duration: str = "24h") -> list:
    bucket = ensure_tenant_bucket(tenant_id)
    client = get_influx_client()
    query_api = client.query_api()

    where_clause = f'|> filter(fn: (r) => r["probe_name"] == "{probe_name}")' if probe_name else ""

    query = f"""\
    from(bucket: "{bucket}")
      |> range(start: -{duration})
      |> filter(fn: (r) => r["_measurement"] == "apex_telemetry")
      {where_clause}
      |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
      |> group()
      |> sort(columns: ["_time"])
      |> yield(name: "mean")
    """

    tables = query_api.query(query)
    results = []
    for table in tables:
        for record in table.records:
            results.append({
                "time": record.get_time().isoformat() if hasattr(record, "get_time") else str(record["_time"]),
                "did": record.values.get("did", ""),
                "probe_name": record.values.get("probe_name", ""),
                "probe_type": record.values.get("probe_type", ""),
                "unit": record.values.get("unit", ""),
                "value": record.get_value(),
            })
    return results


def query_outlets(tenant_id: str) -> list:
    """Get the latest outlet states for a tenant from InfluxDB."""
    bucket = ensure_tenant_bucket(tenant_id)
    client = get_influx_client()
    query_api = client.query_api()

    log.debug("query_outlets: tenant_id=%s, bucket=%s", tenant_id[:20], bucket)

    query = f"""\
    from(bucket: "{bucket}")
      |> range(start: -6h)
      |> filter(fn: (r) => r["_measurement"] == "apex_outlet_states")
      |> filter(fn: (r) => r["_field"] == "state")
      |> last()
    """

    log.debug("query_outlets: executing query for bucket=%s", bucket)
    tables = query_api.query(query)
    results = []
    for table in tables:
        for record in table.records:
            results.append({
                "outlet_name": record.values.get("outlet_name", ""),
                "outlet_type": record.values.get("outlet_type", ""),
                "device_id": record.values.get("device_id", ""),
                "device_group": record.values.get("device_group", ""),
                "state": int(record.get_value()),
                "state_display": "ON" if int(record.get_value()) == 1 else "OFF",
            })
    log.debug("query_outlets: returning %d outlets", len(results))
    return results

# Water tests
MLOG_TYPE_MAP = {1: "KH", 2: "Ca", 4: "Mg", 5: "NO3", 6: "PO4"}
MLOG_UNITS = {"KH": "dkh", "Ca": "ppm", "Mg": "ppm", "NO3": "ppm", "PO4": "ppm"}

def write_water_tests(tenant_id: str, readings: list[dict], bucket_name: str = "", apex_id: str = "") -> int:
    """Write water test results to InfluxDB as apex_water_tests measurement.
    Performs atomic replace: deletes existing apex_water_tests measurement first.
    """
    bucket = bucket_name or ensure_tenant_bucket(tenant_id)
    client = get_influx_client()

    # Atomic replace
    try:
        delete_api = client.delete_api()
        delete_api.delete(start="1970-01-01T00:00:00Z", stop="2100-01-01T00:00:00Z",
                          predicate='_measurement="apex_water_tests"', bucket=bucket, org=settings.influx_org)
    except Exception as e:
        log.error("write_water_tests: delete failed for tenant %s: %s", tenant_id[:8], e)
        # Continue anyway — write may still succeed

    write_api = client.write_api(write_type=SYNCHRONOUS)
    points = []
    for r in readings:
        m_type = r.get("type")
        param = MLOG_TYPE_MAP.get(m_type, "Unknown")
        unit = MLOG_UNITS.get(param, "unknown")

        point = Point("apex_water_tests") \
            .tag("tenant_id", tenant_id) \
            .tag("apex_id", apex_id) \
            .tag("parameter", param) \
            .tag("unit", unit) \
            .field("value", float(r.get("value", 0)))

        if r.get("date"):
            point.time(r["date"])
        points.append(point)

    if points:
        try:
            write_api.write(bucket=bucket, record=points)
        except Exception as e:
            log.error("write_water_tests failed for tenant %s: %s", tenant_id[:8], e)
            return 0
    return len(points)

def query_water_tests(tenant_id: str, parameter: str = "", duration: str = "365d", apex_id: str = "") -> list:
    bucket = ensure_tenant_bucket(tenant_id)
    client = get_influx_client()
    query_api = client.query_api()

    param_filter = f'|> filter(fn: (r) => r["parameter"] == "{parameter}")' if parameter else ""
    apex_filter = f'|> filter(fn: (r) => r["apex_id"] == "{apex_id}")' if apex_id else ""

    query = f"""\
    from(bucket: "{bucket}")
      |> range(start: -{duration})
      |> filter(fn: (r) => r["_measurement"] == "apex_water_tests")
      {param_filter}
      {apex_filter}
      |> yield(name: "water_tests")
    """

    tables = query_api.query(query)
    results = []
    for table in tables:
        for record in table.records:
            results.append({
                "time": record.get_time().isoformat() if hasattr(record, "get_time") else str(record["_time"]),
                "parameter": record.values.get("parameter", ""),
                "value": record.get_value(),
                "unit": record.values.get("unit", ""),
            })
    return results

# Notes
NOTE_TYPES: dict[int, str] = {0: "Basic", 1: "Good", 2: "Bad", 3: "Ugly", 4: "Maintenance", 5: "Event"}

# Reason code → human-readable title (when API title is empty)
# Ported from on-prem scripts/apex_notes.py
REASON_TITLES: dict[tuple[int, int], str] = {
    (0, 0): "Note",
    (1, 0): "General",
    (1, 1): "General",
    (1, 5): "Recovery",
    (1, 9): "Added Fish",
    (1, 10): "Added Coral",
    (1, 11): "Added Invert/CUC",
    (1, 12): "Added Equipment",
    (2, 0): "General",
    (2, 5): "Disease/Injury",
    (2, 10): "Coral Issue",
    (2, 17): "Algae Issue",
    (3, 0): "Fish Died",
    (3, 1): "Coral Died",
    (3, 2): "Invert Died",
    (4, 0): "Water Change",
    (4, 1): "Dosed",
    (4, 2): "General",
    (4, 3): "Changed Filter / Socks",
    (4, 4): "Added Sand",
    (4, 7): "Cleaned Pump",
    (4, 8): "Changed Carbon",
    (4, 9): "Changed Media",
    (4, 10): "Bio-Pellets",
    (4, 11): "Cleaned Glass",
    (4, 12): "Adjusted Equipment",
    (4, 13): "Feeding",
    (5, 0): "General",
}


def _resolve_note_id(note: dict) -> str | None:
    """Try multiple field names Fusion may use for the note ID.
    Returns the ID string or None if not found.
    """
    for key in ("id", "note_id", "_id", "ID"):
        val = note.get(key)
        if val is not None:
            return str(val)
    return None

def write_notes(tenant_id: str, notes: list[dict], bucket_name: str = "", apex_id: str = "") -> int:
    """Write tank notes to InfluxDB as apex_logs measurement.
    Performs atomic replace: deletes existing apex_logs measurement first.
    
    Uses _resolve_note_id() to handle multiple Fusion API field name
    conventions, and falls back to REASON_TITLES when the note title is empty.
    Ported from on-prem scripts/apex_notes.py note_to_points().
    """
    from datetime import datetime, timezone

    bucket = bucket_name or ensure_tenant_bucket(tenant_id)
    client = get_influx_client()

    # Atomic replace
    try:
        delete_api = client.delete_api()
        delete_api.delete(start="1970-01-01T00:00:00Z", stop="2100-01-01T00:00:00Z",
                          predicate='_measurement="apex_logs"', bucket=bucket, org=settings.influx_org)
    except Exception as e:
        log.error("write_notes: delete failed for tenant %s: %s", tenant_id[:8], e)

    write_api = client.write_api(write_type=SYNCHRONOUS)
    points = []
    for n in notes:
        nid = _resolve_note_id(n)
        if nid is None:
            log.warning("write_notes: skipping note with no ID (title=%s)", n.get("title", "(none)"))
            continue

        # Parse timestamp — Fusion stores UTC
        date_iso = n.get("date", "")
        if not isinstance(date_iso, str) or not date_iso:
            log.warning("write_notes: skipping note %s with no date", nid)
            continue
        try:
            ts = datetime.fromisoformat(date_iso.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            log.warning("write_notes: skipping note %s with unparseable date: %s", nid, date_iso)
            continue

        n_type = n.get("type", 0)
        if isinstance(n_type, str):
            try:
                n_type = int(n_type)
            except (ValueError, TypeError):
                n_type = 0
        n_type_name = NOTE_TYPES.get(n_type, f"Type_{n_type}")

        # Title — fall back to reason title when empty
        title = n.get("title", "")
        if not title:
            reason_code = n.get("reason", 0)
            if isinstance(reason_code, str):
                try:
                    reason_code = int(reason_code)
                except (ValueError, TypeError):
                    reason_code = 0
            title = REASON_TITLES.get((n_type, reason_code), n_type_name)
        else:
            reason_code = n.get("reason", 0)

        if isinstance(reason_code, str):
            try:
                reason_code = int(reason_code)
            except (ValueError, TypeError):
                reason_code = 0

        comment = n.get("text", "") or ""
        if not comment.strip():
            comment = ""
        has_comment = "yes" if comment.strip() else "no"

        # Resolve note_id — Fusion API uses _id (MongoDB convention)
        raw_id = n.get("id") or n.get("note_id") or n.get("_id") or n.get("ID") or ""
        note_id = str(raw_id)

        point = Point("apex_logs") \
            .tag("tenant_id", tenant_id) \
            .tag("apex_id", apex_id) \
            .tag("note_id", nid) \
            .tag("type_code", str(n_type)) \
            .tag("type_name", n_type_name) \
            .tag("title", title) \
            .tag("reason_code", str(reason_code)) \
            .tag("has_comment", has_comment) \
            .field("value", 1.0) \
            .field("comment", comment) \
            .time(ts)

        points.append(point)

    if points:
        try:
            write_api.write(bucket=bucket, record=points)
        except Exception as e:
            log.error("write_notes failed for tenant %s: %s", tenant_id[:8], e)
            return 0
    return len(points)

def query_notes(tenant_id: str, duration: str = "730d", limit: int = 100) -> list:
    bucket = ensure_tenant_bucket(tenant_id)
    client = get_influx_client()
    query_api = client.query_api()

    query = f"""\
    from(bucket: "{bucket}")
      |> range(start: -{duration})
      |> filter(fn: (r) => r["_measurement"] == "apex_logs")
      |> sort(columns: ["_time"], desc: true)
      |> yield(name: "notes")
    """

    tables = query_api.query(query)
    # Deduplicate by note_id — InfluxDB stores each field as a separate series
    notes_map: dict[str, dict] = {}
    for table in tables:
        for record in table.records:
            nid = record.values.get("note_id", "")
            if not nid:
                continue

            if nid not in notes_map:
                notes_map[nid] = {
                    "time": record.get_time().isoformat() if hasattr(record, "get_time") else str(record["_time"]),
                    "note_id": nid,
                    "type_code": record.values.get("type_code", ""),
                    "type_name": record.values.get("type_name", ""),
                    "title": record.values.get("title", ""),
                    "reason_code": record.values.get("reason_code", ""),
                    "has_comment": record.values.get("has_comment", "no") == "yes",
                    "comment": "",
                }

            field = record.get_field()
            if field == "comment":
                notes_map[nid]["comment"] = record.get_value() or ""

    sorted_notes = sorted(notes_map.values(), key=lambda n: n.get("time", ""), reverse=True)
    return sorted_notes[:limit]


def write_controller_info(tenant_id: str, info: dict, apex_id: str = "") -> int:
    """Write controller hardware/software/serial/timezone to apex_controller_info.
    Atomic replace — only one record per tenant needed.
    """
    bucket = ensure_tenant_bucket(tenant_id)
    client = get_influx_client()

    try:
        delete_api = client.delete_api()
        delete_api.delete(start="1970-01-01T00:00:00Z", stop="2100-01-01T00:00:00Z",
                          predicate='_measurement="apex_controller_info"', bucket=bucket, org=settings.influx_org)
    except Exception as e:
        log.error("write_controller_info: delete failed for tenant %s: %s", tenant_id[:8], e)

    write_api = client.write_api(write_type=SYNCHRONOUS)
    point = (
        Point("apex_controller_info")
        .tag("tenant_id", tenant_id)
        .tag("apex_id", apex_id)
        .tag("serial", info.get("serial", ""))
        .field("hardware", info.get("hardware", ""))
        .field("software", info.get("software", ""))
        .field("timezone", info.get("timezone", ""))
        .field("name", info.get("name", ""))
    )
    try:
        write_api.write(bucket=bucket, record=point)
    except Exception as e:
        log.error("write_controller_info failed for tenant %s: %s", tenant_id[:8], e)
        return 0
    return 1


def query_controller_info(tenant_id: str) -> dict:
    """Get the latest controller info for a tenant."""
    bucket = ensure_tenant_bucket(tenant_id)
    client = get_influx_client()
    query_api = client.query_api()

    query = f"""\
    from(bucket: "{bucket}")
      |> range(start: -365d)
      |> filter(fn: (r) => r["_measurement"] == "apex_controller_info")
      |> last()
    """

    tables = query_api.query(query)
    info = {}
    for table in tables:
        for record in table.records:
            field = record.get_field()
            if field:
                info[field] = record.get_value()
            if "serial" in record.values:
                info.setdefault("serial", record.values["serial"])
            if "apex_id" in record.values:
                info.setdefault("apex_id", record.values["apex_id"])
    return info
