#!/usr/bin/env python3
"""Check gallery locations and image references against the authored catalog."""
from html.parser import HTMLParser
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent.parent

class GalleryParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.works = []
        self.current = None
        self.in_location = False
        self.viewer_locations = 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'figure' and 'data-sg-work' in a:
            self.current = {'title':a.get('data-title'), 'location':a.get('data-location', ''), 'caption':'', 'full':''}
        if a.get('id') == 'sg-viewer-location':
            self.viewer_locations += 1
        if self.current is not None:
            if tag == 'a' and 'sg-photo-link' in a.get('class', '').split():
                self.current['full'] = a['href']
            if tag == 'span' and 'sg-location' in a.get('class', '').split():
                self.in_location = True
    def handle_data(self, text):
        if self.in_location and self.current is not None:
            self.current['caption'] += text
    def handle_endtag(self, tag):
        if tag == 'span':
            self.in_location = False
        if tag == 'figure' and self.current is not None:
            self.works.append(self.current)
            self.current = None

def main():
    catalog = json.loads((ROOT/'content/photography.json').read_text(encoding='utf-8'))
    photos = {p['id']:p for c in catalog['collections'] for p in c['photos']}
    pages = [('photography/index.html', [photos[i] for i in catalog['selected']])]
    pages += [(f'photography/{c["slug"]}/index.html', c['photos']) for c in catalog['collections']]
    checked = 0
    for path, expected in pages:
        page = ROOT/'docs'/path
        parsed = GalleryParser()
        parsed.feed(page.read_text(encoding='utf-8'))
        if len(parsed.works) != len(expected) or parsed.viewer_locations != 1:
            raise ValueError(f'{path}: unexpected photograph or viewer count')
        for actual, photo in zip(parsed.works, expected):
            location = photo.get('location', '')
            if actual['title'] != photo['title'] or actual['location'] != location or actual['caption'] != location:
                raise ValueError(f'{path}: location mismatch for {photo["id"]}')
            if (page.parent/actual['full']).resolve() != (ROOT/'docs'/photo['full']).resolve():
                raise ValueError(f'{path}: changed image reference for {photo["id"]}')
            checked += 1
    print(json.dumps({'result':'PASS', 'gallery_pages':len(pages), 'photo_location_occurrences':checked}))

if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError) as error:
        print(f'Location checks failed: {error}', file=sys.stderr)
        sys.exit(1)
