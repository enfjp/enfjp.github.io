#!/usr/bin/env python3
"""Build the photo library, place pages, and owner editor without changing research pages.

Python 3.10+, standard library only. Images are copied byte-for-byte. A hidden
photo is not private: source files and prior commits can remain in the public repo.
"""
from __future__ import annotations
import hashlib
import html
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'docs'
ASSETS = ROOT / 'assets'
PAGE_SIZE = 24
SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')


def esc(value):
    return html.escape(str(value), quote=True)


def relative(path, page):
    if path.startswith(('#', 'https://', 'mailto:')):
        return path
    target, mark, fragment = path.partition('#')
    return os.path.relpath(target, str(Path(page).parent)).replace(os.sep, '/') + (mark + fragment if mark else '')


def photo_paths(photo):
    return set([photo['src'], photo['full']] + [v['src'] for v in photo['variants']])


def validate_catalog(catalog, check_files=True):
    """Fail before altering output, including for broken references and unsafe paths."""
    places = catalog.get('places', [])
    place_ids = [p['id'] for p in places]
    if len(set(place_ids)) != len(place_ids) or any(not SLUG.fullmatch(p) for p in place_ids):
        raise ValueError('Place IDs must be unique URL-safe names.')
    place_names = {p['id']: p['name'] for p in places}
    if any(not isinstance(n, str) or not n.strip() or len(n) > 180 for n in place_names.values()):
        raise ValueError('Every place requires a short name.')
    collections = catalog['collections']
    slugs = [c['slug'] for c in collections]
    if len(set(slugs)) != len(slugs) or any(not SLUG.fullmatch(s) for s in slugs):
        raise ValueError('Collection IDs must be unique URL-safe names.')
    if set(slugs) != {'wild', 'land', 'on-the-road'}:
        raise ValueError('Expected the existing Wild, Land, and On the road collections.')
    ids = set()
    for c in collections:
        for photo in c['photos']:
            pid = photo['id']
            if not SLUG.fullmatch(pid) or pid in ids:
                raise ValueError('Photo IDs must be unique URL-safe names.')
            ids.add(pid)
            for field in ['title', 'alt']:
                if not isinstance(photo.get(field), str) or not photo[field].strip():
                    raise ValueError(f'{pid}: missing {field}.')
            if len(photo['title']) > 160 or len(photo['alt']) > 600:
                raise ValueError('Photo title or alternative text is too long.')
            if photo.get('location_id') not in place_names:
                raise ValueError(f'{pid}: choose a known place.')
            if photo.get('location') != place_names[photo['location_id']]:
                raise ValueError(f'{pid}: place name and ID disagree.')
            if not isinstance(photo.get('published', True), bool):
                raise ValueError('Published must be true or false.')
            if photo.get('display', 'landscape') not in ('landscape', 'portrait', 'wide'):
                raise ValueError('Unsupported photo layout.')
            if any(type(photo.get(k)) is not int or not 0 < photo[k] <= 2048 for k in ('width', 'height')):
                raise ValueError('Invalid display dimensions.')
            if not photo.get('variants'):
                raise ValueError('Missing responsive image sizes.')
            widths = [v['width'] for v in photo['variants']]
            if any(type(w) is not int or not 0 < w <= 2048 for w in widths) or len(set(widths)) != len(widths):
                raise ValueError('Image widths must be distinct positive integers.')
            for raw in photo_paths(photo):
                if not isinstance(raw, str) or not re.fullmatch(r'assets/photos/[a-zA-Z0-9/_-]+\.webp', raw):
                    raise ValueError('Only safe local WebP photo paths are supported.')
                path = (ROOT / raw).resolve()
                if not path.is_relative_to(ASSETS.resolve() / 'photos'):
                    raise ValueError('Photo path is outside the image directory.')
                if check_files and not path.is_file():
                    raise ValueError(f'Image has not been uploaded: {raw}')
    selected = catalog.get('selected', [])
    if len(set(selected)) != len(selected) or any(pid not in ids for pid in selected):
        raise ValueError('Selected must be a unique subset of the library, not the entire library.')
    return {p['id']: (p, c) for c in collections for p in c['photos']}


