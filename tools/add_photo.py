#!/usr/bin/env python3
"""Add ONE approved original photograph. Originals are never copied to the project.

Requires Pillow: python3 -m pip install Pillow
Example:
python3 tools/add_photo.py wild /outside/this/project/fox.jpg \
  --title 'An evening encounter' --alt 'A fox standing in grass in evening light' \
  --location 'Yellowstone' --year 2026

Exports web-sized WebP files, applies EXIF orientation, converts an embedded color
profile to sRGB, removes EXIF/GPS data, and updates content/photography.json.
"""
from __future__ import annotations
import argparse
import io
import json
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent


def main():
    try:
        from PIL import Image, ImageCms, ImageOps
    except ImportError:
        raise ValueError('Install Pillow first: python3 -m pip install Pillow')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('collection');parser.add_argument('source',type=Path)
    parser.add_argument('--title',required=True);parser.add_argument('--alt',required=True)
    parser.add_argument('--location',default='');parser.add_argument('--year',type=int)
    args=parser.parse_args()
    if not args.title.strip() or not args.alt.strip():raise ValueError('Title and descriptive alt text are required.')
    source=args.source.expanduser().resolve()
    if source.is_relative_to(ROOT):raise ValueError('Keep original files outside the website project. Move the original outside and try again.')
    if not source.is_file():raise ValueError(f'File not found: {source}')
    data_path=ROOT/'content/photography.json'
    data=json.loads(data_path.read_text(encoding='utf-8'))
    collection=next((c for c in data['collections'] if c['slug']==args.collection),None)
    if collection is None:raise ValueError('Unknown collection. Use an existing slug from content/photography.json.')
    slug=re.sub(r'[^a-z0-9]+','-',source.stem.lower()).strip('-') or f'photo-{len(collection["photos"])+1:03}'
    output=ROOT/'assets/photos'/args.collection
    if any(output.glob(slug+'-*.webp')):raise ValueError('An image with that file stem already exists. Rename your source copy to avoid overwriting.')
    output.mkdir(parents=True,exist_ok=True)
    with Image.open(source) as original:
        if original.width*original.height>120_000_000:raise ValueError('Image is too large. Export a smaller JPEG first.')
        image=ImageOps.exif_transpose(original)
        profile=image.info.get('icc_profile')
        if profile:
            try:
                image=ImageCms.profileToProfile(image,ImageCms.ImageCmsProfile(io.BytesIO(profile)),ImageCms.createProfile('sRGB'),outputMode='RGB')
            except Exception as e:
                raise ValueError('Cannot convert the embedded color profile. Export the original as an sRGB JPEG first.') from e
        elif image.mode in ('RGBA','LA'):
            rgba=image.convert('RGBA'); bg=Image.new('RGB',rgba.size,'white');bg.paste(rgba,mask=rgba.getchannel('A'));image=bg
        else:image=image.convert('RGB')
        entries=[];used=set()
        for long_edge in (900,1600,2400):
            img=image.copy();img.thumbnail((long_edge,long_edge),Image.Resampling.LANCZOS)
            if img.size in used:continue
            used.add(img.size)
            file=output/f'{slug}-{long_edge}.webp'
            img.save(file,'WEBP',quality=86,method=6,exif=b'',icc_profile=b'')
            entries.append({'src':file.relative_to(ROOT).as_posix(),'width':img.width,'height':img.height})
    medium=entries[min(1,len(entries)-1)]
    photo={'title':args.title.strip(),'alt':args.alt.strip(),'location':args.location.strip(),'src':medium['src'],'full':entries[-1]['src'],'width':medium['width'],'height':medium['height'],'variants':[{'src':v['src'],'width':v['width']} for v in entries]}
    if args.year:photo['year']=args.year
    collection['photos'].append(photo)
    if not collection.get('cover'):collection['cover']=medium['src']
    data_path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Added photograph. Verify the title, alt text, location, and year in content/photography.json.')
    print('Original retained outside project; WebP exports have no EXIF/GPS metadata.')
    print('Next: python3 tools/build.py && python3 tools/check_site.py')

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,json.JSONDecodeError) as error:
        print(f'Photo import failed: {error}',file=sys.stderr);sys.exit(1)
