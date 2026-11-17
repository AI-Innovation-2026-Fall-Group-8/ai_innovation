# ZotLife — UCI events from your crawler

The website loads `data/output/unified_events.json` over HTTP on page load.
Events are not embedded in HTML. Your crawler remains a separate collection tool;
its original folder has not been changed. The included feed contains 295 events
from your supplied snapshot, whose records were updated on November 10, 2026.

## Run locally

From this repository directory:

```sh
python3 -m http.server 8765 --bind 127.0.0.1
```

Open http://127.0.0.1:8765/ in a browser. The root page opens the original prototype
filename. Double-clicking the HTML file uses `file://`, which cannot reliably fetch
JSON; the page explains that a web server is needed.

## Refresh after a crawl

1. Run your existing crawler/pipeline to produce its unified output. This website
   does not run crawlers in visitors' browsers or schedule collection jobs.
2. From this repository directory, export the new snapshot:

   ```sh
   python3 scripts/sync_events.py "/Users/zhaohuilinAnne/Downloads/zot_event_crawl-main/data/output/unified_events.json"
   ```

   The command writes the website's `data/output/unified_events.json`. It can also
   read any other path with the same unified schema. Do not substitute raw
   `events.json`, which uses a different schema.
3. Refresh the local browser. No HTML edits or build step are required.
4. Review and commit the updated public feed:

   ```sh
   git diff --stat
   git add data/output/unified_events.json
   git commit -m "Refresh UCI event snapshot"
   ```

   Deploy the new commit through your normal hosting process. A local file change
   alone does not change an already hosted website. Uploading only the HTML also
   does not update the feed.

The exporter keeps a defined set of event fields, strips markup from display text,
removes raw crawler payloads, deduplicates by `(source, id)`, and rejects invalid
dates before replacing the feed atomically. It reconstructs missing end times from
the supplied crawler's raw date text when available and adds timezone offsets.
This avoids marking a multi-day event as past based only on its start date.
Records from different sources are kept distinct; cross-source duplicate matching
belongs in your collection pipeline. Separate recurring occurrences need distinct IDs.

The public feed is approximately 260 KB versus 1.6 MB for the supplied unified
crawler output. Only the public export should be deployed; keep crawler auth,
cookies, debug files and raw collection data outside the website directory.

## What the website does

- Starts with UCI events, showing upcoming and ongoing events in Pacific Time.
- Offers All dates, Past events, and Dates unconfirmed views.
- Searches titles, descriptions, organizers, locations and topic tags.
- Opens RSVP or official event links in a new tab.
- Shows the latest record update date, separately from loading the page.
- Has loading, empty, error, timeout and retry states.
- Keeps the prototype's other sample listings behind an unchecked demo option.
- Displays imported text as text and rejects unsafe action-link protocols.

A record without an end time is considered past after its start time. Unknown
dates appear under All dates or Dates unconfirmed. The saved snapshot may contain
outdated details or broad recurring-event date ranges; follow the official link
for the specific session schedule. Loading JSON does not itself verify freshness.
A page refresh revalidates the published feed; it does not perform a fresh crawl.

The Clubs filter uses the crawler's `organizer_type`; source categorization errors
will carry into this filter until corrected in the pipeline. Other resource
categories contain demo listings until you supply real resource data.

## Why this architecture

```text
ZotSpot / future club websites / other future sources
                         ↓
           Your crawler and source adapters
                         ↓
         Private unified_events.json snapshot
                         ↓  scripts/sync_events.py
       Website data/output/unified_events.json
                         ↓  HTTP fetch on page load
                 ZotLife event cards
```

For this amount of data, a static JSON feed is simpler to operate than a database
and API. Keeping collection out of the frontend means adding a new source does not
require a different page layout. Next, automate the crawl/export/deployment process
when the collection tools are stable. Consider a backend when you need shared user
accounts, saved events across devices, submissions, or a much larger searchable feed.

For a future club-site or Instagram adapter, export the same event schema. Prefer
an official event feed, calendar or approved API where available. Handling source
access, refresh failures and duplicate detection belongs to the crawler project;
none of those adapters have been added in this change.

### Unified source record

```json
{
  "id": "club-talk-2026-11-20",
  "source": "club-site",
  "source_url": "https://example.org/events/talk",
  "title": "Club speaker night",
  "description": "Meet the speakers and ask questions.",
  "start_datetime": "2026-11-20T18:00:00",
  "end_datetime": "2026-11-20T20:00:00",
  "timezone": "America/Los_Angeles",
  "location": "Student Center",
  "organizer_name": "Example Club",
  "organizer_type": "club",
  "categories": ["Professional"],
  "tags": ["Networking"],
  "rsvp_url": "https://example.org/events/talk",
  "cost": "FREE",
  "last_updated": "2026-11-16T12:00:00-08:00"
}
```

`id` and `title` are required. A source adapter should supply an official link,
source name, timezone and update timestamp. Unknown dates can be null. The exporter
converts local timestamps to timestamps with offsets; run it before publishing.
A new source's cards automatically use “View official event” rather than ZotSpot.
The website does not load multiple overlapping crawler output and test files.

## Verification

Python 3.9+ with timezone data and Node.js 18+ for the JavaScript checks:

```sh
python3 -m unittest discover -s tests -v
node tests/test_app.cjs
```

Python tests cover daylight saving offsets, recovered end dates, discarded raw
payloads, deduplication, invalid records and unsafe links. JavaScript checks cover
the actual feed, filters, ongoing events, search, optional demos, safe rendering,
unknown dates, malformed JSON, HTTP failures, retry and local-file guidance.
Browser checks verified the root entry, real feed, no-results view and clearing
filters. No deployment or GitHub push was performed.

## Git workflow used

Work is on `feature/uci-event-feed`, based on upstream commit `c0187b6`.

1. Export and test the public feed.
2. Connect the frontend and verify behavior.
3. Document refresh/deployment and complete validation.

Inspect the work with `git log --oneline -3` and
`git diff c0187b6..HEAD --stat`. All work is local; publish the reviewed branch
through your normal GitHub process.
