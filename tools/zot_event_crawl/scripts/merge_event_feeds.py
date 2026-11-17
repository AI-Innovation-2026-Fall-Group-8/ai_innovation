#!/usr/bin/env python3
"""Merge reviewed unified feeds, preserving distinct source IDs. Stdlib only."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/crawlers'))
from club_sources import write_json

def merge(feeds):
    result={}
    for feed in feeds:
        if not isinstance(feed,list):
            raise ValueError('Each input must be a JSON event array')
        for event in feed:
            if not isinstance(event,dict) or not all(event.get(key) for key in ('id','source','title')):
                raise ValueError('Every event needs id, source and title; do not merge raw text/candidates')
            result[(event['source'],str(event['id']))]=event
    return list(result.values())

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs',type=Path,nargs='+',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.resolve() in [path.resolve() for path in args.inputs]:
        parser.error('Output must differ from inputs so original snapshots are preserved')
    feeds=[json.loads(path.read_text(encoding='utf-8')) for path in args.inputs]
    result=merge(feeds)
    write_json(args.output,result)
    print(f'Saved {len(result)} events to {args.output}')

if __name__=='__main__':
    main()
