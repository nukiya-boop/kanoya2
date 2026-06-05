#!/usr/bin/env python3
"""春日の森イメージ動画生成 v2"""

import os
import subprocess
import tempfile

IMAGES_DIR = "images"
OUTPUT = "kasuga_mori_final.mp4"
W, H = 1920, 1080
FPS = 30
DURATION = 5       # 各画像の表示秒数
FADE = 1           # クロスフェード秒数

images = sorted([f for f in os.listdir(IMAGES_DIR) if f.lower().endswith(".jpg")])
print(f"画像数: {len(images)}")

tmpdir = tempfile.mkdtemp()
clips = []

# 各画像を個別クリップとして書き出す
for i, img in enumerate(images):
    path = os.path.join(IMAGES_DIR, img)
    out = os.path.join(tmpdir, f"clip_{i:02d}.mp4")
    clips.append(out)

    zoom_in = (i % 2 == 0)
    total_frames = FPS * (DURATION + FADE)  # xfadeのオーバーラップ分含む

    # スケール: 横長基準で少し大きめにリサイズしてクロップ
    scale_filter = (
        f"scale={int(W*1.08)}:{int(H*1.08)}:force_original_aspect_ratio=increase,"
        f"crop={int(W*1.08)}:{int(H*1.08)},"
        f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
        f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black"
    )

    # ズームエフェクト: scaleとcropで疑似Ken Burns
    if zoom_in:
        # 1.08→1.0 ズームアウト
        vf = (
            f"{scale_filter},"
            f"zoompan=z='1.08-0.08*in/{total_frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={total_frames}:s={W}x{H}:fps={FPS}"
        )
    else:
        # 1.0→1.08 ズームイン
        vf = (
            f"{scale_filter},"
            f"zoompan=z='1+0.08*in/{total_frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={total_frames}:s={W}x{H}:fps={FPS}"
        )

    # ウォームカラー
    vf += ",eq=brightness=0.03:saturation=1.15:gamma_r=1.04:gamma_b=0.96"
    vf += ",setsar=1"

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
    print(f"[{i+1}/{len(images)}] {img} 処理中...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("エラー:", r.stderr[-1000:])
        exit(1)

print("クリップ結合中...")

# xfadeで結合
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

final_label = f"x{n-1}"
filter_complex = ";".join(filter_parts)

cmd = (
    ["ffmpeg", "-y"]
    + inputs
    + [
        "-filter_complex", filter_complex,
        "-map", f"[{final_label}]",
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

# クリーンアップ
import shutil
shutil.rmtree(tmpdir)