def image(photo, page, eager=False, wide=False):
    variants = ', '.join(f'{relative(v["src"], page)} {v["width"]}w' for v in photo['variants'])
    if wide:
        sizes = '(max-width: 760px) calc(100vw - 38px), (max-width: 1328px) calc(100vw - 88px), 1240px'
    elif photo['height'] > photo['width']:
        sizes = '(max-width: 760px) calc(100vw - 38px), (max-width: 1100px) 40vw, 460px'
    else:
        sizes = '(max-width: 760px) calc(100vw - 38px), (max-width: 1328px) 44vw, 595px'
    priority = ' fetchpriority="high"' if eager else ''
    return (f'<img src="{esc(relative(photo["src"], page))}" srcset="{esc(variants)}" sizes="{esc(sizes)}" '
            f'width="{photo["width"]}" height="{photo["height"]}" alt="{esc(photo["alt"])}" '
            f'loading="{"eager" if eager else "lazy"}" decoding="async"{priority}>')


def figure(photo, coll, page, first=False, selected=True):
    shape = photo.get('display', 'landscape') if selected else ('portrait' if photo['height'] > photo['width'] else 'landscape')
    return (f'<figure class="sg-work {shape}" data-sg-work data-category="{esc(coll["slug"])}" '
            f'data-title="{esc(photo["title"])}" data-category-name="{esc(coll["name"])}" data-location="{esc(photo["location"])}">'
            f'<a class="sg-photo-link" href="{esc(relative(photo["full"], page))}" aria-label="Open photograph: {esc(photo["title"])}">'
            f'{image(photo, page, first, shape == "wide")}</a><figcaption><span class="sg-caption-main">'
            f'<span class="sg-caption-title">{esc(photo["title"])}</span><span class="sg-location">{esc(photo["location"])}</span>'
            f'</span><span class="sg-category">{esc(coll["name"])}</span></figcaption></figure>')


def viewer():
    return '''<dialog class="sg-viewer" id="sg-viewer" aria-label="Photograph viewer"><div class="sg-viewer-frame">
<div class="sg-viewer-top"><span id="sg-viewer-category"></span><button class="sg-close" id="sg-close" type="button" aria-label="Close photograph viewer" autofocus>Close ×</button></div>
<div class="sg-stage"><button class="sg-step sg-prev" id="sg-previous" type="button" aria-label="Previous photograph">←</button><img id="sg-viewer-image" alt=""><p class="sg-error" role="alert">The photograph could not be loaded. Close the viewer and try again.</p><button class="sg-step sg-next" id="sg-next" type="button" aria-label="Next photograph">→</button></div>
<div class="sg-viewer-caption"><div class="sg-viewer-details" aria-live="polite"><p id="sg-viewer-title"></p><p id="sg-viewer-location" hidden></p></div><small>← → Browse · Esc Close</small></div></div></dialog>'''


def page_shell(template, page, site, title, description, body):
    before, rest = template.split('<main id="main">', 1)
    after = rest.split('</main>', 1)[1]
    def adjust(match):
        attr, url = match.group(1), html.unescape(match.group(2))
        parts = urlsplit(url)
        if not url or parts.scheme or url.startswith(('#', '/')):
            return match.group(0)
        target = os.path.normpath(os.path.join('photography', parts.path)).replace(os.sep, '/')
        new = relative(target, page)
        if parts.query: new += '?' + parts.query
        if parts.fragment: new += '#' + parts.fragment
        return f'{attr}="{esc(new)}"'
    before = re.sub(r'(href|src)="([^"]*)"', adjust, before)
    after = re.sub(r'(href|src)="([^"]*)"', adjust, after)
    canonical = site['site_url'].rstrip('/') + '/' + page.removesuffix('index.html')
    before = re.sub(r'<title>.*?</title>', lambda _: f'<title>{esc(title)}</title>', before, flags=re.S)
    for key, value in [('description', description), ('og:title', title), ('og:description', description), ('og:url', canonical)]:
        before = re.sub(r'(<meta (?:name|property)="' + re.escape(key) + r'" content=")[^"]*(">)',
                        lambda m: m.group(1) + esc(value) + m.group(2), before)
    before = re.sub(r'<link rel="canonical" href="[^"]*">', lambda _: f'<link rel="canonical" href="{esc(canonical)}">', before)
    schema = json.dumps({'@context': 'https://schema.org', '@type': 'CollectionPage', 'name': title, 'url': canonical, 'description': description}, ensure_ascii=False).replace('<', '\\u003c')
    before = re.sub(r'<script type="application/ld\+json">.*?</script>', lambda _: f'<script type="application/ld+json">{schema}</script>', before, flags=re.S)
    before = re.sub(r'<div class="wrap"><p class="preview-ribbon">.*?</p></div>', '', before, flags=re.S)
    before = re.sub(r'<(?:link|script)[^>]*(?:gallery\.css|gallery\.js)[^>]*>(?:</script>)?', '', before)
    extra = f'<link rel="stylesheet" href="{esc(relative("assets/gallery.css", page))}"><script src="{esc(relative("assets/gallery.js", page))}" defer></script>'
    return before.replace('</head>', extra + '</head>') + '<main id="main">' + body + '</main>' + after


