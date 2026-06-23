from __future__ import annotations

import argparse
import csv
import io
import re
from pathlib import Path
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Depot

HEADER_LINES = 25
FIELD_COUNT = 13
CSV_FIELDS = [
    'row_id',
    'title',
    'total_score',
    'reviews_count',
    'street',
    'city',
    'state',
    'country_code',
    'website',
    'phone',
    'categories',
    'url',
    'category_name',
]

CLASSIC_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    'name': ('name', 'nom', 'depot', 'depot_name', 'point_name', 'title'),
    'address': ('address', 'adresse', 'street', 'location', 'localisation'),
    'city': ('city', 'ville', 'commune'),
    'quartier': ('quartier', 'district', 'zone', 'sector'),
    'latitude': ('latitude', 'lat', 'y', 'gps_lat', 'gps_latitude'),
    'longitude': ('longitude', 'lng', 'lon', 'x', 'gps_lng', 'gps_longitude'),
    'phone': ('phone', 'telephone', 'téléphone', 'tel', 'mobile'),
    'plv_code': ('plv_code', 'plv', 'code_plv', 'code'),
    'client_name': ('client_name', 'nom_client', 'client', 'contact_name'),
    'maps_url': ('maps_url', 'google_maps', 'maps', 'url', 'link', 'lien'),
    'capacity_6kg': ('capacity_6kg', 'capacite_6kg', 'cap_6kg'),
    'capacity_12kg': ('capacity_12kg', 'capacite_12kg', 'cap_12kg'),
    'status': ('status', 'statut', 'etat'),
    'comments': ('comments', 'commentaires', 'notes', 'note', 'comment', 'commentaire'),
}

CITY_REFERENCES: dict[str, tuple[float, float]] = {
    'ouagadougou': (12.3714, -1.5197),
    'tanghin-dassouri': (12.2722, -1.6684),
    'bobo-dioulasso': (11.1771, -4.2979),
    'koudougou': (12.2526, -2.3627),
}


