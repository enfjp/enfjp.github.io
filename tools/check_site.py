#!/usr/bin/env python3
"""Check generated HTML, local assets, fragments, and essential metadata. No network calls."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import json
import sys

ROOT = Path(__file__).resolve().parent.parent / 'docs'

class Document(HTMLParser):
    def __init__(self):
        super().__init__(); self.refs=[]; self.ids=set(); self.errors=[]; self.h1=0; self.title=False; self.description=False; self.lang=False
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='html': self.lang=bool(a.get('lang'))
        if tag=='title': self.title=True
        if tag=='h1': self.h1+=1
        if tag=='meta' and a.get('name')=='description': self.description=bool(a.get('content'))
        if 'id' in a:
            if a['id'] in self.ids: self.errors.append('Duplicate id: '+a['id'])
            self.ids.add(a['id'])
        if tag=='img' and 'alt' not in a: self.errors.append('Image without alt attribute')
        for key in ('href','src'):
            if a.get(key): self.refs.append(a[key])
        if a.get('srcset'):
            self.refs.extend(item.strip().split()[0] for item in a['srcset'].split(','))
        if tag=='a' and a.get('target')=='_blank' and 'noopener' not in a.get('rel',''):
            self.errors.append('External new-tab link without noopener')


def main():
    parsed={}
    for path in ROOT.rglob('*.html'):
        doc=Document();doc.feed(path.read_text(encoding='utf-8'));parsed[path.resolve()]=doc
    errors=[];references=0
    for path,doc in parsed.items():
        name=path.relative_to(ROOT)
        for error in doc.errors: errors.append(f'{name}: {error}')
        if doc.h1!=1: errors.append(f'{name}: expected one h1, got {doc.h1}')
        if not(doc.title and doc.description and doc.lang): errors.append(f'{name}: missing essential metadata')
        for ref in doc.refs:
            parts=urlsplit(ref)
            if parts.scheme or parts.netloc: continue
            references+=1
            if not parts.path: target=path
            elif parts.path.startswith('/'):target=(ROOT/unquote(parts.path).lstrip('/')).resolve()
            else:target=(path.parent/unquote(parts.path)).resolve()
            if not target.is_relative_to(ROOT.resolve()):
                errors.append(f'{name}: reference escapes output directory: {ref}');continue
            if target.is_dir(): target=target/'index.html'
            if not target.is_file(): errors.append(f'{name}: missing local target: {ref}');continue
            if parts.fragment and target.suffix=='.html' and unquote(parts.fragment) not in parsed[target].ids:
                errors.append(f'{name}: missing fragment: {ref}')
    if not parsed: errors.append('No HTML pages found. Run tools/build.py first.')
    result={'pages':len(parsed),'local_references_checked':references,'errors':errors,'result':'PASS' if not errors else 'FAIL'}
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 1 if errors else 0

if __name__=='__main__':sys.exit(main())
