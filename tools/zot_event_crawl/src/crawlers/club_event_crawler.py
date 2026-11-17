#!/usr/bin/env python3
"""Collect club website/social text, extracting only explicitly structured events."""
import argparse
from collections import deque
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from club_sources import (ROOT, Document, PublicClient, clean_url, digest, now,
                          platform, relevant_pages, write_json)


def script_data(doc):
    for node in doc.root.walk('script'):
        if node.attrs.get('type','').split(';')[0].strip().lower() == 'application/ld+json':
            try:
                yield json.loads(''.join(child for child in node.children if isinstance(child,str)))
            except (ValueError, TypeError):
                continue


def event_nodes(value):
    if isinstance(value,list):
        for child in value:
            yield from event_nodes(child)
    elif isinstance(value,dict):
        types=value.get('@type',[])
        types=[types] if isinstance(types,str) else types
        if any(isinstance(t,str) and t.rsplit('/',1)[-1].endswith('Event') for t in types):
            yield value
        for child in value.values():
            if isinstance(child,(dict,list)):
                yield from event_nodes(child)


def text_value(value):
    if isinstance(value,str):
        return Document(value).root.text()
    if isinstance(value,dict):
        return text_value(value.get('name',''))
    return ''


def date_value(value, zone, end=False):
    if not isinstance(value,str) or not value:
        return None
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if len(value)==10 and end:
        dt=dt.replace(hour=23,minute=59,second=59)
    if dt.tzinfo is None:
        dt=dt.replace(tzinfo=ZoneInfo(zone))
    return dt.isoformat()


def structured_events(html, page_url, club):
    events, candidates = [], []
    for data in script_data(Document(html)):
        for original in event_nodes(data):
            item={'club_id':club['id'],'source_url':page_url,'extraction':'schema.org/Event','data':original}
            title=text_value(original.get('name'))
            if not title or not original.get('startDate'):
                candidates.append({**item,'status':'needs_review','reason':'missing_name_or_event_start'})
                continue
            if 'cancelled' in str(original.get('eventStatus','')).lower():
                candidates.append({**item,'status':'cancelled'})
                continue
            zone='America/Los_Angeles'
            try:
                start=date_value(original['startDate'],zone)
                all_day=len(original['startDate'])==10
                end=date_value(original.get('endDate') or (original['startDate'] if all_day else None),zone,end=True)
                if end and datetime.fromisoformat(end)<datetime.fromisoformat(start):
                    raise ValueError('end_before_start')
            except (ValueError,TypeError) as error:
                candidates.append({**item,'status':'needs_review','reason':str(error)})
                continue
            url=clean_url(original.get('url') or '',page_url) or page_url
            location=original.get('location',{})
            if isinstance(location,list):
                location=location[0] if location else {}
            address=location.get('address',{}) if isinstance(location,dict) else {}
            if isinstance(address,dict):
                address=', '.join(str(address.get(k) or '') for k in ('streetAddress','addressLocality','addressRegion','postalCode')).strip(', ')
            location_text=text_value(location)
            if address:
                location_text += (' — ' if location_text else '') + str(address)
            offer=original.get('offers',{})
            if isinstance(offer,list):
                offer=offer[0] if offer else {}
            price=offer.get('price') if isinstance(offer,dict) else None
            if original.get('isAccessibleForFree') is True:
                cost='FREE'
            else:
                cost=f'{offer.get("priceCurrency","")} {price}'.strip() if price is not None else ''
            keywords=original.get('keywords',[])
            keywords=keywords.split(',') if isinstance(keywords,str) else keywords
            image=original.get('image','')
            if isinstance(image,list):
                image=image[0] if image else ''
            if isinstance(image,dict):
                image=image.get('url','')
            image=clean_url(image,page_url) if isinstance(image,str) and image else None
            timestamp=now()
            record={
                'id':digest(club['id']+'|'+url+'|'+title+'|'+start), 'source':'club_website',
                'source_url':url, 'title':title,'description':text_value(original.get('description','')),
                'start_datetime':start,'end_datetime':end,'timezone':zone,'all_day':all_day,
                'location':location_text,'location_type':'virtual' if isinstance(location,dict) and location.get('@type')=='VirtualLocation' else 'physical' if location_text else 'tbd',
                'organizer_name':club['name'],'organizer_id':club['id'],'organizer_type':'club','organizer_url':club['website'],
                'categories':[text_value(original.get('eventType'))] if original.get('eventType') else [],
                'tags':[text_value(tag).strip() for tag in keywords if text_value(tag).strip()] if isinstance(keywords,list) else [],
                'audience':'students','image_url':image,'flyer_url':image,
                'rsvp_required':None,'rsvp_url':clean_url(offer.get('url',''),page_url) if isinstance(offer,dict) and offer.get('url') else url,
                'rsvp_deadline':None,'cost':cost,'first_seen':timestamp,'last_updated':timestamp,
                'raw_data':{'extraction':'schema.org/Event','collected_from':page_url,'event':original}}
            events.append(record)
    return events,candidates


