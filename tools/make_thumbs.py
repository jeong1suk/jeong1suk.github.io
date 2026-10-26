#!/usr/bin/env python3
"""홈 카드용 16:9 썸네일. 그래프는 흰 배경에 여백을 두고 넣고, 2GB는 CAUCAFall 실제 사진 콜라주."""
from pathlib import Path
from PIL import Image

SITE = Path(__file__).resolve().parent.parent
IMG = SITE / "assets" / "img"
OUT = IMG / "thumbs"
W, H = 960, 540


def fit(src, name, pad=24):
    im = Image.open(src).convert("RGB")
    im.thumbnail((W - 2 * pad, H - 2 * pad), Image.LANCZOS)
    bg = Image.new("RGB", (W, H), "white")
    bg.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
    bg.save(OUT / name, quality=88)


def collage(ids, name):
    n = len(ids)
    tw = W // n
    bg = Image.new("RGB", (W, H), "black")
    for k, i in enumerate(ids):
        im = Image.open(IMG / "caucafall" / f"{i}.jpg").convert("RGB")
        r = max(tw / im.width, H / im.height)
        im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
        x0, y0 = (im.width - tw) // 2, (im.height - H) // 2
        bg.paste(im.crop((x0, y0, x0 + tw, y0 + H)), (k * tw, 0))
    bg.save(OUT / name, quality=88)


OUT.mkdir(parents=True, exist_ok=True)
fit(IMG / "fig6_latency_trajectory.png", "edge-deploy.jpg")
collage(["fall_0403", "fall_0378", "fall_0317", "fall_0383"], "edge-vlm-2gb.jpg")
fit(IMG / "vlm_serving_load_curve.png", "vlm-serving.jpg")
fit(IMG / "fig_mlops1_pipeline.png", "mlops-retrain.jpg")
print(sorted(p.name for p in OUT.iterdir()))
