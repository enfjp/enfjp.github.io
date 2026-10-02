#!/usr/bin/env python3
"""Render the selected photographs after the shared site build.

Uses only Python's standard library. Never modifies source photographs.
Missing images fail the build before any existing pages are changed.
"""
from __future__ import annotations
import html
import json
import os
import re
import shutil
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'docs'
ASSETS = ROOT / 'assets'


def esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def relative(path: str, page: str) -> str:
    if path.startswith(('#', 'https://', 'mailto:')):
        return path
    return os.path.relpath(path, str(Path(page).parent)).replace(os.sep, '/')


def image(photo: dict, page: str, eager: bool = False, wide: bool = False) -> str:
    variants = ', '.join(f'{relative(v["src"], page)} {v["width"]}w' for v in photo['variants'])
    if wide:
        sizes='(max-width: 760px) calc(100vw - 38px), (max-width: 1328px) calc(100vw - 88px), 1240px'
    elif photo['height'] > photo['width']:
        sizes='(max-width: 760px) calc(100vw - 38px), (max-width: 1100px) 40vw, 460px'
    else:
        sizes='(max-width: 760px) calc(100vw - 38px), (max-width: 1328px) 44vw, 595px'
    priority = ' fetchpriority="high"' if eager else ''
    return (f'<img src="{esc(relative(photo["src"],page))}" srcset="{esc(variants)}" '
            f'sizes="{esc(sizes)}" width="{photo["width"]}" height="{photo["height"]}" '
            f'alt="{esc(photo["alt"])}" loading="{"eager" if eager else "lazy"}" decoding="async"{priority}>')


def figure(photo: dict, coll: dict, page: str, first: bool = False, selected: bool = True) -> str:
    shape = photo.get('display','landscape') if selected else ('portrait' if photo['height']>photo['width'] else 'landscape')
    location = photo.get('location', '')
    location_line = f'<span class="sg-location">{esc(location)}</span>' if location else ''
    return (f'<figure class="sg-work {esc(shape)}" data-sg-work data-category="{esc(coll["slug"])}" '
            f'data-title="{esc(photo["title"])}" data-category-name="{esc(coll["name"])}" '
            f'data-location="{esc(location)}">'
            f'<a class="sg-photo-link" href="{esc(relative(photo["full"],page))}" '
            f'aria-label="Open photograph: {esc(photo["title"])}">'
            f'{image(photo,page,first,shape=="wide")}</a><figcaption>'
            f'<span class="sg-caption-main"><span class="sg-caption-title">{esc(photo["title"])}</span>'
            f'{location_line}</span>'
            f'<span class="sg-category">{esc(coll["name"])}</span></figcaption></figure>')


def viewer() -> str:
    return '''<dialog class="sg-viewer" id="sg-viewer" aria-label="Photograph viewer">
<div class="sg-viewer-frame"><div class="sg-viewer-top"><span id="sg-viewer-category"></span>
<button class="sg-close" id="sg-close" type="button" aria-label="Close photograph viewer" autofocus>Close ×</button></div>
<div class="sg-stage"><button class="sg-step sg-prev" id="sg-previous" type="button" aria-label="Previous photograph">←</button>
<img id="sg-viewer-image" alt=""><p class="sg-error" role="alert">The photograph could not be loaded. Close the viewer and try again.</p>
<button class="sg-step sg-next" id="sg-next" type="button" aria-label="Next photograph">→</button></div>
<div class="sg-viewer-caption"><div class="sg-viewer-details" aria-live="polite"><p id="sg-viewer-title"></p><p id="sg-viewer-location" hidden></p></div><small>← → Browse · Esc Close</small></div></div></dialog>'''


