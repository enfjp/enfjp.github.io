#!/usr/bin/env python3
"""Build the static website using Python 3.9+ and the standard library only.

Run from any directory: python3 tools/build.py
Content is authored in content/*.json. The generated docs/ directory is public.
"""
from __future__ import annotations
import argparse
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlsplit
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'docs'
ASSETS = ROOT / 'assets'
PAGE = 'index.html'
SITE = {}
RESEARCH = []
PHOTO = {}


def esc(value):
    return html.escape(str(value), quote=True)


def rel(target):
    if target.startswith(('#', 'https://', 'mailto:')):
        return target
    if PAGE == '404.html':
        return '/' + target.lstrip('/')
    path, mark, fragment = target.partition('#')
    result = os.path.relpath(path, str(Path(PAGE).parent)).replace(os.sep, '/')
    return result + (mark + fragment if mark else '')


def link(target, label, css='text-link', external=False):
    attrs = ' target="_blank" rel="noopener noreferrer"' if external else ''
    return f'<a class="{esc(css)}" href="{esc(rel(target))}"{attrs}>{label}</a>'


def arrow(symbol='↗'):
    return f'<span class="arrow" aria-hidden="true">{symbol}</span>'


def label(text, classes=''):
    return f'<p class="label {esc(classes)}">{esc(text)}</p>'


def external_links(include_cv=True):
    items = []
    for key, text in [('email', 'Email'), ('scholar', 'Scholar'), ('github', 'GitHub'), ('cv', 'CV')]:
        value = SITE.get(key)
        if not value or (key == 'cv' and not include_cv):
            continue
        url = 'mailto:' + value if key == 'email' else value
        items.append(link(url, f'{text} {arrow()}', external=key in ('github', 'scholar')))
    return ''.join(items)


def navigation(active=''):
    items = [('research', 'Research', 'research/index.html'), ('photography', 'Photography', 'photography/index.html'), ('about', 'About', 'about/index.html')]
    def anchors():
        return ''.join(f'<a href="{esc(rel(url))}"' + (' aria-current="page"' if key == active else '') + f'>{text}</a>' for key, text, url in items)
    cv = link(SITE['cv'], 'CV ↗', css='nav-contact') if SITE.get('cv') else ''
    return f'''<div class="wrap"><header class="site-header">
      <a class="brand" href="{esc(rel('index.html'))}" aria-label="{esc(SITE['name'])}, home"><span class="brand-name">JIPENG LI</span><span class="brand-cn" lang="zh-CN">{esc(SITE['preferred_name'])}</span></a>
      <nav class="desktop-nav" aria-label="Main navigation">{anchors()}{cv}</nav>
      <button type="button" class="menu-toggle" data-menu-button aria-expanded="false" aria-controls="mobile-navigation"><span data-menu-word>Menu</span><span class="menu-icon" aria-hidden="true">≡</span></button>
      </header><nav id="mobile-navigation" class="mobile-nav" aria-label="Mobile navigation" data-mobile-menu hidden>{anchors()}{cv}</nav></div>'''


def footer():
    return f'''<footer class="site-footer wrap"><div><p class="footer-name">JIPENG LI <span class="muted">/ Research &amp; Photography</span></p><p class="footer-small">© {SITE['updated'][:4]} Jipeng Li · {esc(SITE['location'])}</p></div>
    <nav class="footer-links" aria-label="Footer">{link('about/index.html#contact','Contact',css='')}{link('privacy/index.html','Privacy',css='')}{link('#top','Back to top ↑',css='')}</nav></footer>'''


