#!/usr/bin/env python3
"""Export a crawler's unified JSON into a small public website feed."""
import argparse
from datetime import datetime
from html import unescape
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('id', 'source', 'source_url', 'title', 'description', 'start_datetime',
          'end_datetime', 'timezone', 'location', 'location_type', 'organizer_name',
          'organizer_type', 'organizer_url', 'categories', 'tags', 'image_url',
          'rsvp_url', 'cost', 'last_updated')

def clean(value):
    return unescape(re.sub(r'<[^>]*>', ' ', str(value or ''))).strip()

def iso(value, timezone):
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(timezone))
    return dt.isoformat()

def export(source):
    if not isinstance(source, list):
        raise ValueError('Expected an array of unified event objects')
    result, seen = [], set()
    for row in source:
        if not isinstance(row, dict) or not row.get('id') or not row.get('title'):
            raise ValueError('Every event needs an id and title')
        event = {key: row.get(key) for key in FIELDS}
        event['source'] = clean(row.get('source') or 'unknown')
        event['id'] = str(row['id'])
        key = (event['source'], event['id'])
        if key in seen:
            continue
        seen.add(key)
        timezone = row.get('timezone') or 'America/Los_Angeles'
        event['timezone'] = timezone
        event['start_datetime'] = iso(row.get('start_datetime'), timezone)
        end = row.get('end_datetime')
        # The supplied crawler omitted end times, but preserved them in p4.
        if not end:
            raw = row.get('raw_data') or {}
            dates = re.findall(r'[A-Z][a-z]{2}, [A-Z][a-z]{2} \d{1,2}, \d{4} \d{1,2}:\d{2} [AP]M', clean(raw.get('p4')))
            if len(dates) > 1:
                end = datetime.strptime(dates[-1], '%a, %b %d, %Y %I:%M %p').isoformat()
        event['end_datetime'] = iso(end, timezone)
        if event['start_datetime'] and event['end_datetime'] and datetime.fromisoformat(event['end_datetime']) < datetime.fromisoformat(event['start_datetime']):
            raise ValueError(f'Event {event["id"]} ends before it starts')
        for field in ('title', 'description', 'location', 'organizer_name', 'cost'):
            event[field] = clean(event[field])
        for field in ('categories', 'tags'):
            if row.get(field) is not None and not isinstance(row[field], list):
                raise ValueError(f'{field} must be an array')
            event[field] = [clean(v) for v in row.get(field) or []]
        for field in ('source_url', 'organizer_url', 'image_url', 'rsvp_url'):
            value = str(event.get(field) or '')
            parts = urlsplit(value)
            event[field] = value if parts.scheme == 'https' and parts.netloc else None
        result.append(event)
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='Crawler data/output/unified_events.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/output/unified_events.json')
    args = parser.parse_args()
    events = export(json.loads(args.input.read_text(encoding='utf-8')))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.output.with_suffix('.tmp')
    tmp.write_text(json.dumps(events, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    tmp.replace(args.output)
    print(f'Exported {len(events)} events to {args.output} ({args.output.stat().st_size:,} bytes)')

if __name__ == '__main__':
    main()
