#!/usr/bin/env python3
"""Export a crawler's unified JSON into a small public website feed."""
import argparse
from datetime import datetime, timedelta
from html import unescape
from html.parser import HTMLParser
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

class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in ('p', 'br', 'div', 'li'):
            self.parts.append(' ')

    def handle_endtag(self, tag):
        if tag in ('p', 'div', 'li'):
            self.parts.append(' ')


def clean(value):
    parser = TextParser()
    parser.feed(unescape(str(value or '')))
    parser.close()
    return ' '.join(''.join(parser.parts).split())


def raw_fields(row):
    raw = row.get('raw_data') or {}
    if not isinstance(raw, dict):
        raw = {}
    fields = raw.get('fields', row.get('fields', ''))
    names = fields.split(',') if isinstance(fields, str) else []
    # Decode by the fields header; p4/p5/p22 are fallbacks for headerless data.
    decoded = {name.strip(): raw.get(f'p{i}', row.get(f'p{i}'))
               for i, name in enumerate(names) if name.strip()}
    return {**raw, **{key: value for key, value in decoded.items() if value is not None}}


DATE = re.compile(r'\b([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})\b')
CLOCK = re.compile(r'\b(\d{1,2})(?::(\d{2}))?\s*([AP]\.?M\.?)\b', re.I)


def parse_schedule(value):
    """Parse ZotSpot's HTML date + time range without depending on paragraphs."""
    text = clean(value)
    dates = list(DATE.finditer(text))
    if not dates:
        return None
    starts, ends = [], []
    for index, match in enumerate(dates):
        month = match[1][:3].title()
        try:
            day = datetime.strptime(f'{month} {match[2]} {match[3]}', '%b %d %Y')
        except ValueError:
            return None
        segment = text[match.end():dates[index + 1].start() if index + 1 < len(dates) else len(text)]
        times = list(CLOCK.finditer(segment))
        values = []
        for clock in times:
            hour, minute = int(clock[1]), int(clock[2] or 0)
            if not 1 <= hour <= 12 or not 0 <= minute <= 59:
                return None
            hour = hour % 12 + (12 if clock[3][0].upper() == 'P' else 0)
            values.append(day.replace(hour=hour, minute=minute))
        starts.append(values[0] if values else day)
        ends.append(values[-1] if values else day)
    all_day = not CLOCK.search(text)
    start = starts[0]
    # One dated paragraph followed by two times is the common single-day layout.
    clock_count = len(CLOCK.findall(text))
    end = ends[-1] if len(dates) > 1 or clock_count > 1 else None
    if len(dates) == 1 and end and end < start:
        end += timedelta(days=1)  # Explicit overnight range, e.g. 11 PM – 1 AM.
    if all_day:
        end = (ends[-1] if end else start).replace(hour=23, minute=59, second=59)
    return start.isoformat(), end.isoformat() if end else None, all_day, text


def event_dates(row, raw):
    for value in (raw.get('eventDates'), raw.get('eventsDates'), row.get('eventDates'),
                  row.get('eventsDates'), raw.get('p4'), row.get('p4'),
                  row.get('start_date'), row.get('start_data'),
                  raw.get('start_date'), raw.get('start_data')):
        parsed = parse_schedule(value)
        if parsed:
            start, end, all_day, text = parsed
            # Separate end_date may carry another full date/time or just a clock.
            if not end and row.get('end_date'):
                separate = parse_schedule(row['end_date'])
                if separate:
                    end = separate[1] or separate[0]
                else:
                    clock = CLOCK.search(clean(row['end_date']))
                    if clock:
                        combined = parse_schedule(text + ' – ' + clean(row['end_date']))
                        end = combined[1] if combined else None
            return start, end, all_day, text
    return row.get('start_datetime'), row.get('end_datetime'), bool(row.get('all_day')), row.get('date_text', '')


class LabelParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.labels, self.text, self.depth, self.aria = [], [], 0, ''

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.depth, self.text = 1, []
            self.aria = dict(attrs).get('aria-label', '')
        elif self.depth:
            self.depth += 1
        elif tag in ('br', 'p', 'div', 'li'):
            self.text.append(' | ')

    def handle_data(self, data):
        self.text.append(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self.depth:
            self.labels.append(clean(''.join(self.text)) or clean(self.aria))
            self.depth, self.text = 0, []
        elif self.depth:
            self.depth -= 1


def labels(value):
    if isinstance(value, list):
        return unique(label for item in value for label in labels(item))
    parser = LabelParser()
    parser.feed(unescape(str(value or '')))
    parser.close()
    if parser.labels:
        return unique(parser.labels)
    text = clean(''.join(parser.text))
    return unique(re.split(r'\s*[,;|]\s*', text))


def unique(values):
    result, seen = [], set()
    for value in values:
        value = clean(value)
        if value and value.casefold() not in seen:
            seen.add(value.casefold())
            result.append(value)
    return result


def event_labels(row, raw):
    # Original eventCategory is authoritative; normalized categories are fallback.
    primary = next((value for value in (raw.get('eventCategory'), row.get('eventCategory'),
                   raw.get('p5'), row.get('p5'), row.get('category')) if value), None)
    categories = labels(primary if primary else row.get('categories', []))
    original_tags = raw.get('eventTags') or row.get('eventTags') or raw.get('p22') or row.get('p22')
    topics = labels(original_tags if original_tags else row.get('tags', []))
    return categories, unique(categories + topics)


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
        raw = raw_fields(row)
        zotspot = any(raw.get(key) for key in ('eventDates', 'p4'))
        event['source'] = clean(row.get('source') or ('zotspot' if zotspot else 'unknown'))
        event['source_url'] = row.get('source_url') or row.get('url')
        event['organizer_name'] = row.get('organizer_name') or row.get('group_name')
        event['rsvp_url'] = row.get('rsvp_url') or row.get('url')
        event['id'] = str(row['id'])
        key = (event['source'], event['id'])
        if key in seen:
            continue
        seen.add(key)
        timezone = row.get('timezone') or 'America/Los_Angeles'
        event['timezone'] = timezone
        start, end, all_day, date_text = event_dates(row, raw)
        event['start_datetime'] = iso(start, timezone)
        event['end_datetime'] = iso(end, timezone)
        event['all_day'] = all_day
        event['date_text'] = date_text
        if event['start_datetime'] and event['end_datetime'] and datetime.fromisoformat(event['end_datetime']) < datetime.fromisoformat(event['start_datetime']):
            raise ValueError(f'Event {event["id"]} ends before it starts')
        for field in ('title', 'description', 'location', 'organizer_name', 'cost'):
            event[field] = clean(event[field])
        event['categories'], event['tags'] = event_labels(row, raw)
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