def browse_path(coll=None, place=None, index=0):
    base = 'photography/' + (coll['slug'] + '/' if coll else '') + (place['id'] + '/' if place else '')
    return base + (f'page/{index + 1}/' if index else '') + 'index.html'


def navigation(catalog, page, collection=None, place=None):
    links = [('Selected', 'photography/index.html', collection is None)]
    links += [(c['name'], browse_path(c), bool(collection and c['slug'] == collection['slug'])) for c in catalog['collections']]
    tabs = '<nav class="sg-filters" aria-label="Photo categories">' + ''.join(
        f'<a class="sg-filter" href="{esc(relative(path, page))}"' + (' aria-current="page"' if active else '') + f'>{esc(name)}</a>' for name, path, active in links) + '</nav>'
    if collection:
        active_places = {p['location_id'] for p in collection['photos'] if p.get('published', True)}
        options = [('All places', browse_path(collection), place is None)]
        options += [(p['name'], browse_path(collection, p), bool(place and p['id'] == place['id'])) for p in catalog['places'] if p['id'] in active_places]
        place_links = ''.join(f'<a href="{esc(relative(path, page))}"' + (' aria-current="page"' if active else '') + f'>{esc(name)}</a>' for name, path, active in options)
        tabs += '<nav class="sg-place-nav" aria-label="Shooting locations"><span>Place</span>' + place_links + '</nav>'
    return '<div class="sg-toolbar">' + tabs + '</div>'


def gallery_body(catalog, page, entries, collection=None, place=None, index=0, total=1):
    title = place['name'] if place else (collection['name'] if collection else catalog['title'])
    intro = (collection['name'] + ' · ' + place['name']) if place else (collection['subtitle'] if collection else catalog['intro'])
    back = ''
    if place:
        back = f'<a class="sg-back" href="{esc(relative(browse_path(collection), page))}">← {esc(collection["name"])}</a>'
    elif collection:
        back = f'<a class="sg-back" href="{esc(relative("photography/index.html", page))}">← Selected photographs</a>'
    works = ''.join(figure(p, c, page, i == 0, collection is None) for i, (p, c) in enumerate(entries))
    if not entries:
        works = '<p class="sg-empty">No photographs are published in this collection yet.</p>'
    pager = ''
    if total > 1:
        controls = []
        if index: controls.append(f'<a rel="prev" href="{esc(relative(browse_path(collection, place, index - 1), page))}">← Previous photographs</a>')
        if index + 1 < total: controls.append(f'<a rel="next" href="{esc(relative(browse_path(collection, place, index + 1), page))}">More photographs →</a>')
        pager = '<nav class="sg-pagination" aria-label="More photographs">' + ''.join(controls) + '</nav>'
    grid_class = 'sg-grid' if collection is None else 'sg-grid sg-collection-grid'
    ending = f'<div class="sg-ending"><p>Photographs by Jipeng Li.</p><a href="{esc(relative("about/index.html#contact", page))}">Get in touch ↗</a></div>'
    return (f'<div class="sg-wrap"><header class="sg-intro">{back}<p class="sg-eyebrow">Photography</p><h1>{esc(title)}</h1>'
            f'<p>{esc(intro)}</p></header>{navigation(catalog, page, collection, place)}'
            f'<div class="{grid_class}" id="sg-grid">{works}</div>{pager}{ending}</div>{viewer()}')


def homepage_teaser(catalog):
    colls = {c['slug']: c for c in catalog['collections']}
    def cover(slug, wide=False):
        c = colls[slug]
        available = [p for p in c['photos'] if p.get('published', True)]
        if not available: return ''
        p = next((p for p in available if p['src'] == c.get('cover')), available[0])
        return (f'<a class="sg-home-card {"sg-home-wide" if wide else "sg-home-portrait"}" href="photography/{slug}/index.html">'
                f'{image(p, "index.html", False, wide)}<div class="sg-home-caption"><div><h3>{esc(c["name"])}</h3>'
                f'<p>{esc(c["subtitle"])}</p></div><span aria-hidden="true">↗</span></div></a>')
    return ('<section class="photo-teaser sg-home-section" id="photography"><div class="sg-wrap"><div class="section-heading"><div>'
            '<p class="label">Photography</p><h2>Ways of seeing.</h2></div><a class="text-link" href="photography/index.html">Enter gallery →</a></div>'
            '<div class="sg-home-covers">' + cover('land', True) + cover('wild') + cover('on-the-road') + '</div>'
            '<p class="sg-home-credit">Photographs by Jipeng Li.</p></div></section>')


