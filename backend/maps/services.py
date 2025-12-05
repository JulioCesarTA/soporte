import hashlib
import json
import os
import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

from django.db import connection

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_\\.]*$")

DEFAULT_MAP_CONFIG = {
    "table": "dimensiones",
    "name_field": "nombre",
    "zone_field": "zona",
    "district_field": "distrito",
    "lat_field": "latitud",
    "lng_field": "longitud",
    "value_field": "valor",
    "limit": 500,
}

DEFAULT_DISTRICT_CONFIG = {
    "table": "dimdistrito",
    "id_field": "distritoid",
    "code_field": "codigodistrito",
    "name_field": "nombredistrito",
    "geojson_field": "geojson",
}

DEFAULT_FILTER_FIELDS = {
    "timestamp": "timestamp",
    "moment_id": "momento_id",
    "altitude_level_id": "nivel_altitud_id",
    "signal_level_id": "nivel_senal_id",
    "speed_level_id": "nivel_velocidad_id",
    "operator_id": "operador_id",
    "network_id": "red_id",
    "district_id": "distrito_id",
    "device_id": "dispositivo_id",
}

DEFAULT_HEAT_DELTA = float(os.environ.get("MAP_HEAT_DELTA", 0.0008))  # ~90 m
DEFAULT_QUIET_SPEED_LEVEL_ID = os.environ.get("MAP_QUIET_SPEED_LEVEL_ID", "1")
HEAT_LIMIT = os.environ.get("MAP_HEAT_LIMIT")

PALETTE = [
    "#0F766E",
    "#1D4ED8",
    "#7C3AED",
    "#DB2777",
    "#EA580C",
    "#16A34A",
    "#0EA5E9",
    "#F59E0B",
    "#6B7280",
    "#EF4444",
]


def _safe_identifier(name: str) -> str:
    if not IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid identifier: {name}")
    return name


def _color_for_key(key: str) -> str:
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
    idx = int(digest, 16) % len(PALETTE)
    return PALETTE[idx]


def get_map_config() -> Dict[str, str]:
    return {
        "table": os.environ.get("MAP_TABLE", DEFAULT_MAP_CONFIG["table"]),
        "name_field": os.environ.get("MAP_NAME_FIELD", DEFAULT_MAP_CONFIG["name_field"]),
        "zone_field": os.environ.get("MAP_ZONE_FIELD", DEFAULT_MAP_CONFIG["zone_field"]),
        "district_field": os.environ.get("MAP_DISTRICT_FIELD", DEFAULT_MAP_CONFIG["district_field"]),
        "lat_field": os.environ.get("MAP_LAT_FIELD", DEFAULT_MAP_CONFIG["lat_field"]),
        "lng_field": os.environ.get("MAP_LNG_FIELD", DEFAULT_MAP_CONFIG["lng_field"]),
        "value_field": os.environ.get("MAP_VALUE_FIELD", DEFAULT_MAP_CONFIG["value_field"]),
        "where": os.environ.get("MAP_WHERE_CLAUSE"),
        "limit": int(os.environ.get("MAP_LIMIT", DEFAULT_MAP_CONFIG["limit"])),
    }


def get_district_config() -> Dict[str, str]:
    return {
        "table": os.environ.get("DISTRICT_TABLE", DEFAULT_DISTRICT_CONFIG["table"]),
        "id_field": os.environ.get("DISTRICT_ID_FIELD", DEFAULT_DISTRICT_CONFIG["id_field"]),
        "code_field": os.environ.get("DISTRICT_CODE_FIELD", DEFAULT_DISTRICT_CONFIG["code_field"]),
        "name_field": os.environ.get("DISTRICT_NAME_FIELD", DEFAULT_DISTRICT_CONFIG["name_field"]),
        "geojson_field": os.environ.get("DISTRICT_GEOJSON_FIELD", DEFAULT_DISTRICT_CONFIG["geojson_field"]),
        "where": os.environ.get("DISTRICT_WHERE_CLAUSE"),
    }


def get_filter_fields() -> Dict[str, str]:
    return {
        "timestamp": os.environ.get("MAP_TIMESTAMP_FIELD", DEFAULT_FILTER_FIELDS["timestamp"]),
        "moment_id": os.environ.get("MAP_MOMENT_FIELD", DEFAULT_FILTER_FIELDS["moment_id"]),
        "altitude_level_id": os.environ.get("MAP_ALTITUDE_LEVEL_FIELD", DEFAULT_FILTER_FIELDS["altitude_level_id"]),
        "signal_level_id": os.environ.get("MAP_SIGNAL_LEVEL_FIELD", DEFAULT_FILTER_FIELDS["signal_level_id"]),
        "speed_level_id": os.environ.get("MAP_SPEED_LEVEL_FIELD", DEFAULT_FILTER_FIELDS["speed_level_id"]),
        "operator_id": os.environ.get("MAP_OPERATOR_FIELD", DEFAULT_FILTER_FIELDS["operator_id"]),
        "network_id": os.environ.get("MAP_NETWORK_FIELD", DEFAULT_FILTER_FIELDS["network_id"]),
        "district_id": os.environ.get("MAP_DISTRICT_ID_FIELD", DEFAULT_FILTER_FIELDS["district_id"]),
        "device_id": os.environ.get("MAP_DEVICE_FIELD", DEFAULT_FILTER_FIELDS["device_id"]),
    }


