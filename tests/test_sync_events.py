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

    def test_split_html_and_hour_only_times_override_bad_normalized_date(self):
        event = self.event(start_datetime='2025-01-01T00:00:00', end_datetime='2025-01-01T01:00:00', raw_data={
            'p4': "<p style='margin:0'>Wed, Nov 11, 2026</p><p>8 AM &ndash; 10 AM</p>"})
        result = sync.export([event])[0]
        self.assertEqual(result['start_datetime'], '2026-11-11T08:00:00-08:00')
        self.assertEqual(result['end_datetime'], '2026-11-11T10:00:00-08:00')

    def test_decodes_named_fields_even_when_positions_change(self):
        event = self.event(raw_data={'fields': 'eventCategory,eventDates',
            'p0': 'Workshop', 'p1': '<p>Thu, Jul 2, 2026</p><p>12 PM – 1:30 PM</p>'})
        result = sync.export([event])[0]
        self.assertEqual(result['start_datetime'], '2026-07-02T12:00:00-07:00')
        self.assertEqual(result['end_datetime'], '2026-07-02T13:30:00-07:00')
        self.assertEqual(result['categories'], ['Workshop'])

    def test_start_date_and_start_data_fallbacks(self):
        for key in ('start_date', 'start_data', 'eventDates', 'eventsDates'):
            with self.subTest(key=key):
                result = sync.export([self.event(**{key: '&lt;p&gt;Fri, Nov 20, 2026&lt;/p&gt;&lt;p&gt;11:30 AM &amp;ndash; 12 PM&lt;/p&gt;'})])[0]
                self.assertEqual(result['start_datetime'], '2026-11-20T11:30:00-08:00')
                self.assertEqual(result['end_datetime'], '2026-11-20T12:00:00-08:00')

    def test_overnight_and_explicit_multiday_ranges(self):
        result = sync.export([self.event(eventDates='<p>Fri, Nov 20, 2026</p><p>11 PM – 1 AM</p>')])[0]
        self.assertEqual(result['end_datetime'], '2026-11-21T01:00:00-08:00')
        result = sync.export([self.event(eventDates='<p>Sat, Oct 31, 2026 11:30 PM –</p><p>Sun, Nov 1, 2026 3 AM</p>')])[0]
        self.assertEqual(result['start_datetime'], '2026-10-31T23:30:00-07:00')
        self.assertEqual(result['end_datetime'], '2026-11-01T03:00:00-08:00')

    def test_date_only_has_no_invented_display_time(self):
        result = sync.export([self.event(eventDates='<p>Fri, Nov 20, 2026</p>')])[0]
        self.assertTrue(result['all_day'])
        self.assertEqual(result['end_datetime'], '2026-11-20T23:59:59-08:00')

    def test_original_category_and_visible_topic_labels_override_stale_fields(self):
        result = sync.export([self.event(categories=['Events', 'Clubs'], tags=['Old tag'], raw_data={
            'p5': '<a><span>Health &amp; Wellness</span></a>',
            'p22': '<p><a aria-label="Health and Wellness"><span>Health &amp; Wellness</span></a><a aria-label="Yoga"><span>Yoga</span></a><a><span>yoga</span></a></p>'})])[0]
        self.assertEqual(result['categories'], ['Health & Wellness'])
        self.assertEqual(result['tags'], ['Health & Wellness', 'Yoga'])

    def test_raw_crawler_record_preserves_action_link_and_organizer(self):
        result = sync.export([dict(id='raw1', title='Talk', group_name='Club',
            url='https://zotspot.uci.edu/rsvp_boot?id=raw1', category='Lecture',
            start_date='<p>Fri, Nov 20, 2026</p><p>6 PM – 7 PM</p>',
            raw_data={'p4': '<p>Fri, Nov 20, 2026</p><p>6 PM – 7 PM</p>'})])[0]
        self.assertEqual(result['organizer_name'], 'Club')
        self.assertEqual(result['source'], 'zotspot')
        self.assertEqual(result['rsvp_url'], 'https://zotspot.uci.edu/rsvp_boot?id=raw1')
        self.assertEqual(result['categories'], ['Lecture'])

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
