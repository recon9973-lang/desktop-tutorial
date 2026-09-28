#!/usr/bin/env python3
"""영상(mp4 주소) → 소리 없음 · 자막 · 이음새 없는 반복 · 움직이는 WebP.
GitHub Actions(.github/workflows/video-to-webp.yml)가 부른다. 로컬에서도 ffmpeg 만 있으면 된다.

환경변수: IN_URL, IN_NAME, IN_SUBS(" | " 로 줄 나눔, "\\n" 은 한 줄 안 줄바꿈), IN_W, IN_FPS, IN_BLEND, IN_Q, IN_GIF, FONT
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'venom-wordpress/preview/images/motion')

def sh(cmd, **kw):
    print('$', ' '.join(cmd) if isinstance(cmd, list) else cmd, flush=True)
    return subprocess.run(cmd, check=True, **kw)

def main():
    url = os.environ['IN_URL'].strip()
    name = re.sub(r'[^A-Za-z0-9_-]+', '-', os.environ['IN_NAME'].strip()).strip('-') or 'motion'
    subs = [s.strip().replace('\\n', '\n') for s in os.environ.get('IN_SUBS', '').split(' | ') if s.strip()]
    W = int(os.environ.get('IN_W') or 480); W += W % 2
    FPS = int(os.environ.get('IN_FPS') or 12)
    BLEND = float(os.environ.get('IN_BLEND') or 0)
    Q = int(os.environ.get('IN_Q') or 80)
    GIF = (os.environ.get('IN_GIF') or 'false').lower() == 'true'
    FONT = os.environ.get('FONT') or ''
    os.makedirs(OUT_DIR, exist_ok=True)
    src = '/tmp/src.mp4'
    sh(['curl', '-fsSL', '--retry', '3', '-o', src, url])

    probe = sh(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', src], capture_output=True, text=True)
    D = float(json.loads(probe.stdout)['format']['duration'])
    X = min(BLEND, D / 4) if BLEND > 0 else 0.0
    L = D - X  # 결과 길이
    print(f'duration={D:.2f}s blend={X:.2f}s out={L:.2f}s')

    # 1) 크기·장수 맞추기
    chain = [f'[0:v]scale={W}:-2:flags=lanczos,fps={FPS},format=yuv420p[v]']
    cur = 'v'
    # 2) 끝↔처음 겹쳐 섞기(이음새 없는 반복)
    if X > 0:
        chain += [
            f'[{cur}]split[a][b]',
            f'[a]trim=start={X:.3f},setpts=PTS-STARTPTS[main]',
            f'[b]trim=start=0:end={X:.3f},setpts=PTS-STARTPTS[head]',
            f'[main][head]xfade=transition=fade:duration={X:.3f}:offset={D - 2 * X:.3f}[looped]',
        ]
        cur = 'looped'
    # 3) 자막(줄마다 시간 나눠 차례로)
    if subs:
        fs = max(14, round(W * 0.065))
        n = len(subs)
        dts = []
        for i, text in enumerate(subs):
            path = f'/tmp/sub_{i}.txt'
            open(path, 'w', encoding='utf-8').write(text)
            a, b = L * i / n, L * (i + 1) / n
            if i == n - 1: b = L + 1
            font = f"fontfile='{FONT}':" if FONT else ''
            dts.append(f"drawtext={font}textfile={path}:fontsize={fs}:fontcolor=white:line_spacing={fs // 5}:"
                       f"borderw=3:bordercolor=black@0.7:box=1:boxcolor=black@0.5:boxborderw={fs // 2}:"
                       f"x=(w-text_w)/2:y=h-text_h-h*0.08:enable='between(t,{a:.3f},{b:.3f})'")
        chain.append(f'[{cur}]' + ','.join(dts) + '[out]')
        cur = 'out'
    graph = ';'.join(chain)

    out_webp = os.path.join(OUT_DIR, name + '.webp')
    sh(['ffmpeg', '-y', '-v', 'error', '-i', src, '-filter_complex', graph, '-map', f'[{cur}]', '-an',
        '-c:v', 'libwebp_anim', '-lossless', '0', '-q:v', str(Q), '-compression_level', '4', '-loop', '0', out_webp])
    print(f'OK {out_webp} {os.path.getsize(out_webp) // 1024}KB')

    if GIF:
        out_gif = os.path.join(OUT_DIR, name + '.gif')
        g = graph + f';[{cur}]split[g1][g2];[g1]palettegen=max_colors=256:stats_mode=diff[p];[g2][p]paletteuse=dither=floyd_steinberg[gif]'
        sh(['ffmpeg', '-y', '-v', 'error', '-i', src, '-filter_complex', g, '-map', '[gif]', '-an', '-loop', '0', out_gif])
        print(f'OK {out_gif} {os.path.getsize(out_gif) // 1024}KB')

if __name__ == '__main__':
    try: main()
    except subprocess.CalledProcessError as e:
        print('FAIL', e, file=sys.stderr); sys.exit(1)
