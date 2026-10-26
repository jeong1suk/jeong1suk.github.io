#!/usr/bin/env python3
"""CAUCAFall 실패 사례 갤러리 생성.

점수는 ~/vlm-edge-quant-bench/results/*/scores.jsonl 에서 직접 읽는다(손으로 옮겨 적지 않는다).
출력: assets/img/caucafall/*.jpg, src/ko/galleries/{small-model,ir}.html
CAUCAFall은 CC BY 4.0 — 출처·라이선스·변경 사항(크롭·축소)을 갤러리마다 표기한다.
"""
import html
import json
from pathlib import Path

from PIL import Image

BENCH = Path.home() / "vlm-edge-quant-bench"
SITE = Path(__file__).resolve().parent.parent
IMG_OUT = SITE / "assets" / "img" / "caucafall"
FRAG_OUT = SITE / "src" / "ko" / "galleries"
T = 0.55  # 회사에서 고정해 쓰던 운영 threshold (DECISIONS D-07)

ACT = {"sit_down": "앉기", "kneel": "무릎 꿇기", "pickup": "물건 줍기"}
CREDIT = ('<p class="credit">사진: <a href="https://data.mendeley.com/datasets/7w7fccy7ky">CAUCAFall</a> '
          '(Universidad del Cauca), <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. '
          '모델 입력과 같은 사람 영역 크롭을 축소해 실었다. 얼굴 흐림은 원본 데이터셋 처리.</p>')

man = {d["id"]: d for d in map(json.loads, open(BENCH / "data/fall/manifest.jsonl"))}


def scores(run):
    return {d["id"]: d["score"] for d in map(json.loads, open(BENCH / f"results/{run}/scores.jsonl"))
            if d["task"] == "fall"}


S500, S256 = scores("fp16"), scores("fp16_256m")


def verdict(s):
    return '<b class="yes">쓰러짐</b>' if s >= T else '<b class="no">정상</b>'


def tile(i, rows, note=""):
    IMG_OUT.mkdir(parents=True, exist_ok=True)
    Image.open(BENCH / f"data/fall/crops/{i}.png").convert("RGB").save(IMG_OUT / f"{i}.jpg", quality=85)
    d = man[i]
    lines = "".join(f"<div>{label} {s:.2f} → {verdict(s)}</div>" for label, s in rows)
    return (f'<div class="tile"><img src="/assets/img/caucafall/{i}.jpg" loading="lazy" alt="{ACT[d["activity"]]}">'
            f'<div class="tcap"><div class="tt">{ACT[d["activity"]]} · 참가자 {d["subject"]}{note}</div>'
            f'{lines}</div></div>')


def gallery(title, tiles, foot):
    return (f'<div class="gallery"><div class="gtitle">{html.escape(title)}</div>'
            f'<div class="tiles">{"".join(tiles)}</div><p class="gfoot">{foot}</p>{CREDIT}</div>')


def main():
    FRAG_OUT.mkdir(parents=True, exist_ok=True)
    # 5번: 작은 모델이 쪼그려 앉기를 쓰러짐으로 본 사례 (정답: 모두 정상)
    sq = [i for i, d in man.items() if d["group"] == "squatting"]
    rate256 = sum(S256[i] >= T for i in sq) / len(sq)
    rate500 = sum(S500[i] >= T for i in sq) / len(sq)
    g1 = gallery("정답은 모두 '정상'. 같은 사진, 다른 모델 크기",
                 [tile(i, [("256M", S256[i]), ("500M", S500[i])]) for i in ["fall_0403", "fall_0317", "fall_0447"]],
                 f"쪼그려 앉기 {len(sq)}장 중 쓰러짐 판정: 256M {rate256:.0%}, 500M {rate500:.0%} "
                 f"(FP16, threshold {T}). 사진은 두 모델의 점수 차이가 큰 사례에서 골랐다.")
    (FRAG_OUT / "small-model.html").write_text(g1, encoding="utf-8")

    # 6번: 같은 동작, 흑백(IR) 대 컬러 (정답: 모두 정상, 500M FP16)
    neg = [i for i, d in man.items() if d["gt"] == 0]
    ir = [i for i in neg if man[i]["subject"] in (6, 8)]
    col = [i for i in neg if man[i]["subject"] not in (6, 8)]
    fpr = lambda ids: sum(S500[i] >= T for i in ids) / len(ids)
    g2 = gallery("정답은 모두 '정상'. 같은 동작, 흑백(IR)과 컬러",
                 [tile("fall_0378", [("500M", S500["fall_0378"])], " · 흑백"),
                  tile("fall_0383", [("500M", S500["fall_0383"])], " · 컬러"),
                  tile("fall_0325", [("500M", S500["fall_0325"])], " · 흑백"),
                  tile("fall_0343", [("500M", S500["fall_0343"])], " · 컬러")],
                 f"음성 오탐률(500M FP16, threshold {T}): 흑백 {fpr(ir):.3f}({len(ir)}장) · "
                 f"컬러 {fpr(col):.3f}({len(col)}장). 흑백 참가자는 2명뿐이라 개인 차이와 완전히 분리하지 못했다. 사진은 판정이 갈린 사례에서 골랐다.")
    (FRAG_OUT / "ir.html").write_text(g2, encoding="utf-8")
    print("ok", rate256, rate500, fpr(ir), fpr(col))


if __name__ == "__main__":
    main()
