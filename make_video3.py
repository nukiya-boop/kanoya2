#!/usr/bin/env python3
"""春日の森イメージ動画 v3 — テロップ入り"""

import os
import subprocess
import tempfile

IMAGES_DIR = "images"
OUTPUT = "kasuga_mori_caption.mp4"
W, H = 1280, 720
FPS = 30
DURATION = 5
FADE = 1
FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"

images = sorted([f for f in os.listdir(IMAGES_DIR) if f.lower().endswith(".jpg")])

# 各画像に対応するテロップ
captions = [
    "静かな時が、ここに流れる",          # 7C1A4163 客室リビング
    "苔むす庭に、季節が宿る",             # 7C1A4164 坪庭正面
    "竹垣に守られた、小さな宇宙",         # 7C1A4165 坪庭俯瞰
    "木漏れ日が、そっと語りかける",        # 7C1A4167 春の木漏れ日
    "移ろいゆく季節を、ただ感じる",        # 7C1A4169 紅葉と苔
    "自然の息吹に、寄り添う宿",           # 7C1A4170 石と砂利
    "夜は静かに、森に抱かれて",           # 7C1A4182 ベッドルーム
    "光と影が奏でる、安らぎの夜",          # 7C1A4184 間接照明
    "奈良春日　鹿のや",                  # 7C1A4282 看板
    "春日の森に佇む、特別な時間",          # 7C1A4317 外観
    "新緑の風と共に、旅はじまる",          # 7C1A4337修 モミジ越し
]

tmpdir = tempfile.mkdtemp()
clips = []

total_frames = FPS * (DURATION + FADE)
# テロップのフェードイン/アウトタイミング
text_fadein_end = FPS * 1.0    # 1秒でフェードイン完了
text_fadeout_start = FPS * 4.5 # 4.5秒からフェードアウト開始

for i, (img, caption) in enumerate(zip(images, captions)):
    path = os.path.join(IMAGES_DIR, img)
    out = os.path.join(tmpdir, f"clip_{i:02d}.mp4")
    clips.append(out)

    zoom_in = (i % 2 == 0)

    scale_filter = (
        f"scale={int(W*1.08)}:{int(H*1.08)}:force_original_aspect_ratio=increase,"
        f"crop={int(W*1.08)}:{int(H*1.08)},"
        f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
        f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black"
    )

    if zoom_in:
        zoom_expr = f"1.08-0.08*in/{total_frames}"
    else:
        zoom_expr = f"1+0.08*in/{total_frames}"

    vf = (
        f"{scale_filter},"
        f"zoompan=z='{zoom_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={total_frames}:s={W}x{H}:fps={FPS},"
        f"eq=brightness=0.03:saturation=1.15:gamma_r=1.04:gamma_b=0.96,"
        f"setsar=1"
    )

    # テロップ: フェードイン/アウト付き、下部中央
    font_size = 38
    text_y = H - 120
    # アルファ: 0→1 (0~text_fadein_end), 1 (text_fadein_end~text_fadeout_start), 1→0 (text_fadeout_start~total_frames)
    alpha_expr = (
        f"if(lt(n,{text_fadein_end}), n/{text_fadein_end},"
        f"if(lt(n,{text_fadeout_start}), 1,"
        f"({total_frames}-n)/({total_frames}-{text_fadeout_start})))"
    )

    drawtext = (
        f"drawtext=fontfile={FONT}:text='{caption}':"
        f"fontsize={font_size}:fontcolor=white@1.0:"
        f"x=(w-text_w)/2:y={text_y}:"
        f"shadowcolor=black@0.7:shadowx=2:shadowy=2:"
        f"alpha='{alpha_expr}'"
    )

    vf += f",{drawtext}"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", path,
        "-vf", vf,
        "-t", str(DURATION + FADE),
        "-r", str(FPS),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        out
    ]
    print(f"[{i+1}/{len(images)}] {img} → 「{caption}」")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("エラー:", r.stderr[-1000:])
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

filter_complex = ";".join(filter_parts)

cmd = (
    ["ffmpeg", "-y"]
    + inputs
    + [
        "-filter_complex", filter_complex,
        "-map", f"[x{n-1}]",
        "-c:v", "libx264", "-profile:v", "baseline", "-level", "3.1",
        "-preset", "medium", "-crf", "22",
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
