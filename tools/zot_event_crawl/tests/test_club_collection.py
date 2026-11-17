import json
import importlib.util
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/crawlers'))
from club_sources import Document, PublicClient, clean_url, directory_clubs, discover, platform, social_links
from club_event_crawler import collect, raw_record, structured_events

DIRECTORY='''<ul>
<li class="list-group-item"><fieldset><div role="group"><input id="cb_club_123" value="123"><h2>Club A &amp; Friends</h2>
<p class="grey-element">Campus Organizations - Arts</p>
<a href="https://club.example/" aria-label="Website">Website</a></div></fieldset></li>
<li class="list-group-item"><h2>Club B</h2><button id="a-mission_456"></button><a aria-label="Website" href="/ClubB/">Website</a></li>
</ul><a href="/club_signup?view=all&amp;">Load all 1000 groups</a>'''
HOME='''<html><title>Club A</title><body><a href="https://instagram.com/club.a/?utm_source=site">Instagram</a>
<a href="https://www.linkedin.com/company/club-a/">LinkedIn</a><a href="https://discord.gg/club123">Discord</a>
<a href="https://www.tiktok.com/@club.a">TikTok</a><a href="mailto:hello@club.example?subject=Hi">Email</a>
<a href="https://evilinstagram.com/fake">Fake</a><a href="https://instagram.com/p/POST/">A post, not a profile</a>
<a href="/events/">Events</a><a href="javascript:alert(1)">Ignore</a></body></html>'''
CLUB={'id':'123','name':'Club A','website':'https://club.example/','social_links':{},'pages':[]}

def event_page(**changes):
    event={'@context':'https://schema.org','@type':'Event','name':'Speaker night',
           'startDate':'2026-11-20T18:00:00','endDate':'2026-11-20T20:00:00',
           'description':'Meet &amp; learn','location':{'@type':'Place','name':'Student Center'},
           'keywords':['Career','Networking'],'url':'https://club.example/events/talk'}
    event.update(changes)
    return '<script type="application/ld+json">'+json.dumps({'@graph':[event]})+'</script>'

class FakeClient:
    def __init__(self,pages):
        self.pages,self.requests=pages,[]
    def fetch(self,url):
        self.requests.append(url)
        if url not in self.pages:
            return dict(requested_url=url,url=url,status='http_error',http_status=404,text='',content_type='text/html')
        value=self.pages[url]
        return dict(requested_url=url,url=url,status='ok',text=value,content_type='text/html')

class DiscoveryTests(unittest.TestCase):
    def test_directory_pairs_each_website_with_the_right_club(self):
        clubs,pages=directory_clubs(DIRECTORY,'https://zotspot.uci.edu/club_signup')
        self.assertEqual([c['id'] for c in clubs],['123','456'])
        self.assertEqual(clubs[0]['name'],'Club A & Friends')
        self.assertEqual(clubs[1]['website'],'https://zotspot.uci.edu/ClubB/')
        self.assertEqual(pages,['https://zotspot.uci.edu/club_signup?view=all&'])

    def test_real_social_links_keep_provenance_and_reject_lookalikes(self):
        links=social_links(HOME,'https://club.example/')
        self.assertEqual({v['platform'] for v in links},{'instagram','linkedin','discord','tiktok','email'})
        ig=next(v for v in links if v['platform']=='instagram')
        self.assertEqual(ig['url'],'https://www.instagram.com/club.a/')
        self.assertEqual(ig['found_on'],'https://club.example/')
        self.assertIsNone(platform('https://evilinstagram.com/fake'))
        self.assertEqual(clean_url('file:///etc/passwd'),'')

    def test_discovery_load_all_deduplicates_and_keeps_unprocessed_clubs(self):
        client=FakeClient({'https://zotspot.uci.edu/club_signup':DIRECTORY,
                          'https://zotspot.uci.edu/club_signup?view=all&':DIRECTORY,
                          'https://club.example/':HOME})
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'club_sources.json'
            clubs,report=discover(client,'https://zotspot.uci.edu/club_signup',output,max_clubs=1,pages_per_club=1)
            self.assertEqual(len(clubs),2)
            self.assertEqual(clubs[1]['crawl_status'],'not_started')
            self.assertEqual(report['clubs_with_instagram'],1)
            self.assertTrue(output.exists())
            self.assertTrue(output.with_name('club_discovery_report.json').exists())

    def test_network_client_rejects_private_destinations(self):
        client=PublicClient(delay=0)
        with patch('club_sources.socket.getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',80))]):
            with self.assertRaisesRegex(ValueError,'non_public'):
                client._validate('https://example.com/')

    def test_robots_block_is_reported_without_requesting_page(self):
        client=PublicClient(delay=0)
        with patch.object(client,'_validate'),patch.object(client,'allowed',return_value=False),patch.object(client,'_request') as request:
            result=client.fetch('https://example.com/')
            self.assertEqual(result['status'],'robots_blocked')
            request.assert_not_called()

