#!/usr/bin/env python3
"""정적 사이트 빌드: src/ 마크다운 → 저장소 루트 HTML (GitHub Pages가 그대로 서빙).

사용:  .venv/bin/python build.py
- 원고는 src/ko/cases/*.md. 원고를 고치고 다시 빌드한다. 생성된 HTML은 직접 고치지 않는다.
- HTML 주석은 빌드 단계에서도 한 번 더 제거한다(공개 사이트라 페이지 소스에도 남으면 안 됨).
- 마지막에 금지어 검사(LEAK_PATTERNS)를 돌려 하나라도 걸리면 실패로 끝난다.
"""
import html
import re
import shutil
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src" / "ko"
OUT_CASES = ROOT / "cases"

SITE_TITLE = "정원석 · 포트폴리오"
GITHUB = "https://github.com/jeong1suk"

# 홈 카드 문구는 각 케이스 원고에 있는 사실만 옮긴다(새 수치를 만들지 않는다).
PROJECTS = [
    dict(slug="edge-deploy", group="main", period="2026.04",
         label="회사 프로젝트 · 코드 비공개",
         summary="8GB 공유 메모리에 2차 검증기를 추가할 수 있는지 판정한 기록. "
                 "입력을 줄여 1.8초를 300ms로 만들었고, 재현율은 끝내 측정하지 못했다."),
    dict(slug="edge-vlm-2gb", group="main", period="2026.10",
         label="개인 프로젝트 · 공개 데이터 · 코드 공개",
         summary="회사에서 남은 질문을 공개 데이터로 다시 풀었다. PyTorch FP16 2,810MB에서 "
                 "llama.cpp Q8_0 1,755MB로, 낙상 AUROC는 낮아지지 않았다(0.960)."),
    dict(slug="vlm-serving", group="main", period="2026.10",
         label="개인 프로젝트 · 공개 데이터",
         summary="2차 검증을 GPU 서버 한 대로 모으면 카메라 몇 대까지 감당하나. "
                 "처리량은 배칭이 바꿨고(초당 25건 → 95건), AWQ는 바꾸지 못했다."),
    dict(slug="mlops-retrain", group="main", period="2026.02~05",
         label="회사 프로젝트 · 코드 비공개",
         summary="설치 환경이 제각각인 카메라를 자동 재학습으로 따라가는 파이프라인. "
                 "구조를 네 번 갈아엎었고, 개선 폭은 측정하기 전에 중단됐다."),
    dict(slug="fire-lora", group="more", period="2026.10",
         label="개인 실험 · 회사 업무 데이터 사용 · 코드·데이터 비공개",
         summary="VLM에 화재 LoRA를 붙인 실험. 13/13 복구가 암기였음을 홀드아웃으로 드러냈고, "
                 "처음 보는 음성에서는 전부 무너졌다."),
]

LEAK_PATTERNS = [
    r"<!--", r"(?i)claude", r"\[확인", r"<계정>", r"C00_\d", r"review_(codex|gpt)",
    r"FIRE_LORA", r"/home/", r"Desktop", r"(?i)aimatix", r"에이아이매틱스",
    r"best_alpha", r"\.md\b",
]

CSS = """
:root { --fg:#1a202c; --muted:#5a6475; --line:#e2e8f0; --accent:#1f5fae; --bg-soft:#f6f8fb; }
* { box-sizing:border-box; }
body { margin:0; font-family:"Pretendard","Noto Sans KR","Noto Sans CJK KR","Apple SD Gothic Neo",sans-serif;
       color:var(--fg); line-height:1.7; font-size:16px; word-break:keep-all; }
.wrap { max-width:760px; margin:0 auto; padding:0 20px; }
header.site { border-bottom:1px solid var(--line); }
header.site .wrap { display:flex; justify-content:space-between; align-items:center; height:56px; }
header.site a { color:var(--fg); text-decoration:none; }
header.site nav a { margin-left:18px; color:var(--muted); font-size:15px; }
header.site nav a:hover { color:var(--accent); }
main { padding:40px 0 64px; }
h1 { font-size:28px; line-height:1.35; margin:0 0 12px; letter-spacing:-0.4px; }
h2 { font-size:19px; margin:44px 0 14px; padding-bottom:6px; border-bottom:2px solid var(--accent); }
a { color:var(--accent); }
blockquote { margin:18px 0; padding:10px 16px; border-left:3px solid #a0aec0; background:var(--bg-soft); color:#3b4352; }
blockquote p { margin:6px 0; }
sub { display:block; font-size:13.5px; color:var(--muted); line-height:1.6; margin-top:2px; vertical-align:baseline; }
article p { margin:14px 0; }
img { max-width:100%; height:auto; display:block; margin:20px auto; border:1px solid var(--line); }
hr { border:none; border-top:1px solid var(--line); margin:28px 0; }
code { background:#edf2f7; padding:1px 5px; border-radius:3px; font-size:14px; }
table { border-collapse:collapse; width:100%; font-size:14px; }
th, td { border:1px solid var(--line); padding:6px 9px; text-align:left; }
.badge { display:inline-block; font-size:12.5px; color:var(--accent); background:#eaf1fb;
         border-radius:4px; padding:1px 8px; margin-bottom:10px; }
.hero h1 { font-size:30px; }
.hero .lead { font-size:18px; color:#2d3748; margin:0 0 8px; }
.hero .sub { color:var(--muted); margin:0; }
.cards { display:grid; gap:14px; }
.card { display:block; border:1px solid var(--line); border-radius:8px; padding:16px 18px;
        text-decoration:none; color:var(--fg); transition:border-color .15s; }
.card:hover { border-color:var(--accent); }
.card .meta { font-size:13px; color:var(--muted); }
.card .title { font-weight:700; font-size:17px; margin:4px 0 6px; line-height:1.45; }
.card .summary { font-size:15px; color:#3b4352; margin:0; }
ul.principles { padding-left:20px; color:#3b4352; }
.back { font-size:14px; }
footer.site { border-top:1px solid var(--line); color:var(--muted); font-size:13px; padding:20px 0 40px; }
@media (max-width:600px) { h1, .hero h1 { font-size:24px; } body { font-size:15.5px; } }
"""


