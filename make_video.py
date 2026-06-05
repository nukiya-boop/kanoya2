#!/usr/bin/env python3
"""春日の森イメージ動画生成スクリプト"""

import os
import subprocess
import math

IMAGES_DIR = "images"
OUTPUT = "kasuga_mori.mp4"
W, H = 1920, 1080
FPS = 30
DURATION = 5       # 各画像の表示秒数
FADE = 1           # クロスフェード秒数
ZOOM_SPEED = 0.0003  # Ken Burns ズーム速度

images = sorted([
    f for f in os.listdir(IMAGES_DIR)
    if f.lower().endswith(".jpg")
])
print(f"画像数: {len(images)}")

frames_per_img = FPS * DURATION
fade_frames = FPS * FADE

# zoompan フィルタ: 画像ごとにゆっくりズームイン or ズームアウト交互
def zoompan_filter(i, w, h):
    # 縦画像は中央クロップして横に合わせる
    zoom_in = (i % 2 == 0)
    if zoom_in:
        zoom_expr = f"1+{ZOOM_SPEED}*in"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    else:
        zoom_expr = f"1.1-{ZOOM_SPEED}*in"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    return (
        f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,"
        f"crop={W*2}:{H*2},"
        f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}'"
        f":d={frames_per_img}:s={W}x{H}:fps={FPS},"
        f"setsar=1"
    )

# ffmpeg 入力とフィルタグラフ構築
inputs = []
for img in images:
    inputs += ["-loop", "1", "-t", str(DURATION + FADE), "-i", os.path.join(IMAGES_DIR, img)]

n = len(images)

filter_parts = []

# 各画像にzoompanとウォームカラーグレード適用
for i in range(n):
    w, h = (5760, 3840)  # fallback
    flt = zoompan_filter(i, w, h)
    # ウォームカラー（春っぽい暖色+明るさ）
    color_grade = (
        "eq=brightness=0.03:saturation=1.15:gamma_r=1.05:gamma_b=0.95,"
        "curves=r='0/0 0.5/0.55 1/1':g='0/0 0.5/0.52 1/1':b='0/0 0.5/0.47 1/1'"
    )
    filter_parts.append(f"[{i}:v]{flt},{color_grade}[v{i}]")

# xfade チェーン
# v0 xfade v1 → vx1, vx1 xfade v2 → vx2, ...
xfade_parts = []
offset = DURATION - FADE  # 最初のオフセット

prev = "v0"
for i in range(1, n):
    out = f"vx{i}"
    xfade_parts.append(
        f"[{prev}][v{i}]xfade=transition=fade:duration={FADE}:offset={offset}[{out}]"
    )
    prev = out
    offset += DURATION - FADE

filter_complex = ";".join(filter_parts) + ";" + ";".join(xfade_parts)
final_out = f"vx{n-1}"

cmd = (
    ["ffmpeg", "-y"]
    + inputs
    + [
        "-filter_complex", filter_complex,
        "-map", f"[{final_out}]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        OUTPUT,
    ]
)

print("動画生成開始...")
print(f"予想尺: {n * DURATION - (n-1) * FADE}秒")
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode == 0:
    size = os.path.getsize(OUTPUT) / 1024 / 1024
    print(f"完成: {OUTPUT} ({size:.1f} MB)")
else:
    print("エラー:", result.stderr[-3000:])
