#!/usr/bin/env python3
"""Validate the owner editor and all public gallery outputs; standard library only."""
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
import unittest
from copy import deepcopy
import publish_gallery as g

class Document(HTMLParser):
    def __init__(self, text):
        super().__init__();self.refs=[];self.figures=[];self.ids=set();self.feed(text)
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if a.get('id'):self.ids.add(a['id'])
        for field in ('href','src'):
            if a.get(field):self.refs.append(a[field])
        for entry in a.get('srcset','').split(','):
            if entry.strip():self.refs.append(entry.strip().split()[0])
        if 'data-sg-work' in a:self.figures.append(a)

class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=json.loads((g.ROOT/'content/photography.json').read_text())
    @staticmethod
    def fixture():
        photo={'id':'test-photo','title':'Test photograph','alt':'A test subject.',
               'location_id':'test-place','location':'Test place','published':True,
               'width':1400,'height':900,'display':'landscape',
               'src':'assets/photos/test-1400.webp','full':'assets/photos/test-2048.webp',
               'variants':[{'src':'assets/photos/test-800.webp','width':800},
                           {'src':'assets/photos/test-1400.webp','width':1400},
                           {'src':'assets/photos/test-2048.webp','width':2048}]}
        return {'selected':['test-photo'],'places':[{'id':'test-place','name':'Test place'}],
                'collections':[{'slug':s,'name':s,'photos':[deepcopy(photo)] if s=='wild' else [],'cover':''}
                               for s in ('wild','land','on-the-road')]}
    def test_catalog(self):g.validate_catalog(self.catalog)
    def test_selected_can_be_subset(self):
        c=deepcopy(self.catalog);c['selected']=c['selected'][:2];g.validate_catalog(c)
    def test_unknown_selection_fails(self):
        c=deepcopy(self.catalog);c['selected'].append('nonexistent')
        with self.assertRaises(ValueError):g.validate_catalog(c)
    def test_all_hidden_and_empty_collections(self):
        c=deepcopy(self.catalog)
        for coll in c['collections']:
            for p in coll['photos']:p['published']=False
        g.validate_catalog(c)
        self.assertNotIn('<img ',g.homepage_teaser(c))
        c['selected']=[]
        for coll in c['collections']:coll['photos']=[];coll['cover']=''
        g.validate_catalog(c)
    def test_traversal_and_wrong_place_fail(self):
        for field,value in [('src','assets/photos/../../bad.webp'),('location_id','missing')]:
            c=self.fixture();c['collections'][0]['photos'][0][field]=value
            with self.assertRaises(ValueError):g.validate_catalog(c,check_files=False)
    def test_html_escape(self):
        c=self.fixture();p=c['collections'][0]['photos'][0];p['title']='<script>alert(1)</script>';p['location']='A & B'
        markup=g.figure(p,c['collections'][0],'photography/index.html')
        self.assertNotIn('<script>',markup);self.assertIn('&lt;script&gt;',markup);self.assertIn('A &amp; B',markup)
    def test_distinct_paths(self):
        fixture=self.fixture();c=fixture['collections'][0];place=fixture['places'][0]
        self.assertEqual(g.browse_path(c,place,1),f'photography/{c["slug"]}/{place["id"]}/page/2/index.html')
    def test_generated_membership(self):
        lookup=g.validate_catalog(self.catalog)
        def actual(path):
            return [x['data-title'] for x in Document((g.OUT/path).read_text()).figures]
        def compare_group(expected,coll=None,place=None):
            count=max(1,(len(expected)+g.PAGE_SIZE-1)//g.PAGE_SIZE)
            result=[]
            for i in range(count):result.extend(actual(g.browse_path(coll,place,i)))
            self.assertEqual(result,expected)
        compare_group([lookup[i][0]['title'] for i in self.catalog['selected'] if lookup[i][0].get('published',True)])
        for c in self.catalog['collections']:
            expected=[p['title'] for p in c['photos'] if p.get('published',True)]
            compare_group(expected,c)
            for place in self.catalog['places']:
                p=[p['title'] for p in c['photos'] if p.get('published',True) and p['location_id']==place['id']]
                if p:compare_group(p,c,place)
        public=json.loads((g.OUT/'photography/catalog-public.json').read_text())
        expected=hashlib.sha256((g.ROOT/'content/photography.json').read_bytes()).hexdigest()
        self.assertEqual(public['catalog_sha256'],expected)
    def test_all_local_references(self):
        count=0
        for page in g.OUT.rglob('*.html'):
            doc=Document(page.read_text())
            for ref in doc.refs:
                u=urlsplit(ref)
                if u.scheme or u.netloc:continue
                dest=g.OUT/unquote(u.path).lstrip('/') if u.path.startswith('/') else page.parent/unquote(u.path)
                if not u.path:dest=page
                if dest.is_dir():dest=dest/'index.html'
                self.assertTrue(dest.exists(),f'{page}: broken {ref}')
                if u.fragment and dest.suffix=='.html':self.assertIn(unquote(u.fragment),Document(dest.read_text()).ids,f'{page}: missing {ref}')
                count+=1
        print(f'Checked {count} local links and image references.')
    def test_admin_secret_hygiene(self):
        js=(g.ROOT/'admin/admin.js').read_text();html=(g.ROOT/'admin/index.html').read_text()
        for disallowed in ('localStorage','sessionStorage','document.cookie','console.log'):
            self.assertNotIn(disallowed,js)
        self.assertIn('Content-Security-Policy',html)
        self.assertIn("redirect:'error'",js);self.assertIn('force:false',js)
        self.assertNotIn('force:true',js)
        self.assertIn('noindex,nofollow',html)
        self.assertNotRegex(js+html,r'github_pat_[A-Za-z0-9_]{20,}')
    def test_no_binary_changes(self):
        active=[p for p,_ in g.validate_catalog(self.catalog).values() if p.get('published',True)]
        for p in active:
            for path in g.photo_paths(p):
                self.assertEqual(hashlib.sha256((g.ROOT/path).read_bytes()).digest(),hashlib.sha256((g.OUT/path).read_bytes()).digest())

if __name__=='__main__':unittest.main(verbosity=2)
