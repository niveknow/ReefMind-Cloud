from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from app.config import get_settings

settings = get_settings()

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


def write_telemetry(tenant_id: str, readings: list[dict]) -> int:
    bucket = ensure_tenant_bucket(tenant_id)
    client = get_influx_client()
    write_api = client.write_api(write_type=SYNCHRONOUS)

    points = []
    for r in readings:
        point = Point("apex_telemetry").tag("tenant_id", tenant_id).tag("probe_name", r["probe_name"]).tag("probe_type", r["probe_type"]).tag("unit", r["unit"]).tag("did", r.get("did", "")).field("value", float(r["value"]))
        if r.get("timestamp"):
            point.time(r["timestamp"])
        points.append(point)

    write_api.write(bucket=bucket, record=points)
    return len(points)


def write_outlets(tenant_id: str, outlets: list[dict]) -> int:
    bucket = ensure_tenant_bucket(tenant_id)
    client = get_influx_client()
    write_api = client.write_api(write_type=SYNCHRONOUS)

    points = []
    for o in outlets:
        point = Point("apex_outlet_states").tag("tenant_id", tenant_id).tag("outlet_name", o["outlet_name"]).field("state", int(o["state"])).field("state_display", str(o["state_display"]))
        if o.get("timestamp"):
            point.time(o["timestamp"])
        points.append(point)

    write_api.write(bucket=bucket, record=points)
    return len(points)


def write_power(tenant_id: str, readings: list[dict]) -> int:
    bucket = ensure_tenant_bucket(tenant_id)
    client = get_influx_client()
    write_api = client.write_api(write_type=SYNCHRONOUS)

    points = []
    for r in readings:
        point = Point("apex_power").tag("tenant_id", tenant_id).tag("outlet_name", r["outlet_name"]).tag("channel", r.get("channel", "main")).field("watts", float(r["watts"])).field("amps", float(r.get("amps", 0)))
        if r.get("timestamp"):
            point.time(r["timestamp"])
        points.append(point)

    write_api.write(bucket=bucket, record=points)
    return len(points)


def query_telemetry(tenant_id: str, probe_name: str = "", duration: str = "24h") -> list:
    bucket = ensure_tenant_bucket(tenant_id)
    client = get_influx_client()
    query_api = client.query_api()

    where_clause = f'|> filter(fn: (r) => r["probe_name"] == "{probe_name}")' if probe_name else ""

    query = f"""
    from(bucket: "{bucket}")
      |> range(start: -{duration})
      |> filter(fn: (r) => r["_measurement"] == "apex_telemetry")
      {where_clause}
      |> sort(columns: ["_time"], desc: false)
      |> yield(name: "results")
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

    print(f"DEBUG query_outlets: tenant_id={tenant_id[:20]}, bucket={bucket}")

    query = f"""
    from(bucket: "{bucket}")
      |> range(start: -30m)
      |> filter(fn: (r) => r["_measurement"] == "apex_outlet_states")
      |> filter(fn: (r) => r["_field"] == "state")
      |> last()
    """

    print(f"DEBUG query_outlets: executing query for bucket={bucket}")
    tables = query_api.query(query)
    results = []
    for table in tables:
        for record in table.records:
            results.append({
                "outlet_name": record.values.get("outlet_name", ""),
                "state": int(record.get_value()),
                "state_display": "ON" if int(record.get_value()) == 1 else "OFF",
            })
    print(f"DEBUG query_outlets: returning {len(results)} outlets")
    return results

# Water tests
MLOG_TYPE_MAP = {1: "KH", 2: "Ca", 4: "Mg", 5: "NO3", 6: "PO4"}
MLOG_UNITS = {"KH": "dkh", "Ca": "ppm", "Mg": "ppm", "NO3": "ppm", "PO4": "ppm"}

def write_water_tests(tenant_id: str, readings: list[dict], bucket_name: str = "") -> int:
    """Write water test results to InfluxDB as apex_water_tests measurement.
    Performs atomic replace: deletes existing apex_water_tests measurement first.
    """
    bucket = bucket_name or ensure_tenant_bucket(tenant_id)
    client = get_influx_client()
    
    # Atomic replace
    delete_api = client.delete_api()
    delete_api.delete(start="1970-01-01T00:00:00Z", stop="2100-01-01T00:00:00Z", 
                      predicate='_measurement="apex_water_tests"', bucket=bucket, org=settings.influx_org)
    
    write_api = client.write_api(write_type=SYNCHRONOUS)
    points = []
    for r in readings:
        m_type = r.get("type")
        param = MLOG_TYPE_MAP.get(m_type, "Unknown")
        unit = MLOG_UNITS.get(param, "unknown")
        
        point = Point("apex_water_tests") \
            .tag("tenant_id", tenant_id) \
            .tag("parameter", param) \
            .tag("unit", unit) \
            .field("value", float(r.get("value", 0)))
        
        if r.get("date"):
            # Assuming date format is compatible with InfluxDB or ISO
            point.time(r["date"])
        points.append(point)
    
    if points:
        write_api.write(bucket=bucket, record=points)
    return len(points)

def query_water_tests(tenant_id: str, parameter: str = "", duration: str = "365d") -> list:
    bucket = ensure_tenant_bucket(tenant_id)
    client = get_influx_client()
    query_api = client.query_api()
    
    param_filter = f'|> filter(fn: (r) => r["parameter"] == "{parameter}")' if parameter else ""
    
    query = f"""
    from(bucket: "{bucket}")
      |> range(start: -{duration})
      |> filter(fn: (r) => r["_measurement"] == "apex_water_tests")
      {param_filter}
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
NOTE_TYPES = {0: "Basic", 1: "Good", 2: "Bad", 3: "Ugly", 4: "Maintenance", 5: "Event"}