def _clean(value: any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        value = str(value)
    elif not isinstance(value, str):
        value = str(value)
    cleaned = value.strip().strip('\ufeff')
    if not cleaned or cleaned in {'undefined', 'null', '#', '""', "''"}:
        return None
    return cleaned


def _normalize_header(value: any) -> str:
    if value is None:
        return ''
    if not isinstance(value, str):
        value = str(value)
    return (
        value.strip()
        .strip('\ufeff')
        .strip('"')
        .strip("'")
        .lower()
        .replace('é', 'e')
        .replace('è', 'e')
        .replace('ê', 'e')
        .replace('à', 'a')
        .replace('ù', 'u')
        .replace('ô', 'o')
        .replace('ï', 'i')
        .replace('î', 'i')
        .replace('-', '_')
        .replace(' ', '_')
    )


def _detect_delimiter(text: str) -> str:
    first_line = next((line for line in text.splitlines() if line.strip()), '')
    if not first_line:
        return ','
    semicolon_count = first_line.count(';')
    comma_count = first_line.count(',')
    tab_count = first_line.count('\t')
    
    if semicolon_count > comma_count and semicolon_count > tab_count:
        return ';'
    if tab_count > comma_count and tab_count > semicolon_count:
        return '\t'
    return ','


def _parse_float(value: any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = _clean(value)
    if cleaned is None:
        return None
    try:
        return float(cleaned.replace(',', '.'))
    except ValueError:
        return None


def _parse_int(value: any, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    cleaned = _clean(value)
    if cleaned is None:
        return default
    try:
        return int(float(cleaned.replace(',', '.')))
    except ValueError:
        return default


def _pick_value(row: dict[str, any], field: str) -> str | None:
    aliases = CLASSIC_FIELD_ALIASES.get(field, (field,))
    for alias in aliases:
        value = row.get(alias)
        cleaned = _clean(value)
        if cleaned is not None:
            return cleaned
    return None


def _normalize_row_keys(row: dict[str, any]) -> dict[str, any]:
    normalized: dict[str, any] = {}
    for key, value in row.items():
        normalized[_normalize_header(key)] = value
    return normalized


def _looks_like_classic_csv(text: str) -> bool:
    first_line = next((line for line in text.splitlines() if line.strip()), '')
    if not first_line:
        return False
    delimiter = _detect_delimiter(text)
    normalized_headers = {_normalize_header(part) for part in first_line.split(delimiter)}
    has_name = bool(normalized_headers.intersection(CLASSIC_FIELD_ALIASES['name']))
    has_lat = bool(normalized_headers.intersection(CLASSIC_FIELD_ALIASES['latitude']))
    has_lng = bool(normalized_headers.intersection(CLASSIC_FIELD_ALIASES['longitude']))
    return has_name and has_lat and has_lng


def _load_locator_records_from_lines(raw_lines: list[str]) -> list[dict[str, str | None]]:
    payload = [line.strip().strip('\ufeff') for line in raw_lines if line.strip()]
    if len(payload) <= HEADER_LINES:
        return []
    rows = payload[HEADER_LINES:]

    records: list[dict[str, str | None]] = []
    for index in range(0, len(rows), FIELD_COUNT):
        chunk = rows[index:index + FIELD_COUNT]
        if not chunk:
            continue
        if len(chunk) < FIELD_COUNT:
            chunk = chunk + [None] * (FIELD_COUNT - len(chunk))
        record = dict(zip(CSV_FIELDS, chunk, strict=False))
        title = _clean(record.get('title'))
        if not title:
            continue
        records.append(record)
    return records


def _load_classic_records_from_text(text: str) -> list[dict[str, str | None]]:
    stream = io.StringIO(text)
    delimiter = _detect_delimiter(text)
    reader = csv.DictReader(stream, delimiter=delimiter)
    records: list[dict[str, str | None]] = []
    for raw_row in reader:
        row = _normalize_row_keys(raw_row)
        name = _pick_value(row, 'name')
        latitude = _parse_float(_pick_value(row, 'latitude'))
        longitude = _parse_float(_pick_value(row, 'longitude'))
        if not name or latitude is None or longitude is None:
            continue
        records.append({
            'name': name,
            'address': _pick_value(row, 'address') or name,
            'city': _pick_value(row, 'city') or 'Ouagadougou',
            'quartier': _pick_value(row, 'quartier'),
            'latitude': str(latitude),
            'longitude': str(longitude),
            'phone': _pick_value(row, 'phone') or '',
            'plv_code': _pick_value(row, 'plv_code'),
            'client_name': _pick_value(row, 'client_name'),
            'maps_url': _pick_value(row, 'maps_url'),
            'capacity_6kg': str(_parse_int(_pick_value(row, 'capacity_6kg'))),
            'capacity_12kg': str(_parse_int(_pick_value(row, 'capacity_12kg'))),
            'status': _pick_value(row, 'status') or 'Actif',
            'comments': _pick_value(row, 'comments'),
        })
    return records


def _city_reference(city: str | None) -> tuple[float, float]:
    normalized = (city or 'ouagadougou').strip().lower()
    return CITY_REFERENCES.get(normalized, CITY_REFERENCES['ouagadougou'])


def _decode_plus_code(street: str | None, city: str | None) -> tuple[float, float] | None:
    value = _clean(street)
    if not value or '+' not in value:
        return None

    plus_code = value.split(',')[0].strip()
    if len(plus_code) < 6:
        return None

    ref_lat, ref_lng = _city_reference(city)
    try:
        from openlocationcode import openlocationcode as olc  # type: ignore

        full_code = plus_code
        if not olc.isFull(plus_code):
            full_code = olc.recoverNearest(plus_code, ref_lat, ref_lng)
        area = olc.decode(full_code)
        return (area.latitudeCenter, area.longitudeCenter)
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Le package openlocationcode est requis pour importer le format locator basé sur les plus codes."
        ) from exc
    except Exception:
        return None


def _extract_plv_code(title: str | None) -> str | None:
    if not title:
        return None
    match = re.search(r'\bPLV\s*([0-9A-Za-z-]+)\b', title, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def _build_address(record: dict[str, str | None]) -> str:
    street = _clean(record.get('street'))
    city = _clean(record.get('city'))
    parts = [part for part in [street, city, 'Burkina Faso'] if part]
    return ', '.join(parts)


def _build_unique_name(base_name: str, city: str | None, row_id: str | None, existing_names: set[str]) -> str:
    candidate = base_name.strip()
    if candidate.lower() not in existing_names:
        existing_names.add(candidate.lower())
        return candidate

    suffixes = [
        city,
        _extract_plv_code(base_name),
        row_id,
    ]
    for suffix in suffixes:
        if not suffix:
            continue
        next_candidate = f'{base_name} - {suffix}'
        if next_candidate.lower() not in existing_names:
            existing_names.add(next_candidate.lower())
            return next_candidate

    counter = 2
    while True:
        next_candidate = f'{base_name} - {counter}'
        if next_candidate.lower() not in existing_names:
            existing_names.add(next_candidate.lower())
            return next_candidate
        counter += 1


def _upsert_depot_from_record(
    db: Session,
    existing_names: set[str],
    *,
    name: str,
    latitude: float,
    longitude: float,
    address: str,
    city: str | None,
    quartier: str | None,
    plv_code: str | None,
    maps_url: str | None,
    phone: str,
    row_id: str | None = None,
    capacity_6kg: int = 0,
    capacity_12kg: int = 0,
    status: str = "Actif",
    comments: str | None = None,
    client_name: str | None = None,
) -> str:
    depot = None

    if maps_url:
        depot = db.query(Depot).filter(Depot.maps_url == maps_url).first()
    if depot is None and plv_code:
        depot = db.query(Depot).filter(Depot.plv_code == plv_code).first()
    if depot is None:
        depot = db.query(Depot).filter(Depot.name == name).first()

    if depot is None:
        unique_name = _build_unique_name(name, city, row_id, existing_names)
        depot = Depot(
            name=unique_name,
            latitude=latitude,
            longitude=longitude,
            address=address,
            city=city or 'Ouagadougou',
            quartier=quartier,
            plv_code=plv_code,
            client_name=client_name,
            maps_url=maps_url,
            phone=phone,
            capacity_6kg=capacity_6kg,
            capacity_12kg=capacity_12kg,
            stock_6kg_plein=0,
            stock_12kg_plein=0,
            is_active=(status == "Actif"),
            status=status or "Actif",
            comments=comments,
        )
        db.add(depot)
        return 'created'

    if depot.name.lower() in existing_names:
        existing_names.discard(depot.name.lower())
    depot.name = _build_unique_name(name, city, row_id, existing_names)
    depot.latitude = latitude
    depot.longitude = longitude
    depot.address = address
    depot.city = city or depot.city
    depot.quartier = quartier or depot.quartier
    depot.plv_code = plv_code or depot.plv_code
    depot.client_name = client_name or depot.client_name
    depot.maps_url = maps_url or depot.maps_url
    depot.phone = phone or depot.phone or ''
    depot.capacity_6kg = capacity_6kg if capacity_6kg else depot.capacity_6kg
    depot.capacity_12kg = capacity_12kg if capacity_12kg else depot.capacity_12kg
    if status:
        depot.status = status
        depot.is_active = (status == "Actif")
    if comments is not None:
        depot.comments = comments
    return 'updated'


def _import_classic_records(records: list[dict[str, str | None]], db: Session) -> tuple[int, int, int]:
    created = 0
    updated = 0
    skipped = 0

    existing_names = {depot.name.lower() for depot in db.query(Depot).all()}

    for record in records:
        name = _clean(record.get('name'))
        latitude = _parse_float(record.get('latitude'))
        longitude = _parse_float(record.get('longitude'))
        if not name or latitude is None or longitude is None:
            skipped += 1
            continue

        result = _upsert_depot_from_record(
            db,
            existing_names,
            name=name,
            latitude=latitude,
            longitude=longitude,
            address=_clean(record.get('address')) or name,
            city=_clean(record.get('city')) or 'Ouagadougou',
            quartier=_clean(record.get('quartier')),
            plv_code=_clean(record.get('plv_code')),
            client_name=_clean(record.get('client_name')),
            maps_url=_clean(record.get('maps_url')),
            phone=_clean(record.get('phone')) or '',
            capacity_6kg=_parse_int(record.get('capacity_6kg')),
            capacity_12kg=_parse_int(record.get('capacity_12kg')),
            status=_clean(record.get('status')) or 'Actif',
            comments=_clean(record.get('comments')),
        )
        if result == 'created':
            created += 1
        else:
            updated += 1

    db.commit()
    return created, updated, skipped


def import_locator_csv_from_records(records: list[dict[str, str | None]], db: Session) -> tuple[int, int, int]:
    created = 0
    updated = 0
    skipped = 0

    existing_names = {depot.name.lower() for depot in db.query(Depot).all()}

    for record in records:
        title = _clean(record.get('title'))
        city = _clean(record.get('city')) or 'Ouagadougou'
        maps_url = _clean(record.get('url'))
        phone = _clean(record.get('phone')) or ''
        website = _clean(record.get('website'))
        category_name = _clean(record.get('category_name'))
        street = _clean(record.get('street'))
        row_id = _clean(record.get('row_id'))
        coordinates = _decode_plus_code(street, city)

        if not title or coordinates is None:
            skipped += 1
            continue

        latitude, longitude = coordinates
        plv_code = _extract_plv_code(title)
        address = _build_address(record)
        result = _upsert_depot_from_record(
            db,
            existing_names,
            name=title,
            latitude=latitude,
            longitude=longitude,
            address=address,
            city=city,
            quartier=category_name,
            plv_code=plv_code,
            maps_url=maps_url or website,
            phone=phone,
            row_id=row_id,
        )
        if result == 'created':
            created += 1
        else:
            updated += 1

    db.commit()
    return created, updated, skipped


def import_depots_csv_text(text: str, db: Session = None) -> tuple[int, int, int, str]:
    is_external_db = (db is not None)
    if not is_external_db:
        db = SessionLocal()
        
    try:
        normalized_text = text.lstrip('\ufeff')
        if _looks_like_classic_csv(normalized_text):
            records = _load_classic_records_from_text(normalized_text)
            created, updated, skipped = _import_classic_records(records, db)
            return created, updated, skipped, 'classic'

        raw_lines = normalized_text.splitlines()
        records = _load_locator_records_from_lines(raw_lines)
        created, updated, skipped = import_locator_csv_from_records(records, db)
        return created, updated, skipped, 'locator'
    finally:
        if not is_external_db:
            db.close()


def import_depots_excel_bytes(content_bytes: bytes, db: Session = None) -> tuple[int, int, int, str]:
    is_external_db = (db is not None)
    if not is_external_db:
        db = SessionLocal()
        
    try:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(content_bytes), data_only=True)
        sheet = wb.active
        
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return 0, 0, 0, 'excel'
            
        # Find the header row
        header_row_idx = None
        headers = []
        for idx, row in enumerate(rows):
            row_headers = [_normalize_header(str(cell)) for cell in row if cell is not None]
            has_name = any(h in CLASSIC_FIELD_ALIASES['name'] for h in row_headers)
            has_lat = any(h in CLASSIC_FIELD_ALIASES['latitude'] for h in row_headers)
            has_lng = any(h in CLASSIC_FIELD_ALIASES['longitude'] for h in row_headers)
            if has_name and has_lat and has_lng:
                headers = [str(cell).strip() if cell is not None else "" for cell in row]
                header_row_idx = idx
                break
                
        if header_row_idx is None:
            # Fallback: check if the first row could be headers
            headers = [str(cell).strip() if cell is not None else "" for cell in rows[0]]
            header_row_idx = 0
            
        records = []
        for row in rows[header_row_idx + 1:]:
            if not any(cell is not None for cell in row):
                continue
                
            raw_row = {}
            for col_idx, cell in enumerate(row):
                if col_idx < len(headers):
                    header = headers[col_idx]
                    if header:
                        raw_row[header] = cell
                        
            row_norm = _normalize_row_keys(raw_row)
            name = _pick_value(row_norm, 'name')
            latitude = _parse_float(_pick_value(row_norm, 'latitude'))
            longitude = _parse_float(_pick_value(row_norm, 'longitude'))
            
            if not name or latitude is None or longitude is None:
                continue
                
            records.append({
                'name': name,
                'address': _pick_value(row_norm, 'address') or name,
                'city': _pick_value(row_norm, 'city') or 'Ouagadougou',
                'quartier': _pick_value(row_norm, 'quartier'),
                'latitude': str(latitude),
                'longitude': str(longitude),
                'phone': _pick_value(row_norm, 'phone') or '',
                'plv_code': _pick_value(row_norm, 'plv_code'),
                'client_name': _pick_value(row_norm, 'client_name'),
                'maps_url': _pick_value(row_norm, 'maps_url'),
                'capacity_6kg': str(_parse_int(_pick_value(row_norm, 'capacity_6kg'))),
                'capacity_12kg': str(_parse_int(_pick_value(row_norm, 'capacity_12kg'))),
                'status': _pick_value(row_norm, 'status') or 'Actif',
                'comments': _pick_value(row_norm, 'comments'),
            })
            
        created, updated, skipped = _import_classic_records(records, db)
        return created, updated, skipped, 'excel'
    finally:
        if not is_external_db:
            db.close()