def page_shell(template: str, page: str, site: dict, title: str, description: str, body: str) -> str:
    """Keep the existing shared header/footer; adjust their relative links."""
    parts=template.split('<main id="main">',1)
    if len(parts)!=2 or '</main>' not in parts[1]:
        raise ValueError('Shared photography template is missing its main element.')
    before=parts[0]; after=parts[1].split('</main>',1)[1]
    def adjust(match):
        attr,url=match.group(1),html.unescape(match.group(2))
        parsed=urlsplit(url)
        if not url or parsed.scheme or url.startswith(('#','/')):
            return match.group(0)
        target=os.path.normpath(os.path.join('photography',parsed.path)).replace(os.sep,'/')
        new=relative(target,page)
        if parsed.query: new+='?'+parsed.query
        if parsed.fragment: new+='#'+parsed.fragment
        return f'{attr}="{esc(new)}"'
    before=re.sub(r'(href|src)="([^"]*)"',adjust,before)
    after=re.sub(r'(href|src)="([^"]*)"',adjust,after)
    canonical=site['site_url'].rstrip('/')+'/'+page.removesuffix('index.html')
    before=re.sub(r'<title>.*?</title>',f'<title>{esc(title)}</title>',before,flags=re.S)
    for key,value in [('description',description),('og:title',title),('og:description',description),('og:url',canonical)]:
        before=re.sub(r'(<meta (?:name|property)="'+re.escape(key)+r'" content=")[^"]*(">)',
                      lambda m:m.group(1)+esc(value)+m.group(2),before)
    before=re.sub(r'<link rel="canonical" href="[^"]*">',f'<link rel="canonical" href="{esc(canonical)}">',before)
    schema={'@context':'https://schema.org','@type':'CollectionPage','name':title,'url':canonical,'description':description}
    schema_text=json.dumps(schema,ensure_ascii=False).replace('<','\\u003c')
    before=re.sub(r'<script type="application/ld\+json">.*?</script>',
                  lambda _:f'<script type="application/ld+json">{schema_text}</script>',before,flags=re.S)
    before=re.sub(r'<div class="wrap"><p class="preview-ribbon">.*?</p></div>','',before,flags=re.S)
    # Remove older integration tags so rebuilding is idempotent.
    before=re.sub(r'<(?:link|script)[^>]*(?:gallery\.css|gallery\.js)[^>]*>(?:</script>)?','',before)
    extra=(f'<link rel="stylesheet" href="{esc(relative("assets/gallery.css",page))}">'
           f'<script src="{esc(relative("assets/gallery.js",page))}" defer></script>')
    before=before.replace('</head>',extra+'</head>')
    return before+'<main id="main">'+body+'</main>'+after


def gallery_body(catalog: dict, page: str, collection: dict | None = None) -> str:
    index={p['id']:(p,c) for c in catalog['collections'] for p in c['photos']}
    if collection:
        entries=[index[p['id']] for p in collection['photos']]
        title=collection['name']; intro=collection['subtitle']
        back=f'<a class="sg-back" href="{esc(relative("photography/index.html",page))}">← All photographs</a>'
        buttons=''; grid_class='sg-grid sg-collection-grid'
    else:
        entries=[index[p] for p in catalog['selected']]
        title=catalog['title'];intro=catalog['intro'];back='';grid_class='sg-grid'
        buttons=('<nav class="sg-filters" aria-label="Filter photographs" hidden>'
                 '<button class="sg-filter" data-sg-filter="all" type="button" aria-pressed="true">Selected</button>'+
                 ''.join(f'<button class="sg-filter" type="button" data-sg-filter="{esc(c["slug"])}" aria-pressed="false">{esc(c["name"])}</button>' for c in catalog['collections'])+'</nav>')
    works=''.join(figure(p,c,page,i==0,collection is None) for i,(p,c) in enumerate(entries))
    note=('<div class="sg-ending"><p>Photographs by Jipeng Li.</p><a href="'+esc(relative('about/index.html#contact',page))+'">Get in touch ↗</a></div>')
    return (f'<div class="sg-wrap"><header class="sg-intro">{back}<p class="sg-eyebrow">Photography</p>'
            f'<h1>{esc(title)}</h1><p>{esc(intro)}</p></header><div class="sg-toolbar">{buttons}</div>'
            f'<div class="{grid_class}" id="sg-grid">{works}</div>{note}</div>{viewer()}')