def write_notes(tenant_id: str, notes: list[dict], bucket_name: str = "") -> int:
    """Write tank notes to InfluxDB as apex_logs measurement.
    Performs atomic replace: deletes existing apex_logs measurement first.
    """
    bucket = bucket_name or ensure_tenant_bucket(tenant_id)
    client = get_influx_client()
    
    # Atomic replace
    delete_api = client.delete_api()
    delete_api.delete(start="1970-01-01T00:00:00Z", stop="2100-01-01T00:00:00Z", 
                      predicate='_measurement="apex_logs"', bucket=bucket, org=settings.influx_org)
    
    write_api = client.write_api(write_type=SYNCHRONOUS)
    points = []
    for n in notes:
        n_type = n.get("type", 0)
        n_type_name = NOTE_TYPES.get(n_type, "Basic")
        
        point = Point("apex_logs") \
            .tag("tenant_id", tenant_id) \
            .tag("note_id", str(n.get("id", ""))) \
            .tag("type_code", str(n_type)) \
            .tag("type_name", n_type_name) \
            .tag("title", n.get("title", "")) \
            .tag("reason_code", str(n.get("reason", 0))) \
            .tag("has_comment", "true" if n.get("text") else "false") \
            .field("value", 1.0) \
            .field("comment", n.get("text", ""))
        
        if n.get("date"):
            point.time(n["date"])
        points.append(point)
    
    if points:
        write_api.write(bucket=bucket, record=points)
    return len(points)

def query_notes(tenant_id: str, duration: str = "365d", limit: int = 100) -> list:
    bucket = ensure_tenant_bucket(tenant_id)
    client = get_influx_client()
    query_api = client.query_api()

    query = f"""
    from(bucket: "{bucket}")
      |> range(start: -{duration})
      |> filter(fn: (r) => r["_measurement"] == "apex_logs")
      |> sort(columns: ["_time"], desc: true)
      |> yield(name: "notes")
    """

    tables = query_api.query(query)
    # Deduplicate by note_id — InfluxDB stores each field as a separate series
    # (one for "value", one for "comment"), so raw iteration yields 2 records per note.
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
                    "has_comment": record.values.get("has_comment", "false") == "true",
                    "comment": "",
                }

            field = record.get_field()
            if field == "comment":
                notes_map[nid]["comment"] = record.get_value() or ""

    # Sort by time desc, apply limit
    sorted_notes = sorted(notes_map.values(), key=lambda n: n.get("time", ""), reverse=True)
    return sorted_notes[:limit]
