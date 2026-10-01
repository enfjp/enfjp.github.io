#!/usr/bin/env python3
"""Build the website and its source-backed academic profile (Python 3.9+).

Public content lives in content/*.json. The older CV is not a website asset.
The existing build interface and release checks are preserved.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
import _site_builder as base


def render_profile() -> str:
    """Render selected biographical content without attaching a CV file."""
    profile = json.loads((base.ROOT / 'content/profile.json').read_text(encoding='utf-8'))
    esc, link, label, arrow = base.esc, base.link, base.label, base.arrow
    sections = [('education', 'Education'), ('selected-work', 'Selected work'),
                ('background', 'Research background'), ('honors', 'Selected honors'),
                ('service', 'Academic service'), ('contact', 'Contact')]
    contents = ''.join(link('#' + key, title, css='') for key, title in sections)
    bio = ''.join(f'<p>{esc(text)}</p>' for text in base.SITE['bio'])
    education = ''
    for entry in base.SITE['education']:
        note = f'<p class="profile-detail">{esc(entry["note"])}</p>' if entry.get('note') else ''
        education += (f'<article class="profile-entry">{label(entry["period"], "muted")}'
                      f'<h3>{esc(entry["school"])}</h3><p class="profile-degree">{esc(entry["degree"])}</p>{note}</article>')
    publications = ''
    for work in base.RESEARCH:
        path = 'research/' + work['slug'] + '/index.html'
        publications += (f'<article class="profile-publication">{base.venue_badges(work)}'
                         f'<h3>{link(path, esc(work["title"]), css="")}</h3>'
                         f'{link(path, "Project details " + arrow("→"))}</article>')
    background = ''
    for entry in profile['research_background']:
        background += (f'<article class="profile-entry">{label(entry["context"], "muted")}'
                       f'<h3>{esc(entry["title"])}</h3><p>{esc(entry["description"])}</p>'
                       f'<p class="profile-detail">{esc(entry["advisors"])}</p></article>')
    honors = ''
    for entry in profile['honors']:
        honors += (f'<article class="profile-award"><span class="label muted">{esc(entry["year"])}</span>'
                   f'<div><h3>{esc(entry["title"])}</h3><p>{esc(entry["detail"])}</p></div></article>')
    service = ''.join(f'<p>{esc(item)}</p>' for item in profile['service'])
    return f'''<div class="wrap profile-page"><header class="page-hero">{label('03 / ABOUT')}<h1>Behind the work.</h1><p class="deck">Research, education, and a life with a camera.</p></header>
<div class="profile-layout"><aside class="profile-sidebar" aria-label="Academic profile navigation"><div class="profile-identity"><span class="profile-monogram" aria-hidden="true">JL</span><h2>Jipeng Li <span lang="zh-CN">冀鹏</span></h2><p>Ph.D. student · UC Irvine</p><p>{esc(base.SITE['location'])}</p></div><nav class="profile-nav" aria-label="On this page">{contents}</nav><div class="profile-direct">{link('mailto:' + base.SITE['email'], esc(base.SITE['email']) + ' ' + arrow())}</div></aside>
<div class="profile-main"><section class="profile-intro" aria-label="Biography">{bio}</section>
<section class="profile-section" id="education"><header>{label('01 / EDUCATION')}<h2>Academic path</h2></header><div class="profile-education">{education}</div></section>
<section class="profile-section" id="selected-work"><header>{label('02 / SELECTED WORK')}<h2>Recent publications</h2></header>{publications}</section>
<section class="profile-section" id="background"><header>{label('03 / BACKGROUND')}<h2>Earlier research</h2></header>{background}</section>
<section class="profile-section" id="honors"><header>{label('04 / RECOGNITION')}<h2>Selected honors</h2></header>{honors}</section>
<section class="profile-section" id="service"><header>{label('05 / COMMUNITY')}<h2>Academic service</h2></header><div class="profile-service">{service}</div></section>
<section class="profile-section profile-contact" id="contact"><header>{label('06 / CONTACT')}<h2>Get in touch.</h2></header><p>For research correspondence, please use my university email.</p><div class="text-links">{base.external_links()}</div></section></div></div></div>'''


def main() -> None:
    base.about = render_profile
    base.main()
    # The shared builder keeps the other pages unchanged. Add the profile-only stylesheet.
    path = base.OUT / 'about/index.html'
    markup = path.read_text(encoding='utf-8')
    markup = markup.replace('</head>', '<link rel="stylesheet" href="../assets/profile.css">\n</head>', 1)
    path.write_text(markup, encoding='utf-8')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as error:
        print(f'Build failed: {error}', file=sys.stderr)
        sys.exit(1)
