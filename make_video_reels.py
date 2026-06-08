#!/usr/bin/env python3
"""Instagram Reels 1080x1920 — 元解像度処理版"""

import os
import subprocess
import tempfile
from PIL import Image

IMAGES_DIR = "images"
OUTPUT = "kasuga_mori_reels_hq.mp4"
W, H = 1080, 1920
FPS = 30
DURATION = 3.5
FADE = 0.8
FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"

images = sorted([f for f in os.listdir(IMAGES_DIR) if f.lower().endswith(".jpg")])

captions = [
    "静かな時が、ここに流れる",
    "苔むす庭に、季節が宿る",
    "竹垣に守られた、小さな宇宙",
    "木漏れ日が、そっと語りかける",
    "移ろいゆく季節を、ただ感じる",
    "自然の息吹に、寄り添う宿",
    "夜は静かに、森に抱かれて",
    "光と影が奏でる、安らぎの夜",
    "ここにしかない、時間がある",
    "春日の森に佇む、特別な時間",
    "新緑の風と共に、旅はじまる",
]

tmpdir = tempfile.mkdtemp()
clips = []
total_frames = int(FPS * (DURATION + FADE))
text_fadein_end = FPS * 0.6
text_fadeout_start = FPS * 3.0

for i, (img, caption) in enumerate(zip(images, captions)):
    path = os.path.join(IMAGES_DIR, img)
    out = os.path.join(tmpdir, f"clip_{i:02d}.mp4")
    clips.append(out)

    iw, ih = Image.open(path).size
    is_portrait = ih > iw

    # ぼかし背景: 1080x1920にクロップ拡大+ブラー
    bg_filter = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},"
        f"gblur=sigma=40,"
        f"eq=brightness=-0.1:saturation=0.7"
    )

    # 前景: アスペクト比維持で最大サイズにフィット
    if is_portrait:
        # 縦長: 幅1080に合わせる（高さが1920を超えないように）
        scale_w = W
        scale_h = int(ih * W / iw)
        if scale_h > H:
            scale_h = H
            scale_w = int(iw * H / ih)
        fg_scale = f"scale={scale_w}:{scale_h}"
    else:
        # 横長: 幅1080に合わせる
        scale_w = W
        scale_h = int(ih * W / iw)
        fg_scale = f"scale={scale_w}:{scale_h}"

    # ズーム方向交互（Ken Burns風・軽め）
    zoom_in = (i % 2 == 0)
    zoom_dir = "in" if zoom_in else "out"
    z_start = 1.0 if zoom_in else 1.05
    z_end   = 1.05 if zoom_in else 1.0
    z_expr  = f"{z_start}+({z_end}-{z_start})*in/{total_frames}"

    fg_filter = (
        f"{fg_scale},"
        f"zoompan=z='{z_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={total_frames}:s={scale_w}x{scale_h}:fps={FPS}"
    )

    # テロップ
    alpha_expr = (
        f"if(lt(n,{text_fadein_end}),n/{text_fadein_end},"
        f"if(lt(n,{text_fadeout_start}),1,"
        f"({total_frames}-n)/({total_frames}-{text_fadeout_start})))"
    )
    drawtext = (
        f"drawtext=fontfile={FONT}:text='{caption}':"
        f"fontsize=52:fontcolor=white@1.0:"
        f"x=(w-text_w)/2:y=h-200:"
        f"shadowcolor=black@0.8:shadowx=2:shadowy=2:"
        f"alpha='{alpha_expr}'"
    )

    fc = (
        f"[0:v]split[bg0][fg0];"
        f"[bg0]{bg_filter}[bg];"
        f"[fg0]{fg_filter}[fgz];"
        f"[bg][fgz]overlay=x=(W-w)/2:y=(H-h)/2[ov];"
        f"[ov]eq=saturation=1.15:gamma_r=1.04:gamma_b=0.96,"
        f"setsar=1,{drawtext}[out]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", path,
        "-filter_complex", fc,
        "-map", "[out]",
        "-t", str(DURATION + FADE),
        "-r", str(FPS),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        out
    ]
    print(f"[{i+1}/{len(images)}] {img} ({iw}x{ih}) → 「{caption}」")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("エラー:", r.stderr[-2000:])
        exit(1)

print("クリップ結合中...")
n = len(clips)
inputs = []
for c in clips:
    inputs += ["-i", c]

filter_parts = []
prev = "0:v"
offset = DURATION - FADE
for i in range(1, n):
    out_label = f"x{i}"
    filter_parts.append(
        f"[{prev}][{i}:v]xfade=transition=fade:duration={FADE}:offset={offset}[{out_label}]"
    )
    prev = out_label
    offset += DURATION - FADE

cmd = (
    ["ffmpeg", "-y"]
    + inputs
    + [
        "-filter_complex", ";".join(filter_parts),
        "-map", f"[x{n-1}]",
        "-c:v", "libx264", "-profile:v", "baseline", "-level", "4.0",
        "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        OUTPUT,
    ]
)
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode == 0:
    size = os.path.getsize(OUTPUT) / 1024 / 1024
    print(f"完成: {OUTPUT} ({size:.1f} MB)")
else:
    print("結合エラー:", r.stderr[-2000:])

import shutil
shutil.rmtree(tmpdir)