def page(title, body, desc=""):
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="stylesheet" href="/assets/style.css">
</head>
<body>
<header class="site"><div class="wrap">
  <a href="/"><strong>정원석</strong></a>
  <nav><a href="/#work">작업</a><a href="{GITHUB}">GitHub</a></nav>
</div></header>
<main><div class="wrap">
{body}
</div></main>
<footer class="site"><div class="wrap">
수치는 모두 측정 조건과 함께 적었습니다. 회사 프로젝트는 제품 구조·내부 경로·고객 정보를 빼고 정리했습니다.
</div></footer>
</body>
</html>
"""


def strip_comments(text):
    return re.sub(r"<!--.*?-->\s*", "", text, flags=re.S)


def render_case(p):
    raw = strip_comments((SRC / "cases" / f"{p['slug']}.md").read_text(encoding="utf-8"))
    m = re.search(r"^#\s+(.+)$", raw, flags=re.M)
    title = m.group(1).strip()
    raw = raw[:m.start()] + raw[m.end():]
    body_html = markdown.markdown(raw, extensions=["tables", "nl2br"])
    body = (f'<p class="back"><a href="/#work">← 작업 목록</a></p>\n'
            f'<article>\n<span class="badge">{html.escape(p["label"])}</span>\n'
            f'<h1>{html.escape(title)}</h1>\n{body_html}\n</article>')
    out = OUT_CASES / p["slug"] / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(f"{title} · 정원석", body, p["summary"]), encoding="utf-8")
    p["title"] = title
    return out


def card(p):
    return (f'<a class="card" href="/cases/{p["slug"]}/">'
            f'<div class="meta">{p["period"]} · {html.escape(p["label"])}</div>'
            f'<div class="title">{html.escape(p["title"])}</div>'
            f'<p class="summary">{html.escape(p["summary"])}</p></a>')


def render_index():
    main_cards = "\n".join(card(p) for p in PROJECTS if p["group"] == "main")
    more_cards = "\n".join(card(p) for p in PROJECTS if p["group"] == "more")
    body = f"""
<section class="hero">
<h1>VLM·비전 모델이 현장에서 왜 실패하는지 찾아내고, 되게 만드는 엔지니어</h1>
<p class="lead">오프라인에서 좋아 보이던 모델이 실제 환경에서 무너지는 지점을 측정으로 찾고,
프롬프트·입력·모델 선택·평가 기준을 바꿔 되돌립니다.</p>
<p class="sub">판정 기준을 먼저 세우고, 증명하지 못한 것을 함께 남기는 방식으로 일합니다.</p>
</section>

<h2>이 기록이 지키는 것</h2>
<ul class="principles">
<li>모든 수치에 측정 조건을 붙입니다. 조건이 빠진 숫자는 결과로 쓰지 않습니다.</li>
<li>각 프로젝트의 마지막 항목은 증명하지 못한 것입니다.</li>
<li>회사 프로젝트는 제품 아키텍처·내부 경로·고객 정보를 빼고 정리했습니다. 상세판은 요청하시면 보내드립니다.</li>
</ul>

<h2 id="work">대표 작업</h2>
<div class="cards">
{main_cards}
</div>

<h2>그 밖의 실험</h2>
<div class="cards">
{more_cards}
</div>
"""
    out = ROOT / "index.html"
    out.write_text(page(SITE_TITLE, body,
                        "VLM·비전 모델을 현장에서 되게 만드는 엔지니어 정원석의 포트폴리오"),
                   encoding="utf-8")
    return out


def leak_check(paths):
    bad = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for pat in LEAK_PATTERNS:
            for m in re.finditer(pat, text):
                line = text.count("\n", 0, m.start()) + 1
                bad.append(f"{path.relative_to(ROOT)}:{line}: '{m.group(0)}'")
    return bad


def main():
    if OUT_CASES.exists():
        shutil.rmtree(OUT_CASES)
    (ROOT / "assets" / "style.css").write_text(CSS.lstrip(), encoding="utf-8")
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")
    outputs = [render_case(p) for p in PROJECTS]
    outputs.append(render_index())
    sources = list((ROOT / "src").rglob("*.md"))
    bad = leak_check(outputs + sources)
    for o in outputs:
        print("built", o.relative_to(ROOT))
    if bad:
        print("\n금지어 검사 실패:")
        print("\n".join(bad))
        sys.exit(1)
    print("금지어 검사 통과 (HTML %d개 + 원고 %d개)" % (len(outputs), len(sources)))


if __name__ == "__main__":
    main()