class InterfaceTests(unittest.TestCase):
    def test_existing_club_crawler_entry_point_runs_without_optional_packages(self):
        entry=Path(__file__).resolve().parents[1]/'src/crawlers/club_crawler.py'
        for flags in (['--help'],['--collect-events','--help']):
            result=subprocess.run([sys.executable,'-B',str(entry),*flags],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('--pages-per-club',result.stdout)

class EventTests(unittest.TestCase):
    def test_structured_event_matches_unified_feed_schema(self):
        events,drafts=structured_events(event_page(),'https://club.example/events/',CLUB)
        self.assertEqual(drafts,[])
        self.assertEqual(events[0]['start_datetime'],'2026-11-20T18:00:00-08:00')
        self.assertEqual(events[0]['organizer_id'],'123')
        self.assertEqual(events[0]['tags'],['Career','Networking'])
        self.assertIsNone(events[0]['rsvp_required'])

    def test_structured_events_can_be_exported_for_the_website(self):
        exporter=Path(__file__).resolve().parents[3]/'scripts/sync_events.py'
        spec=importlib.util.spec_from_file_location('website_export',exporter)
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        events,_=structured_events(event_page(),'https://club.example/',CLUB)
        public=module.export(events)
        self.assertEqual(public[0]['source'],'club_website')
        self.assertEqual(public[0]['start_datetime'],'2026-11-20T18:00:00-08:00')
        self.assertEqual(public[0]['tags'],['Career','Networking'])

    def test_post_publication_time_is_never_an_event_date(self):
        html='<meta property="article:published_time" content="2026-11-01T12:00:00Z"><meta property="og:description" content="Join us next Friday!"><p>Join us next Friday!</p>'
        events,_=structured_events(html,'https://instagram.com/p/ABC/',CLUB)
        self.assertEqual(events,[])
        record=raw_record(dict(url='https://instagram.com/p/ABC/',status='ok',text=html,content_type='text/html'),CLUB)
        self.assertEqual(record['published_at'],'2026-11-01T12:00:00Z')
        self.assertEqual(record['description'],'Join us next Friday!')
        self.assertNotIn('start_datetime',record)

    def test_invalid_or_cancelled_events_remain_candidates(self):
        for fields in ({'startDate':None},{'startDate':'Friday at six'},{'eventStatus':'https://schema.org/EventCancelled'},{'endDate':'2025-01-01'}):
            events,drafts=structured_events(event_page(**fields),'https://club.example/',CLUB)
            self.assertEqual(events,[])
            self.assertEqual(len(drafts),1)

    def test_date_only_event_is_all_day(self):
        events,_=structured_events(event_page(startDate='2026-11-20',endDate=None),'https://club.example/',CLUB)
        self.assertTrue(events[0]['all_day'])
        self.assertEqual(events[0]['end_datetime'],'2026-11-20T23:59:59-08:00')

    def test_duplicate_events_and_raw_fallback_are_checkpointed(self):
        client=FakeClient({'https://club.example/':HOME+event_page(),
                          'https://club.example/events/':event_page()})
        with tempfile.TemporaryDirectory() as directory:
            events,raw=collect(client,[CLUB],directory,pages_per_club=2)
            self.assertEqual(len(events),1)
            self.assertEqual(len(raw),2)
            self.assertTrue(all('instagram.com' not in url for url in client.requests))
            self.assertTrue((Path(directory)/'club_raw_text.json').exists())
            self.assertTrue((Path(directory)/'club_event_crawl_report.json').exists())

    def test_event_pages_are_prioritized_before_social_pages(self):
        club={**CLUB,'social_links':{'instagram':[{'url':'https://www.instagram.com/club.a/'}]}}
        client=FakeClient({'https://club.example/':HOME,'https://club.example/events/':event_page()})
        with tempfile.TemporaryDirectory() as directory:
            events,raw=collect(client,[club],directory,pages_per_club=2,include_social=True)
            self.assertEqual(len(events),1)
            self.assertEqual(client.requests,['https://club.example/','https://club.example/events/'])

    def test_redirected_pages_are_not_collected_twice(self):
        class RedirectClient(FakeClient):
            def fetch(self,url):
                result=super().fetch(url)
                result['url']='https://club.example/'
                return result
        club={**CLUB,'website':'http://club.example/','pages':[{'url':'https://club.example/','status':'ok'}]}
        client=RedirectClient({'http://club.example/':'<p>A public website.</p>'})
        with tempfile.TemporaryDirectory() as directory:
            _,raw=collect(client,[club],directory,pages_per_club=3)
            self.assertEqual(len(raw),1)
            self.assertEqual(client.requests,['http://club.example/'])

    def test_social_collection_stays_bounded_and_preserves_failed_attempts(self):
        club={**CLUB,'social_links':{'instagram':[{'url':'https://www.instagram.com/club.a/'}]}}
        client=FakeClient({'https://club.example/':'<p>Plain page without events.</p>'})
        with tempfile.TemporaryDirectory() as directory:
            events,raw=collect(client,[club],directory,pages_per_club=2,include_social=True)
            self.assertEqual(events,[])
            self.assertEqual(len(raw),2)
            self.assertEqual(raw[-1]['status'],'http_error')

if __name__=='__main__':
    unittest.main()
