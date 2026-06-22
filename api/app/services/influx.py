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
      |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
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


def query_noaa_buoy(tenant_id: str, duration: str = "24h") -> list:
    """Query NOAA buoy readings from tenant's InfluxDB bucket."""
    bucket = f"reefmind_{tenant_id}"
    client = get_influx_client()
    query_api = client.query_api()

    query = f"""
    from(bucket: "{bucket}")
      |> range(start: -{duration})
      |> filter(fn: (r) => r["_measurement"] == "noaa_buoy")
      |> yield(name: "mean")
    """

    tables = query_api.query(query)
    results = []
    for table in tables:
        for record in table.records:
            results.append(record)
    return results