def main():
    site = json.loads((ROOT / 'content/site.json').read_text(encoding='utf-8'))
    catalog_file = ROOT / 'content/photography.json'
    catalog = json.loads(catalog_file.read_text(encoding='utf-8'))
    lookup = validate_catalog(catalog)
    template = (OUT / 'photography/index.html').read_text(encoding='utf-8')
    pages = {}
    selected = [lookup[pid] for pid in catalog['selected'] if lookup[pid][0].get('published', True)]
    def add_group(entries, coll=None, place=None):
        total = max(1, (len(entries) + PAGE_SIZE - 1) // PAGE_SIZE)
        for index in range(total):
            page = browse_path(coll, place, index)
            title = (place['name'] + ' — ' + coll['name']) if place else (coll['name'] if coll else 'Photography')
            pages[page] = page_shell(template, page, site, title + ' — Jipeng Li', catalog['intro'],
                                    gallery_body(catalog, page, entries[index * PAGE_SIZE:(index + 1) * PAGE_SIZE], coll, place, index, total))
    add_group(selected)
    for coll in catalog['collections']:
        entries = [(p, coll) for p in coll['photos'] if p.get('published', True)]
        add_group(entries, coll)
        for place in catalog['places']:
            group = [(p, c) for p, c in entries if p['location_id'] == place['id']]
            if group: add_group(group, coll, place)
    home = (OUT / 'index.html').read_text(encoding='utf-8')
    home, count = re.subn(r'<section class="photo-teaser(?: [^"]*)?" id="photography">.*?</section>', lambda _: homepage_teaser(catalog), home, count=1, flags=re.S)
    if count != 1: raise ValueError('Home photography section was not found.')
    home = re.sub(r'<link rel="stylesheet" href="assets/gallery.css">', '', home)
    home = home.replace('</head>', '<link rel="stylesheet" href="assets/gallery.css"></head>')
    home = re.sub(r'<div class="wrap"><p class="preview-ribbon">.*?</p></div>', '', home, flags=re.S)
    home = re.sub(r'(<p class="label[^\"]*">)0\d / ', r'\1', home)
    pages['index.html'] = home
    active = [p for p, _ in lookup.values() if p.get('published', True)]
    paths = set().union(*(photo_paths(p) for p in active)) if active else set()
    total_bytes = sum((ROOT / raw).stat().st_size for raw in paths)
    if total_bytes > 950_000_000:
        raise ValueError('Published photo files exceed the 950 MB safety budget; move media storage first.')
    # Everything above is validation/planning. Mutate only the gallery-owned outputs below.
    for path in (OUT / 'photography').rglob('*.html'):
        if path.relative_to(OUT).as_posix() not in pages: path.unlink()
    for file in (OUT / 'assets/photos').rglob('*.webp'):
        if file.relative_to(OUT).as_posix() not in paths: file.unlink()
    for raw in paths:
        dest = OUT / raw
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / raw, dest)
    for name in ('gallery.css', 'gallery.js'):
        shutil.copy2(ASSETS / name, OUT / 'assets' / name)
    for path, markup in pages.items():
        dest = OUT / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(markup, encoding='utf-8')
    public = dict(catalog)
    public['collections'] = [dict(c, photos=[p for p in c['photos'] if p.get('published', True)]) for c in catalog['collections']]
    public['selected'] = [p['id'] for p, _ in selected]
    public['catalog_sha256'] = hashlib.sha256(catalog_file.read_bytes()).hexdigest()
    (OUT / 'photography/catalog-public.json').write_text(json.dumps(public, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if (ROOT / 'admin').is_dir():
        shutil.copytree(ROOT / 'admin', OUT / 'admin', dirs_exist_ok=True)
    print(f'Gallery ready: {len(active)} published, {len(selected)} selected; {len(pages)} generated pages; {total_bytes / 1e6:.2f} MB image bytes.')


if __name__ == '__main__':
    main()