def _build_filters(params: Dict[str, str]) -> Tuple[List[str], List]:
    fields = get_filter_fields()
    clauses: List[str] = []
    values: List = []

    def add_clause(key: str, sql_op: str = "="):
        if key in params and params[key] not in (None, "", "todos", "todas"):
            field = _safe_identifier(fields[key])
            clauses.append(f"{field} {sql_op} %s")
            values.append(params[key])

    add_clause("moment_id")
    add_clause("altitude_level_id")
    add_clause("signal_level_id")
    add_clause("speed_level_id")
    add_clause("operator_id")
    add_clause("network_id")
    add_clause("district_id")
    add_clause("device_id")

    # fechas
    ts_field = _safe_identifier(fields["timestamp"])
    if params.get("date_from"):
        clauses.append(f"DATE({ts_field}) >= %s")
        values.append(params["date_from"])
    if params.get("date_to"):
        clauses.append(f"DATE({ts_field}) <= %s")
        values.append(params["date_to"])

    if params.get("time_from"):
        clauses.append(f"CAST({ts_field} AS time) >= %s")
        values.append(params["time_from"])
    if params.get("time_to"):
        clauses.append(f"CAST({ts_field} AS time) <= %s")
        values.append(params["time_to"])
    return clauses, values


def fetch_dimensions(filters: Dict[str, str] | None = None) -> List[Dict]:
    filters = filters or {}
    cfg = get_map_config()
    try:
        table = _safe_identifier(cfg["table"])
        select_fields: List[Tuple[str, str]] = [
            ("name", _safe_identifier(cfg["name_field"])),
            ("zone", _safe_identifier(cfg["zone_field"])),
            ("district", _safe_identifier(cfg["district_field"])),
            ("latitude", _safe_identifier(cfg["lat_field"])),
            ("longitude", _safe_identifier(cfg["lng_field"])),
            ("value", _safe_identifier(cfg["value_field"])),
        ]
    except ValueError as exc:
        raise ValueError(f"ConfiguraciÃ³n invÃ¡lida de campos: {exc}") from exc

    select_sql = ", ".join(f"{col} AS {alias}" for alias, col in select_fields)
    sql = f"SELECT {select_sql} FROM {table}"
    where_clauses = []
    values: List = []
    if cfg.get("where"):
        where_clauses.append(cfg["where"])

    filter_clauses, filter_values = _build_filters(filters)
    where_clauses.extend(filter_clauses)

    where_clauses.append(f"{_safe_identifier(cfg['lat_field'])} IS NOT NULL")
    where_clauses.append(f"{_safe_identifier(cfg['lng_field'])} IS NOT NULL")

    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
    if cfg.get("limit"):
        sql += f" LIMIT {int(cfg['limit'])}"

    with connection.cursor() as cursor:
        cursor.execute(sql, filter_values)
        columns = [col[0] for col in cursor.description]
        data = [dict(zip(columns, row)) for row in cursor.fetchall()]

    colors_by_district: Dict[str, str] = {}
    for item in data:
        district_key = item.get("district") or "Sin distrito"
        if district_key not in colors_by_district:
            colors_by_district[district_key] = _color_for_key(str(district_key))
        item["color"] = colors_by_district[district_key]
    return data


def summarize_by_zone(dimensions: List[Dict]) -> List[Dict]:
    grouped: Dict[str, Dict] = {}
    for row in dimensions:
        zone = row.get("zone") or "Sin zona"
        district = row.get("district")
        entry = grouped.setdefault(
            zone,
            {
                "zone": zone,
                "count": 0,
                "districts": set(),
                "color": _color_for_key(str(zone)),
                "sample": [],
            },
        )
        entry["count"] += 1
        if district:
            entry["districts"].add(district)
        if len(entry["sample"]) < 5:
            entry["sample"].append(
                {
                    "name": row.get("name"),
                    "zone": zone,
                    "district": district,
                    "latitude": row.get("latitude"),
                    "longitude": row.get("longitude"),
                    "value": row.get("value"),
                    "color": row.get("color"),
                }
            )

    result = []
    for zone, payload in grouped.items():
        result.append(
            {
                "zone": zone,
                "color": payload["color"],
                "count": payload["count"],
                "district_count": len(payload["districts"]),
                "sample": payload["sample"],
            }
        )
    return sorted(result, key=lambda x: x["zone"])


