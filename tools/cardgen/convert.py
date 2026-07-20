#!/usr/bin/env python3
"""render.mjs가 만든 PNG를 jpg+webp로 변환해 content/images/에 저장한다.
사용: python3 convert.py <outDir> <imagesDir>
  outDir: render.mjs의 out (jobs.json + *.png)
  imagesDir: venom-wordpress/preview/content/images
"""
import json, sys, os
from PIL import Image

out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), 'out')
img_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), '..', '..', 'venom-wordpress', 'preview', 'content', 'images')

jobs_path = os.path.join(out_dir, 'jobs.json')
if not os.path.exists(jobs_path):
    print('jobs.json 없음 — 변환할 것 없음'); sys.exit(0)
jobs = json.load(open(jobs_path))
if not jobs:
    print('변환 대상 없음'); sys.exit(0)

os.makedirs(img_dir, exist_ok=True)
n = 0
for j in jobs:
    png = os.path.join(out_dir, j['out'] + '.png')
    if not os.path.exists(png):
        print('MISS png', j['out']); continue
    im = Image.open(png).convert('RGB')
    for base in j['files']:
        im.save(os.path.join(img_dir, base + '.jpg'), 'JPEG', quality=86, optimize=True)
        im.save(os.path.join(img_dir, base + '.webp'), 'WEBP', quality=82, method=6)
        n += 1
print(f'변환 완료: {n} base → jpg+webp {n*2}개')
