#!/usr/bin/env python3
"""홈 카드용 16:9 썸네일. 그래프는 흰 배경에 여백을 두고 넣고, 2GB는 CAUCAFall 실제 사진 콜라주."""
from pathlib import Path
from PIL import Image, ImageChops

SITE = Path(__file__).resolve().parent.parent
IMG = SITE / "assets" / "img"
OUT = IMG / "thumbs"
W, H = 960, 540


def fit(src, name, pad=24):
    im = Image.open(src).convert("RGB")
    box = ImageChops.difference(im, Image.new("RGB", im.size, "white")).getbbox()
    if box:
        im = im.crop((max(box[0] - 10, 0), max(box[1] - 10, 0), min(box[2] + 10, im.width), min(box[3] + 10, im.height)))
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
# edge-deploy: 실제로 쓴 장비 사진(제조사 카탈로그에서 로고·제품명 없이 기기만 잘라냄) + 지연 그래프
def device_and_chart(dev, chart, name):
    bg = Image.new("RGB", (W, H), "white")
    d = Image.open(dev).convert("RGB")
    s = min(380 / d.width, 320 / d.height)
    d = d.resize((int(d.width * s), int(d.height * s)), Image.LANCZOS)
    bg.paste(d, (20 + (380 - d.width) // 2, (H - d.height) // 2))
    c = Image.open(chart).convert("RGB")
    c = c.crop(ImageChops.difference(c, Image.new("RGB", c.size, "white")).getbbox())
    s = min(530 / c.width, 470 / c.height)
    c = c.resize((int(c.width * s), int(c.height * s)), Image.LANCZOS)
    bg.paste(c, (410 + (540 - c.width) // 2, (H - c.height) // 2))
    bg.save(OUT / name, quality=92)


device_and_chart(IMG / "device" / "edge_box.png", IMG / "fig6_latency_trajectory.png", "edge-deploy.jpg")
collage(["fall_0403", "fall_0378", "fall_0317", "fall_0383"], "edge-vlm-2gb.jpg")
fit(IMG / "vlm_serving_load_curve.png", "vlm-serving.jpg")
fit(IMG / "fig_mlops1_pipeline.png", "mlops-retrain.jpg")
fit(IMG / "diagrams" / "senior-principles_2.png", "senior-principles.jpg")
# onvif-rag 썸네일은 실제 챗봇 화면 (assets/img/onvif/line.png 상단) — 아래 make_onvif_thumb 참고
# fit(IMG / "onvif_rag_score.png", "onvif-rag.jpg")
fit(IMG / "fire_lora_tradeoff.png", "fire-lora.jpg")
fit(IMG / "pm_flow.png", "pm-requirements.jpg")
print(sorted(p.name for p in OUT.iterdir()))
# ONVIF RAG: 공개 표준 질문에 답한 실제 챗봇 화면 상단. 위쪽 여백은 카드 배지 자리.
_bg = Image.new("RGB", (W, H), "#eef2f7")
_im = Image.open(IMG / "onvif" / "line.png").convert("RGB")
_im = _im.resize((W - 40, int(_im.height * (W - 40) / _im.width)), Image.LANCZOS).crop((0, 0, W - 40, H - 54))
_bg.paste(_im, (20, 54)); _bg.save(OUT / "onvif-rag.jpg", quality=90)
