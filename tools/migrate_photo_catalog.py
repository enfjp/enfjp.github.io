#!/usr/bin/env python3
"""One-time, non-destructive migration of the existing author-approved catalog."""
import json
from pathlib import Path
R=Path(__file__).resolve().parent.parent
p=R/'content/photography.json'
c=json.loads(p.read_text(encoding='utf-8'))
if c.get('schema_version',1)<2:
    names=[('yellowstone','Yellowstone National Park'),('yosemite','Yosemite National Park'),('grand-teton','Grand Teton National Park'),('piedras-blancas','Piedras Blancas Elephant Seal Rookery'),('carmel-by-the-sea','Carmel-by-the-Sea')]
    mapping={name:pid for pid,name in names}
    photos=[x for coll in c['collections'] for x in coll['photos']]
    if any(x.get('location') not in mapping for x in photos):
        raise ValueError('An unrecognized location needs author confirmation before migration.')
    for x in photos:
        x['location_id']=mapping[x['location']]
        x.setdefault('published',True)
        for v in x['variants']:
            path=(R/v['src']).resolve()
            if not path.is_relative_to(R/'assets/photos') or not path.is_file():
                raise ValueError('Missing or unsafe photo path.')
            v['size_bytes']=path.stat().st_size
    c['schema_version']=2
    c['places']=[{'id':pid,'name':name} for pid,name in names]
    p.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Migrated the existing catalog. Titles, locations, photographs and order are unchanged.')
else:
    print('Photo catalog already uses schema 2.')