def wrapper(path, title, description, content_fn, active='', dark=False, schema=None):
    global PAGE
    PAGE = path
    content = content_fn()
    canonical_path = '' if path == 'index.html' else path.removesuffix('index.html')
    canonical = SITE['site_url'].rstrip('/') + '/' + canonical_path
    structured = schema or {'@context': 'https://schema.org', '@type': 'WebPage', 'name': title, 'url': canonical, 'description': description}
    if path == 'index.html':
        structured = {'@context': 'https://schema.org', '@type': 'ProfilePage', 'url': canonical, 'mainEntity': {'@type': 'Person', 'name': SITE['name'], 'description': SITE['description'], 'sameAs': [v for v in (SITE.get('github'), SITE.get('scholar')) if v]}}
    if path == '404.html':
        canonical_tag = ''
        robots = 'noindex, nofollow'
    else:
        canonical_tag = f'<link rel="canonical" href="{esc(canonical)}">'
        robots = 'noindex, nofollow' if SITE['preview'] else 'index, follow'
    ribbon = '<div class="wrap"><p class="preview-ribbon"><span class="preview-dot" aria-hidden="true"></span>DESIGN PREVIEW · PHOTOGRAPHS &amp; CONTACT DETAILS TO BE ADDED</p></div>' if SITE['preview'] else ''
    code = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(description)}"><meta name="robots" content="{robots}">