def raw_record(page, club):
    html=page.get('text','')
    content_type=page.get('content_type','')
    doc=Document(html) if 'html' in content_type else None
    meta={}
    if doc:
        for node in doc.root.walk('meta'):
            key=node.attrs.get('property') or node.attrs.get('name')
            if key and node.attrs.get('content'):
                meta[key]=node.attrs['content']
    body=doc.root.text() if doc else html
    titles=list(doc.root.walk('title')) if doc else []
    status=page['status']
    if status=='ok' and len(body.strip())<60 and not meta.get('og:description'):
        status='needs_browser_rendering'
    return {'id':digest(club['id']+'|'+page['url']),'club_id':club['id'],'club_name':club['name'],
            'url':page['url'],'requested_url':page.get('requested_url',page['url']),
            'platform':platform(page['url']) or 'website','status':status,
            'http_status':page.get('http_status'),'error':page.get('error'),
            'title':titles[0].text() if titles else meta.get('og:title',''),
            'text':body,'description':meta.get('og:description') or meta.get('description',''),
            'published_at':meta.get('article:published_time'), 'fetched_at':page.get('fetched_at',now()),
            'content_type':content_type,'processing_status':'raw_text_only',
            'note':'Publication timestamps are not event dates. No OCR or caption date inference has been applied.'}


def collect(client, clubs, output_dir, max_clubs=None, pages_per_club=4, include_social=False, posts_per_profile=3):
    output=Path(output_dir)
    output.mkdir(parents=True,exist_ok=True)
    events,candidates,raws,report=[],[],[],[]
    processed=clubs[:max_clubs] if max_clubs is not None else clubs
    # Per-run checkpoints replace snapshots; blocked sites are always reported.
    seen_events=set()
    def checkpoint():
        write_json(output/'club_events.json',events)
        write_json(output/'club_event_candidates.json',candidates)
        write_json(output/'club_raw_text.json',raws)
        write_json(output/'club_event_crawl_report.json',{'updated_at':now(),'clubs_processed':len(report),'events':len(events),'raw_records':len(raws),'records':report})
    for club in processed:
        queue,social_queue,seen=deque([club['website']]),deque(),set()
        pages=club.get('pages',[])
        queue.extend(p['url'] for p in pages if p.get('status')=='ok')
        if include_social:
            for kind in ('instagram','linkedin','tiktok','discord'):
                social_queue.extend(item['url'] for item in club.get('social_links',{}).get(kind,[]) if item.get('account_scope') != 'individual')
        collected=0
        while (queue or social_queue) and collected<pages_per_club:
            url=queue.popleft() if queue else social_queue.popleft()
            if url in seen:
                continue
            seen.add(url)
            kind=platform(url)
            if kind and (not include_social or kind=='email'):
                continue
            page=client.fetch(url)
            if page['url'] != url and page['url'] in seen:
                continue
            seen.add(page['url'])
            raw=raw_record(page,club)
            raws.append(raw)
            collected+=1
            if page['status']!='ok':
                continue
            if 'html' in page.get('content_type',''):
                extracted,drafts=structured_events(page['text'],page['url'],club)
                for event in extracted:
                    if event['id'] not in seen_events:
                        seen_events.add(event['id'])
                        events.append(event)
                candidates.extend(drafts)
                if not kind:
                    queue.extend(sorted(relevant_pages(page['text'],page['url']), key=lambda url: not bool(re.search(r'event|calendar',url,re.I))))
                elif kind=='instagram':
                    # Only post links actually present in the fetched public profile.
                    posts=[link['url'] for link in Document(page['text']).links(page['url'])
                           if platform(link['url'])=='instagram' and re.match(r'^/(p|reel)/[^/]+',urlsplit(link['url']).path)]
                    social_queue.extend(dict.fromkeys(posts[:posts_per_profile]))
        pending=[url for url in dict.fromkeys([*queue,*social_queue]) if url not in seen and (not platform(url) or include_social)]
        report.append({'club_id':club['id'],'name':club['name'],'pages_collected':collected,
                       'pending_urls':pending,'page_limit_reached':bool(pending),
                       'social_collection_enabled':include_social})
        checkpoint()
    checkpoint()
    return events,raws


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources',type=Path,default=ROOT/'data/clubs/club_sources.json')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'data/output')
    parser.add_argument('--max-clubs',type=int)
    parser.add_argument('--pages-per-club',type=int,default=4)
    parser.add_argument('--include-social',action='store_true',help='Also attempt public social landing pages/posts; never logs in or joins servers')
    parser.add_argument('--posts-per-profile',type=int,default=3)
    parser.add_argument('--delay',type=float,default=2)
    args=parser.parse_args()
    if args.pages_per_club<1 or args.posts_per_profile<0 or args.max_clubs is not None and args.max_clubs<0:
        parser.error('Invalid crawl limit')
    clubs=json.loads(args.sources.read_text(encoding='utf-8'))
    events,raw=collect(PublicClient(delay=args.delay),clubs,args.output_dir,args.max_clubs,args.pages_per_club,args.include_social,args.posts_per_profile)
    print(f'Saved {len(events)} structured events and {len(raw)} raw records in {args.output_dir}')

if __name__=='__main__':
    main()
