import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('sync_events', Path(__file__).resolve().parents[1] / 'scripts/sync_events.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

class ExportTests(unittest.TestCase):
    def event(self, **changes):
        row = dict(id='1', title='Meeting', source='zotspot',
                   start_datetime='2026-11-17T18:00:00', timezone='America/Los_Angeles',
                   source_url='https://zotspot.uci.edu/rsvp_boot?id=1')
        return {**row, **changes}

    def test_timezone_does_not_depend_on_viewers_timezone(self):
        self.assertEqual(sync.export([self.event()])[0]['start_datetime'], '2026-11-17T18:00:00-08:00')
        self.assertEqual(sync.export([self.event(start_datetime='2026-07-17T18:00:00')])[0]['start_datetime'], '2026-07-17T18:00:00-07:00')

    def test_recovers_multiday_end_before_discarding_raw_data(self):
        event = self.event(start_datetime='2021-06-28T00:00:00', raw_data={
            'p4': '<p>Mon, Jun 28, 2021 12:00 AM &ndash;</p><p>Sat, Jan 1, 2028 10:00 AM</p>', 'cookie': 'secret'})
        result = sync.export([event])[0]
        self.assertEqual(result['end_datetime'], '2028-01-01T10:00:00-08:00')
        self.assertNotIn('raw_data', result)
        self.assertNotIn('secret', str(result))

    def test_deduplicates_within_source_but_retains_other_sources(self):
        self.assertEqual(len(sync.export([self.event(), self.event(), self.event(source='club-site')])), 2)

    def test_sanitizes_markup_and_unsafe_links(self):
        result = sync.export([self.event(title='<b>Meeting &amp; snacks</b>', rsvp_url='javascript:alert(1)')])[0]
        self.assertEqual(result['title'], 'Meeting & snacks')
        self.assertIsNone(result['rsvp_url'])

    def test_invalid_feed_rejected(self):
        for value in ({}, [{}], [self.event(start_datetime='not a date')], [self.event(end_datetime='2026-01-01T00:00:00')]):
            with self.assertRaises(ValueError):
                sync.export(value)

if __name__ == '__main__':
    unittest.main()