def summarize_by_district(dimensions: List[Dict]) -> List[Dict]:
    grouped: Dict[str, Dict] = defaultdict(lambda: {"district": None, "count": 0, "color": None})
    for row in dimensions:
        district = row.get("district") or "Sin distrito"
        entry = grouped[district]
        entry["district"] = district
        entry["count"] += 1
        entry["color"] = entry["color"] or _color_for_key(str(district))
    return sorted(grouped.values(), key=lambda x: x["district"])


def fetch_district_polygons() -> List[Dict]:
    cfg = get_district_config()
    try:
        table = _safe_identifier(cfg["table"])
        select_fields: List[Tuple[str, str]] = [
            ("id", _safe_identifier(cfg["id_field"])),
            ("code", _safe_identifier(cfg["code_field"])),
            ("name", _safe_identifier(cfg["name_field"])),
            ("geojson", _safe_identifier(cfg["geojson_field"])),
        ]
    except ValueError as exc:
        raise ValueError(f"ConfiguraciÃ³n invÃ¡lida de distritos: {exc}") from exc

    select_sql = ", ".join(f"{col} AS {alias}" for alias, col in select_fields)
    sql = f"SELECT {select_sql} FROM {table}"
    if cfg.get("where"):
        sql += f" WHERE {cfg['where']}"

    with connection.cursor() as cursor:
        cursor.execute(sql)
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    parsed: List[Dict] = []
    for row in rows:
        geojson_text = row.get("geojson")
        try:
            data = json.loads(geojson_text) if geojson_text else {}
            coordinates = data.get("coordinates") or []
        except Exception:
            coordinates = []

        polygons: List[List[Dict[str, float]]] = []
        for polygon in coordinates:
            if not polygon:
                continue
            outer_ring = polygon[0]
            path = []
            for point in outer_ring:
                try:
                    lng, lat = float(point[0]), float(point[1])
                    path.append({"lat": lat, "lng": lng})
                except Exception:
                    continue
            if path:
                polygons.append(path)

        parsed.append(
            {
                "id": row.get("id"),
                "code": row.get("code"),
                "name": row.get("name"),
                "color": _color_for_key(str(row.get("name") or row.get("code") or row.get("id"))),
                "polygons": polygons,
            }
        )
    return parsed


def fetch_heatmap(filters: Dict[str, str] | None = None) -> List[Dict]:
    """Devuelve puntos filtrados (lat/lng) respetando todos los filtros activos."""
    filters = filters or {}
    cfg = get_map_config()
    fields = get_filter_fields()
    try:
        table = _safe_identifier(cfg["table"])
        lat = _safe_identifier(cfg["lat_field"])
        lng = _safe_identifier(cfg["lng_field"])
        device = _safe_identifier(fields["device_id"])
    except ValueError as exc:
        raise ValueError(f"Configuraci?n inv?lida de heatmap: {exc}") from exc

    clauses, values = _build_filters(filters)
    clauses.append(f"{lat} IS NOT NULL")
    clauses.append(f"{lng} IS NOT NULL")
    where_sql = " AND ".join(clauses) if clauses else "1=1"

    sql = f"""
    SELECT {lat} AS lat,
           {lng} AS lng,
           {device} AS device_id
    FROM {table}
    WHERE {where_sql}
    """
    if HEAT_LIMIT:
        try:
            sql += f" LIMIT {int(HEAT_LIMIT)}"
        except Exception:
            pass

    with connection.cursor() as cursor:
        cursor.execute(sql, values)
        rows = cursor.fetchall()

    return [{"lat": row[0], "lng": row[1], "count": 1, "device_id": row[2]} for row in rows]

def fetch_filter_options() -> Dict[str, List[Dict]]:
    tables = {
        "moments": ("dim_momento", "momento_id", "momento_dia"),
        "altitude_levels": ("dim_nivel_altitud", "nivel_altitud_id", "nivel_altitud"),
        "signal_levels": ("dim_nivel_senal", "nivel_senal_id", "nivel_senal"),
        "speed_levels": ("dim_nivel_velocidad", "nivel_velocidad_id", "nivel_velocidad"),
        "operators": ("dim_operador", "operador_id", "nombre_operador"),
        "networks": ("dim_red", "red_id", "tipo_red"),
    }
    result: Dict[str, List[Dict]] = {}
    with connection.cursor() as cursor:
        for key, (table, id_field, name_field) in tables.items():
            try:
                cursor.execute(
                    f"SELECT {_safe_identifier(id_field)}, {_safe_identifier(name_field)} FROM {_safe_identifier(table)} ORDER BY 1"
                )
                rows = cursor.fetchall()
                result[key] = [{"id": r[0], "name": r[1]} for r in rows]
            except Exception:
                result[key] = []
    return result