<meta name="theme-color" content="{'#131917' if dark else '#f5f3ed'}">{canonical_tag}
<meta property="og:type" content="website"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(canonical)}"><meta property="og:site_name" content="Jipeng Li">
<meta name="twitter:card" content="summary"><link rel="icon" type="image/svg+xml" href="{esc(rel('assets/favicon.svg'))}"><link rel="stylesheet" href="{esc(rel('assets/style.css'))}">
<script type="application/ld+json">{json.dumps(structured, ensure_ascii=False).replace('<', '\\u003c')}</script>
<script src="{esc(rel('assets/site.js'))}" defer></script></head>
<body id="top" class="{'dark' if dark else 'light'}"><a class="skip-link" href="#main">Skip to content</a>{navigation(active)}{ribbon}
<main id="main">{content}</main>{footer()}</body></html>'''
    dest = OUT / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(code, encoding='utf-8')


def placeholder(number='01', tone=1, caption='Your photograph, not a stock image'):
    return f'<div class="placeholder tone-{tone}"><span class="slot-index" aria-hidden="true">{esc(number)}</span><span class="slot-title">Photograph to be added</span><span class="slot-caption">{esc(caption)}</span></div>'


def image_tag(photo, cover=False):
    source = photo['src']
    attrs = ''
    if photo.get('width') and photo.get('height'):
        attrs += f' width="{int(photo["width"])}" height="{int(photo["height"])}"'
    variants = photo.get('variants', [])
    if variants:
        srcset = ', '.join(f'{rel(v["src"])} {int(v["width"])}w' for v in variants)
        attrs += f' srcset="{esc(srcset)}" sizes="(max-width: 720px) 90vw, 42vw"'
    return f'<img src="{esc(rel(source))}" alt="{esc(photo["alt"])}" loading="lazy" decoding="async"{attrs}>'


def cards():
    result = []
    for i, coll in enumerate(PHOTO['collections']):
        photos = coll['photos']
        if not SITE['preview'] and not photos:
            continue
        cover = next((p for p in photos if p['src'] == coll.get('cover')), photos[0] if photos else None)
        visual = image_tag(cover, True) if cover else placeholder(coll['number'], i % 3 + 1)
        result.append(f'''<a class="collection-card" href="{esc(rel('photography/' + coll['slug'] + '/index.html'))}">
        <div class="collection-cover">{visual}</div><div class="collection-info"><div><p class="collection-volume">COLLECTION {esc(coll['number'])}</p><h3>{esc(coll['name'])}</h3><p class="collection-subtitle">{esc(coll['subtitle'])}</p></div>{arrow()}</div></a>''')
    return '<div class="collection-grid">' + ''.join(result) + '</div>'


def work_row(work, index=1):
    project = 'research/' + work['slug'] + '/index.html'
    paper_links = link(work['paper'], 'Paper ' + arrow(), external=True)
    if work.get('code'):
        paper_links += link(work['code'], 'Code ' + arrow(), external=True)
    return f'''<article class="work-row"><span class="work-number">{index:02}</span><div class="work-main"><h3>{link(project, esc(work['short_title']), css='')}</h3><p>{esc(work['summary'])}</p><div class="text-links">{paper_links}{link(project + '#citation','BibTeX ' + arrow('↘'))}</div></div><div class="work-meta"><span class="badge">{esc(work['venue'])}</span>{link(project,'Read project ' + arrow('→'))}</div></article>'''


def home():
    return f'''<div class="wrap"><section class="hero" aria-labelledby="home-title"><div class="hero-top">{label('RESEARCHER / PHOTOGRAPHER')}{label('PERSONAL INDEX — 2026', 'edition')}</div><h1 id="home-title">Jipeng Li<span class="period">.</span></h1><div class="hero-lower"><p class="hero-subtitle">Thinking in models.<br><span class="serif">Looking beyond them.</span></p><div class="intro-block"><p>{esc(SITE['research_intro'])}</p><div class="text-links">{link('research/index.html','Explore research ' + arrow('→'))}{link('photography/index.html','View photographs ' + arrow('→'))}</div></div></div><div class="hero-bottom">{label(SITE['role'])}{label(SITE['location'])}<a href="#selected-research" aria-label="Scroll to selected research">↓</a></div></section>
    <section class="section rule" id="selected-research"><div class="section-heading"><div>{label('01 / INQUIRY')}<h2>Selected research</h2></div>{link('research/index.html','Research index ' + arrow('→'))}</div>{''.join(work_row(w, i+1) for i,w in enumerate(RESEARCH[:3]))}<p class="section-note">A selection of published work. Full paper details, links, and citations are available on the research page.</p></section></div>
    <section class="photo-teaser" id="photography"><div class="wrap"><div class="section-heading"><div>{label('02 / OBSERVATION')}<h2>A life outside<br>the frame.</h2></div>{link('photography/index.html','Enter gallery ' + arrow('→'))}</div>{cards()}<div class="photo-teaser-bottom"><p>Landscapes, wildlife, and places along the way.</p><p>{'Layout preview. All image spaces await original photographs.' if SITE['preview'] else 'Photographs by Jipeng Li.'}</p></div></div></section>
    <div class="wrap"><section class="section about-strip"><div>{label('03 / THE PERSON', 'muted')}<h2 style="margin-top:20px">Research is one<br>part of the story.</h2></div><div><p>I am a Ph.D. student at UC Irvine. Away from my desk, I spend time with a camera — looking at the world from a different distance.</p><div class="text-links">{link('about/index.html','A little about me ' + arrow('→'))}{external_links(False)}</div></div></section></div>'''


def research():
    rows = ''.join(work_row(w,i+1) for i,w in enumerate(RESEARCH))
    publications = ''.join(f'''<article class="publication-line">{label(w['year'], 'muted')}<div><h3>{esc(w['title'])}</h3><p>{esc(w['authors'])} · {esc(w['venue'])}</p><div class="text-links">{link(w['paper'],'Paper '+arrow(),external=True)}{link(w['proceedings'],'Proceedings '+arrow(),external=True)}{link('research/'+w['slug']+'/index.html#citation','BibTeX '+arrow('↘'))}</div></div></article>''' for w in RESEARCH)
    return f'''<div class="wrap"><section class="page-hero">{label('01 / RESEARCH')}<h1>What information<br><span class="serif">is enough?</span></h1><p class="deck">{esc(SITE['research_intro'])}</p></section><section class="section rule" style="padding-top:42px"><div class="section-heading"><div>{label('PUBLISHED WORK')}<h2>Selected projects</h2></div><a class="text-link" href="#publications">Publications {arrow('↓')}</a></div>{rows}</section><section class="section rule"><div class="section-heading"><div>{label('CURRENT INTERESTS')}<h2>Questions I work on</h2></div></div><div class="focus-grid"><div>{label('01', 'muted')}<h3>Learned representations</h3><p>What information does a representation retain, and is that information useful for the decisions made from it?</p></div><div>{label('02', 'muted')}<h3>Generative models</h3><p>Which inputs and components do generative models need, and which assumptions can be tested rather than taken for granted?</p></div><div>{label('03', 'muted')}<h3>Model behavior</h3><p>What can controlled changes tell us about how a model reaches an answer, and when does an observed effect transfer?</p></div></div></section><section class="section rule" id="publications"><div class="section-heading"><div>{label('BIBLIOGRAPHIC RECORD')}<h2>Publications</h2></div></div>{publications}</section></div>'''


def project(work):
    sections = ''.join(f'<section class="article-section" id="{key}"><h2>{text}</h2><p>{esc(work[key])}</p></section>' for key,text in [('problem','The question'),('approach','The approach'),('finding','What we found')])
    return f'''<div class="wrap"><div class="back-link">{link('research/index.html','← Research index',css='')}</div><header class="article-hero">{label(work['venue'] + ' / ' + ' · '.join(work['tags']))}<h1>{esc(work['title'])}</h1><p class="authors">{esc(work['authors'])}</p><div class="text-links">{link(work['paper'],'Read the paper '+arrow(),external=True)}{link(work['proceedings'],'Conference proceedings '+arrow(),external=True)}{link('#citation','BibTeX '+arrow('↓'))}</div></header><div class="article-layout rule"><aside class="article-aside" aria-label="On this page">{label('ON THIS PAGE')}{link('#problem','01 — The question',css='')}{link('#approach','02 — The approach',css='')}{link('#finding','03 — What we found',css='')}{link('#citation','04 — Citation',css='')}</aside><div class="article-content"><div class="research-question">{label('IN ONE QUESTION')}<p>{esc(work['question'])}</p></div>{sections}<section class="article-section" id="citation"><h2>Cite this work</h2><div class="bibtex-wrap"><div class="bibtex-top">{label('BIBTEX')}<button class="copy-button" type="button" data-copy-bibtex="bibtex">Copy citation</button></div><pre id="bibtex">{esc(work['bibtex'])}</pre><p class="copy-status" data-copy-status role="status" aria-live="polite"></p></div></section></div></div></div>'''


def photo_grid(items):
    contents = []
    for coll, p in items:
        detail = ' · '.join(str(x) for x in [p.get('location'), p.get('year')] if x)
        contents.append(f'''<figure class="photo-item" data-photo-item data-collection="{esc(coll['slug'])}"><a class="photo-open" href="{esc(rel(p.get('full',p['src'])))}" data-photo-open data-title="{esc(p['title'])}" data-alt="{esc(p['alt'])}" data-detail="{esc(detail)}" aria-label="Open photograph: {esc(p['title'])}">{image_tag(p)}</a><figcaption class="photo-caption"><span>{esc(p['title'])}</span><span>{esc(detail)}</span></figcaption></figure>''')
    return '<div class="gallery-grid">'+''.join(contents)+'</div>'


def lightbox():
    return '''<dialog class="lightbox" data-lightbox aria-label="Photograph viewer"><div class="lightbox-inner"><div class="lightbox-top"><p class="label" data-lb-count></p><button class="lb-close" type="button" data-lb-close aria-label="Close photograph viewer" autofocus>Close ×</button></div><div class="lightbox-stage"><button class="lb-nav prev" type="button" data-lb-step="-1" aria-label="Previous photograph">←</button><img data-lb-image alt=""><p class="lightbox-error" data-lb-error hidden>Unable to load this photograph. Close the viewer and try again.</p><button class="lb-nav next" type="button" data-lb-step="1" aria-label="Next photograph">→</button></div><div class="lightbox-caption"><p data-lb-title></p><small data-lb-detail></small><small>← → to browse · Esc to close</small></div></div></dialog>'''


def photography():
    items = [(coll,p) for coll in PHOTO['collections'] for p in coll['photos']]
    if items:
        filters = '<div class="gallery-filters" aria-label="Filter photographs"><button type="button" class="filter-button" data-filter="all" aria-pressed="true">All</button>' + ''.join(f'<button type="button" class="filter-button" data-filter="{esc(c["slug"])}" aria-pressed="false">{esc(c["name"])}</button>' for c in PHOTO['collections'] if c['photos']) + '</div>'
        all_photos = filters + photo_grid(items)
    else:
        all_photos = '<div class="empty-state">'+label('ORIGINAL WORK ONLY')+'<h2>The photographs come next.</h2><p>No stock photographs or other photographers’ work have been included. Original images will be added after selection. The collection pages show the intended layout.</p></div>'
    return f'''<div class="wrap gallery-page"><section class="page-hero">{label('02 / PHOTOGRAPHY')}<div class="page-hero-bottom"><div><h1>{esc(PHOTO['title'])}</h1><p class="deck">{esc(PHOTO['intro'])}</p></div>{label('SELECTED PHOTOGRAPHS', 'muted')}</div></section><div class="gallery-toolbar"><div class="view-switch" role="tablist" aria-label="Gallery view"><button type="button" id="tab-collections" data-gallery-tab role="tab" aria-controls="collections-panel" aria-selected="true">Collections</button><button type="button" id="tab-all" data-gallery-tab role="tab" aria-controls="all-panel" aria-selected="false" tabindex="-1">All photographs</button></div>{label(f'{len(PHOTO["collections"]):02} COLLECTIONS / {len(items):02} PHOTOGRAPHS', 'muted')}</div><section class="gallery-panel" id="collections-panel" data-gallery-panel role="tabpanel" aria-labelledby="tab-collections">{cards()}</section><section class="gallery-panel" id="all-panel" data-gallery-panel role="tabpanel" aria-labelledby="tab-all" hidden>{all_photos}</section><noscript><p class="no-js-note">Open a collection to view its photographs. Enable JavaScript for filters and the full-screen viewer.</p></noscript></div>{lightbox()}'''


def collection(coll,index):
    photos = coll['photos']
    next_coll = PHOTO['collections'][(index+1) % len(PHOTO['collections'])]
    if photos:
        gallery = photo_grid([(coll,p) for p in photos])
    elif SITE['preview']:
        gallery = f'''<div class="empty-gallery"><div>{placeholder('01',index%3+1)}</div><div>{placeholder('02',(index+1)%3+1)}</div></div><div class="gallery-intro"><p>This is a layout preview, not a published photo essay. Add your photographs and replace the collection introduction with your own words before launch.</p></div>'''
    else:
        gallery = '<div class="empty-state"><h2>Photographs are being selected.</h2><p>This collection will be published when the selection is ready.</p></div>'
    return f'''<div class="wrap"><div class="back-link">{link('photography/index.html','← All collections',css='')}</div><header class="collection-header"><div class="title-block">{label('COLLECTION '+coll['number'])}<h1>{esc(coll['name'])}</h1><p>{esc(coll['subtitle'])}</p></div><div><p>{esc(coll['description'])}</p></div></header>{gallery}<div class="next-collection"><div>{label('NEXT COLLECTION','muted')}<h2>{esc(next_coll['name'])}</h2></div>{link('photography/'+next_coll['slug']+'/index.html','Explore '+arrow('→'))}</div></div>{lightbox()}'''


def about():
    bio = ''.join(f'<p>{esc(p)}</p>' for p in SITE['bio'])
    education = ''.join(f'<div class="education-row"><div><h3>{esc(x["school"])}</h3><p>{esc(x["degree"])}</p></div>{label(x["period"],"muted")}</div>' for x in SITE['education'])
    contact_note = 'For research correspondence, use the email link below.' if SITE.get('email') else 'Find my public work on GitHub. A direct email link will be added before the final launch.'
    return f'''<div class="wrap"><header class="page-hero">{label('03 / ABOUT')}<h1>Behind the work.</h1></header><div class="about-layout"><div><div class="portrait-panel" aria-label="Typographic monogram, not a portrait"><span class="monogram" aria-hidden="true">JL</span>{label('JIPENG LI / 冀鹏')}</div><p class="section-note">{esc(SITE['location'])}<br>Research &amp; photography</p></div><div class="about-copy">{bio}<section class="education"><h2>Education</h2>{education}</section><section class="contact-box" id="contact"><h2>Get in touch.</h2><p>{esc(contact_note)}</p><div class="text-links">{external_links()}</div></section></div></div></div>'''


def privacy():
    return '''<div class="wrap"><article class="simple-page"><p class="label muted">SITE INFORMATION</p><h1>Privacy &amp; credits.</h1><h2>Privacy</h2><p>This website does not install analytics, advertising trackers, contact forms, or third-party fonts. The website code does not set cookies. The hosting provider may process technical access logs. If hosted on GitHub Pages, GitHub logs visitor IP addresses for security purposes.</p><p>External links, including GitHub, arXiv, and conference proceedings, have their own privacy practices.</p><h2>Photographs</h2><p>Only photographs approved by Jipeng Li are intended for publication. The design preview contains labeled empty image spaces, not photographs. A published photograph is not offered under an open-source license unless a separate license is stated.</p><h2>Design</h2><p>Designed for this website, with editorial references to yichi.studio, 1x.com, and chuweimin.com. No code, photographs, or branding from those websites has been copied into this project.</p><h2>Accessibility</h2><p>The site includes keyboard navigation, visible focus states, reduced-motion support, and descriptive image text. The photograph viewer supports the arrow keys and Escape. Image links work without JavaScript.</p></article></div>'''


def validate():
    if urlsplit(SITE['site_url']).scheme != 'https' or not urlsplit(SITE['site_url']).netloc:
        raise ValueError('site_url must be a complete HTTPS URL.')
    for field in ('github','scholar'):
        if SITE.get(field) and urlsplit(SITE[field]).scheme != 'https':
            raise ValueError(f'{field} must be an HTTPS URL.')
    if SITE.get('email') and not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+',SITE['email']):
        raise ValueError('Invalid public email address.')
    paths = []
    if SITE.get('cv'):
        paths.append(SITE['cv'])
    seen = set()
    for w in RESEARCH:
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',w['slug']):
            raise ValueError('Unsafe research slug.')
        if w['slug'] in seen: raise ValueError('Duplicate research slug.')
        seen.add(w['slug'])
        for key in ('paper','proceedings','code'):
            if w.get(key) and urlsplit(w[key]).scheme != 'https':
                raise ValueError(f'Invalid {key} URL.')
    seen.clear()
    for coll in PHOTO['collections']:
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',coll['slug']):
            raise ValueError('Unsafe collection slug.')
        if coll['slug'] in seen: raise ValueError('Duplicate collection slug.')
        seen.add(coll['slug'])
        if coll.get('cover'): paths.append(coll['cover'])
        for p in coll['photos']:
            if not p.get('title') or not p.get('alt'):
                raise ValueError('Every photograph requires a title and descriptive alt text.')
            paths.append(p['src'])
            if p.get('full'): paths.append(p['full'])
            for v in p.get('variants',[]): paths.append(v['src'])
            for key in ('width','height'):
                if p.get(key) is not None and int(p[key]) <= 0:
                    raise ValueError('Image dimensions must be positive.')
    for path in paths:
        if urlsplit(path).scheme:
            if not path.startswith('https://'): raise ValueError('Only HTTPS asset URLs are allowed.')
            continue
        asset = (ROOT/path).resolve()
        if not asset.is_relative_to(ASSETS.resolve()) or not asset.is_file():
            raise ValueError(f'Missing asset, or asset outside assets/: {path}')


def main():
    global SITE, RESEARCH, PHOTO
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release',action='store_true',help='Require publication-ready content; does not change the preview flag.')
    args=parser.parse_args()
    SITE=json.loads((ROOT/'content/site.json').read_text(encoding='utf-8'))
    RESEARCH=json.loads((ROOT/'content/research.json').read_text(encoding='utf-8'))
    PHOTO=json.loads((ROOT/'content/photography.json').read_text(encoding='utf-8'))
    validate()
    if args.release:
        if SITE['preview']: raise ValueError('Release blocked: set preview to false after content review.')
        if not SITE.get('email'): raise ValueError('Release blocked: add an approved public contact email.')
        if not any(c['photos'] for c in PHOTO['collections']): raise ValueError('Release blocked: no original photographs have been added.')
    OUT.mkdir(exist_ok=True)
    # Only generated pages/assets are replaced. An existing CNAME is preserved.
    for name in ('research','photography','about','privacy','assets'):
        path=OUT/name
        if path.exists(): shutil.rmtree(path)
    shutil.copytree(ASSETS, OUT/'assets',ignore=shutil.ignore_patterns('*.md','.DS_Store'))
    wrapper('index.html', 'Jipeng Li — Research & Photography', SITE['description'], home)
    wrapper('research/index.html','Research — Jipeng Li',SITE['research_intro'],research,'research')
    for w in RESEARCH:
        schema={'@context':'https://schema.org','@type':'ScholarlyArticle','headline':w['title'],'author':[{'@type':'Person','name':n.strip()} for n in w['authors'].split(',')],'datePublished':str(w['year']),'url':w['proceedings'],'isPartOf':{'@type':'CreativeWork','name':w['venue']}}
        wrapper(f'research/{w["slug"]}/index.html', w['short_title']+' — Jipeng Li',w['summary'],lambda w=w:project(w),'research',schema=schema)
    wrapper('photography/index.html','Photography — Jipeng Li',PHOTO['intro'],photography,'photography',True)
    for i,c in enumerate(PHOTO['collections']):
        wrapper(f'photography/{c["slug"]}/index.html',c['name']+' — Photographs by Jipeng Li',c['description'],lambda c=c,i=i:collection(c,i),'photography',True)
    wrapper('about/index.html','About — Jipeng Li',SITE['bio'][0],about,'about')
    wrapper('privacy/index.html','Privacy & credits — Jipeng Li','Privacy, photography credits, and accessibility information.',privacy)
    wrapper('404.html','Page not found — Jipeng Li','The requested page could not be found.',lambda:'<div class="wrap"><section class="simple-page">'+label('404 / PAGE NOT FOUND')+'<h1>A small detour.</h1><p>The page you were looking for is not here.</p><div class="text-links">'+link('index.html','Return home '+arrow('→'))+'</div></section></div>')
    (OUT/'.nojekyll').touch()
    pages=sorted(p for p in OUT.rglob('*.html') if p.name!='404.html')
    robots='User-agent: *\nDisallow: /\n' if SITE['preview'] else f'User-agent: *\nAllow: /\nSitemap: {SITE["site_url"].rstrip("/")}/sitemap.xml\n'
    (OUT/'robots.txt').write_text(robots,encoding='utf-8')
    locations=[] if SITE['preview'] else [SITE['site_url'].rstrip('/')+'/'+p.relative_to(OUT).as_posix().removesuffix('index.html') for p in pages]
    sitemap='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{xml_escape(u)}</loc><lastmod>{SITE["updated"]}</lastmod></url>' for u in locations)+'</urlset>\n'
    (OUT/'sitemap.xml').write_text(sitemap,encoding='utf-8')
    print(f'Built {len(pages)+1} pages in {OUT}')
    print('MODE: PREVIEW — noindex is enabled; this is not access control.' if SITE['preview'] else 'MODE: PUBLIC — search indexing is enabled.')
    print('Next: python3 tools/check_site.py')


if __name__=='__main__':
    try: main()
    except (ValueError,KeyError,OSError,json.JSONDecodeError) as error:
        print(f'Build failed: {error}',file=sys.stderr);sys.exit(1)