def homepage_teaser(catalog: dict) -> str:
    colls={c['slug']:c for c in catalog['collections']}
    def cover(slug,wide=False):
        c=colls[slug]
        p=next(p for p in c['photos'] if p['src']==c['cover'])
        return (f'<a class="sg-home-card {"sg-home-wide" if wide else "sg-home-portrait"}" href="photography/{esc(slug)}/index.html">'
                f'{image(p,"index.html",False,wide)}<div class="sg-home-caption"><div><h3>{esc(c["name"])}</h3>'
                f'<p>{esc(c["subtitle"])}</p></div><span aria-hidden="true">↗</span></div></a>')
    return ('<section class="photo-teaser sg-home-section" id="photography"><div class="sg-wrap">'
            '<div class="section-heading"><div><p class="label">Photography</p><h2>Ways of seeing.</h2></div>'
            '<a class="text-link" href="photography/index.html">Enter gallery <span class="arrow" aria-hidden="true">→</span></a></div>'
            '<div class="sg-home-covers">'+cover('land',True)+cover('wild')+cover('on-the-road')+'</div>'
            '<p class="sg-home-credit">Photographs by Jipeng Li.</p></div></section>')


def main() -> None:
    site=json.loads((ROOT/'content/site.json').read_text(encoding='utf-8'))
    catalog=json.loads((ROOT/'content/photography.json').read_text(encoding='utf-8'))
    photos=[p for c in catalog['collections'] for p in c['photos']]
    if not photos:
        return
    ids=[p['id'] for p in photos]
    if len(set(ids))!=len(ids) or sorted(catalog['selected'])!=sorted(ids):
        raise ValueError('Selected photographs must match the catalog exactly, without duplicates.')
    for c in catalog['collections']:
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',c['slug']):
            raise ValueError('Unsafe collection slug.')
        if c['cover'] not in [p['src'] for p in c['photos']]:
            raise ValueError('Collection cover must be an approved photograph.')
    paths=[]
    for p in photos:
        if not p.get('title') or not p.get('alt'):
            raise ValueError('Every photo requires a descriptive title and alt text.')
        if 'location' in p and not isinstance(p['location'], str):
            raise ValueError('Photo locations must be text.')
        paths.extend([p['src'],p['full']]+[v['src'] for v in p['variants']])
    for raw in set(paths):
        file=(ROOT/raw).resolve()
        if not file.is_relative_to(ASSETS.resolve()) or not file.is_file():
            raise ValueError(f'Photograph has not been uploaded: {raw}')
    template=(OUT/'photography/index.html').read_text(encoding='utf-8')
    pages={'photography/index.html':page_shell(template,'photography/index.html',site,
           'Photography — Jipeng Li',catalog['intro'],gallery_body(catalog,'photography/index.html'))}
    for c in catalog['collections']:
        path=f'photography/{c["slug"]}/index.html'
        pages[path]=page_shell(template,path,site,c['name']+' — Photographs by Jipeng Li',c['description'],gallery_body(catalog,path,c))
    home=(OUT/'index.html').read_text(encoding='utf-8')
    home,count=re.subn(r'<section class="photo-teaser(?: [^"]*)?" id="photography">.*?</section>',
                      lambda _:homepage_teaser(catalog),home,count=1,flags=re.S)
    if count!=1:
        raise ValueError('Home page photography section was not found; no page was changed.')
    home=re.sub(r'<link rel="stylesheet" href="assets/gallery.css">','',home)
    home=home.replace('</head>','<link rel="stylesheet" href="assets/gallery.css"></head>')
    # Keep the existing indexing setting; remove only obsolete visual preview notices.
    ribbon=r'<div class="wrap"><p class="preview-ribbon">.*?</p></div>'
    home=re.sub(ribbon,'',home,flags=re.S)
    # The user requested an uncluttered presentation; remove decorative homepage section prefixes.
    home=re.sub(r'(<p class="label[^\"]*">)0\d / ',r'\1',home)
    pages['index.html']=home
    for raw in set(paths):
        dest=OUT/raw;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/raw,dest)
    for name in ('gallery.css','gallery.js'):
        shutil.copy2(ASSETS/name,OUT/'assets'/name)
    for path,markup in pages.items():
        dest=OUT/path;dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(markup,encoding='utf-8')
    print(f'Published {len(photos)} photographs into {len(pages)} local pages. No filenames or photo numbers are displayed.')


if __name__=='__main__':
    main()
