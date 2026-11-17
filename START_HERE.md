# Start here

This folder contains the full ZotLife website, upgraded UCI crawler, saved data,
and `.git` history. Keep the hidden `.git` folder when moving the project.
You do not need a GitHub account. Nothing was pushed or published.

## Open the website

In Terminal, change into this extracted `ai_innovation` folder, then run:

```sh
python3 -m http.server 8765 --bind 127.0.0.1
```

Open http://127.0.0.1:8765/. See `README.md` for website details.

## Updated crawler

Code and all crawler data: `tools/zot_event_crawl/`.
Read `tools/zot_event_crawl/README.md` for discovery, event collection and publishing.

Main result files:

- Club websites/contact links: `tools/zot_event_crawl/data/clubs/club_sources.json`
- Collected text/statuses: `tools/zot_event_crawl/data/output/club_raw_text.json`
- Parsed events: `tools/zot_event_crawl/data/output/club_events.json`
- Crawl report: `tools/zot_event_crawl/data/output/club_event_crawl_report.json`

The bounded live test discovered 1,000 directory groups but enriched only three;
997 remain unprocessed. It saved website text and contact links. Social requests
were blocked, and no additional structured events were found in the sample.
The parsed events file is therefore empty; raw text is available for later parsing.

## Local Git

Current branch: `feature/uci-event-feed`.

```sh
git status
git log --oneline
```

The `origin` URL still records the source repository, MaghyC/ai_innovation.
You can use local commits without connecting to it. Generated crawler output is
ignored by Git but included in this complete ZIP alongside the source and history.
