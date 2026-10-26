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
    dict(slug="edge-deploy",
         figs={0: ["fig8_cascade"], 1: ["fig2_memory_budget"], 2: ["fig1_memory_timeline"], 3: ["fig5_score_separation"], 4: ["fig4_prompt_generations", "fig3_threshold_sweep"], 5: ["fig7_decode_refutation", "fig7b_splitting_lever"], 6: ["fig6_latency_trajectory"]},
         stat="1.8초 → 300ms", stat_cap="VLM 2차 검증 지연 · 정확도는 떨어지지 않음(21장)", group="main", period="2026.04",
         label="회사 프로젝트 · 코드 비공개",
         summary="8GB 공유 메모리에 2차 검증기를 추가할 수 있는지 판정한 기록. "
                 "입력을 줄여 1.8초를 300ms로 만들었고, 재현율은 끝내 측정하지 못했다."),
    dict(slug="edge-vlm-2gb",
         figs={5: ["gallery:small-model"], 6: ["gallery:ir"]},
         stat="2,810 → 1,755MB", stat_cap="PyTorch FP16 → llama.cpp Q8_0 · 낙상 AUROC 0.960", group="main", period="2026.10",
         label="개인 프로젝트 · 공개 데이터 · 코드 공개",
         summary="회사에서 남은 질문을 공개 데이터로 다시 풀었다. PyTorch FP16 2,810MB에서 "
                 "llama.cpp Q8_0 1,755MB로, 낙상 AUROC는 낮아지지 않았다(0.960)."),
    dict(slug="vlm-serving",
         stat="25 → 95건/초", stat_cap="HF batch 1 → vLLM 연속 배칭 · 같은 GPU", group="main", period="2026.10",
         label="개인 프로젝트 · 공개 데이터",
         summary="2차 검증을 GPU 서버 한 대로 모으면 카메라 몇 대까지 감당하나. "
                 "처리량은 배칭이 바꿨고(초당 25건 → 95건), AWQ는 바꾸지 못했다."),
    dict(slug="mlops-retrain",
         figs={0: ["fig_mlops1_pipeline"], 4: ["fig_mlops2_states"], 6: ["fig_mlops3_threshold"]},
         stat="구조 4회 전환", stat_cap="v0.1 직렬 → v2.0 배포 후 평가", group="main", period="2026.02~05",
         label="회사 프로젝트 · 코드 비공개",
         summary="설치 환경이 제각각인 카메라를 자동 재학습으로 따라가는 파이프라인. "
                 "구조를 네 번 갈아엎었고, 개선 폭은 측정하기 전에 중단됐다."),
    dict(slug="fire-lora",
         stat="88/88 오탐", stat_cap="처음 보는 카메라의 음성이 전부 Yes (3 epoch)", group="more", period="2026.10",
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

strong { background:linear-gradient(transparent 62%, #fde68a 62%); font-weight:700; }
.card strong, .toc strong, h3 strong, header.site strong { background:none; }
.tags { margin:6px 0 0; }
.tag { display:inline-block; font-size:12px; color:#3b4352; background:#eef1f5; border-radius:999px;
       padding:2px 9px; margin:0 6px 6px 0; }
.statline { display:flex; align-items:baseline; gap:12px; flex-wrap:wrap; margin:18px 0 6px;
            padding:14px 18px; background:var(--bg-soft); border-radius:8px; }
.stat { font-size:26px; font-weight:800; color:var(--accent); letter-spacing:-0.5px; white-space:nowrap; }
.cap { font-size:13.5px; color:var(--muted); }
.toc { border:1px solid var(--line); border-radius:8px; padding:14px 18px 6px; margin:24px 0 32px; }
.toc-h { font-weight:700; font-size:14px; color:var(--muted); margin-bottom:6px; }
.toc ol { margin:0; padding-left:22px; }
.toc li { margin:0 0 8px; font-size:15px; }
.toc a { color:var(--fg); text-decoration:none; }
.toc a:hover { color:var(--accent); }
.item { display:flex; gap:16px; padding:22px 0; border-top:1px solid var(--line); scroll-margin-top:16px; }
.num { flex:0 0 34px; height:34px; border-radius:50%; background:var(--accent); color:#fff;
       font-weight:700; display:flex; align-items:center; justify-content:center; font-size:15px; }
.ibody { flex:1; min-width:0; }
.ibody h3 { margin:3px 0 8px; font-size:18px; line-height:1.45; }
.ibody p { margin:8px 0; }
figure { margin:14px 0; } figure img { margin:0 auto; border-radius:6px; cursor:zoom-in; }
.gallery { margin:16px 0; padding:14px; border:1px solid var(--line); border-radius:8px; background:#fff; }
.gtitle { font-weight:700; font-size:14.5px; margin-bottom:10px; }
.tiles { display:grid; grid-template-columns:repeat(auto-fill, minmax(140px, 1fr)); gap:10px; }
.tile img { width:100%; aspect-ratio:248/360; object-fit:cover; margin:0; border-radius:6px; }
.tcap { font-size:12.5px; line-height:1.5; margin-top:4px; color:#3b4352; }
.tcap .tt { font-weight:700; color:var(--fg); }
.yes { color:#c53030; } .no { color:#2f855a; }
.gfoot { font-size:13px; color:#3b4352; margin:10px 0 2px; }
.credit { font-size:11.5px; color:var(--muted); margin:2px 0 0; }
details { margin-top:10px; font-size:14px; color:var(--muted); }
summary { cursor:pointer; color:var(--accent); font-size:13.5px; user-select:none; }
details p { margin:8px 0 0; padding:10px 12px; background:var(--bg-soft); border-radius:6px; line-height:1.65; }
.tailnote { border-top:1px solid var(--line); margin-top:8px; padding-top:14px; font-size:13.5px; color:var(--muted); }
.intro > p > sub { display:block; padding:8px 12px; background:#f0f5fc; border-radius:6px; color:#2d3748; }
.card { display:flex; gap:18px; align-items:stretch; }
.cstat { flex:0 0 170px; border-right:1px solid var(--line); padding-right:14px; display:flex;
         flex-direction:column; justify-content:center; }
.cstat .stat { font-size:21px; white-space:normal; line-height:1.25; }
.cstat .cap { margin-top:6px; font-size:12.5px; line-height:1.5; }
.cmain { flex:1; min-width:0; }
.flow { display:flex; align-items:stretch; gap:8px; margin:0 0 18px; }
.flow .step { flex:1; background:var(--bg-soft); border-radius:8px; padding:10px 12px; font-size:14px; line-height:1.5; }
.flow .who { display:block; font-size:12px; font-weight:700; color:var(--accent); margin-bottom:2px; }
.flow .arrow { align-self:center; color:var(--muted); }
@media (max-width:600px) {
  h1, .hero h1 { font-size:24px; } body { font-size:15.5px; }
  .card { flex-direction:column; gap:10px; }
  .cstat { flex:none; border-right:none; border-bottom:1px solid var(--line); padding:0 0 10px; }
  .flow { flex-direction:column; } .flow .arrow { transform:rotate(90deg); }
  .item { gap:12px; } .num { flex-basis:28px; height:28px; font-size:13px; }
}
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


def md(text):
    return markdown.markdown(text.strip(), extensions=["tables", "nl2br"])


ITEM_RE = re.compile(r"^\*\*(\d+)\.\s*(.+?)\*\*[ \t]*\n(.*?)(?=^\*\*\d+\.|^---[ \t]*$|\Z)", re.M | re.S)


def split_case(raw):
    """카드 원고 → 제목 / 태그 / 도입부 / 항목 8개 / 꼬리말. 문장은 바꾸지 않는다."""
    m = re.search(r"^#\s+(.+)$", raw, flags=re.M)
    title = m.group(1).strip()
    raw = raw[m.end():]
    tags = []
    h = re.search(r"^\*\*정원석\*\*\s*\|\s*(.+)$", raw, flags=re.M)
    if h:
        tags = [t.strip() for t in h.group(1).split(" · ") if t.strip()]
        raw = raw[:h.start()] + raw[h.end():]
    items = list(ITEM_RE.finditer(raw))
    intro = raw[:items[0].start()]
    intro = re.sub(r"^---[ \t]*$", "", intro, flags=re.M)
    tail = raw[items[-1].end():]
    tail = re.sub(r"^---[ \t]*$", "", tail, flags=re.M)
    parsed = []
    for it in items:
        body = it.group(3)
        subs = re.findall(r"<sub>(.*?)</sub>", body, flags=re.S)
        body = re.sub(r"<sub>.*?</sub>", "", body, flags=re.S)
        parsed.append(dict(n=it.group(1), head=it.group(2).strip(), body=body, notes=subs))
    return title, tags, intro, parsed, tail


def fig_html(names):
    out = []
    for n in names:
        if n.startswith("gallery:"):
            out.append((SRC / "galleries" / f"{n[8:]}.html").read_text(encoding="utf-8"))
        else:
            out.append(_fig(n))
    return "".join(out)


def _fig(n):
    return "".join(f'<figure><a href="/assets/img/{n}.png" target="_blank">'
                   f'<img src="/assets/img/{n}.png" loading="lazy" alt="{n}"></a></figure>' for n in [n])


def render_case(p):
    raw = strip_comments((SRC / "cases" / f"{p['slug']}.md").read_text(encoding="utf-8"))
    title, tags, intro, items, tail = split_case(raw)
    tag_html = "".join(f'<span class="tag">{html.escape(t)}</span>' for t in tags)
    toc = "\n".join(f'<li><a href="#s{i["n"]}">{md(i["head"])[3:-4]}</a></li>' for i in items)
    blocks = []
    for i in items:
        notes = ""
        if i["notes"]:
            notes = ('<details><summary>측정 조건</summary>'
                     + "".join(f"<p>{n.strip()}</p>" for n in i["notes"]) + "</details>")
        blocks.append(f'<section class="item" id="s{i["n"]}"><div class="num">{i["n"]}</div>'
                      f'<div class="ibody"><h3>{md(i["head"])[3:-4]}</h3>{md(i["body"])}'
                      f'{fig_html(p.get("figs", {}).get(int(i["n"]), []))}{notes}</div></section>')
    tail_html = md(tail.replace("<sub>", "").replace("</sub>", ""))
    body = f"""<p class="back"><a href="/#work">← 작업 목록</a></p>
<article>
<span class="badge">{html.escape(p["label"])}</span>
<h1>{html.escape(title)}</h1>
<div class="tags">{tag_html}</div>
<div class="statline"><span class="stat">{html.escape(p["stat"])}</span><span class="cap">{html.escape(p["stat_cap"])}</span></div>
<div class="intro">{md(intro)}{fig_html(p.get("figs", {}).get(0, []))}</div>
<nav class="toc"><div class="toc-h">한눈에 보기</div><ol>
{toc}
</ol></nav>
{"".join(blocks)}
<div class="tailnote">{tail_html}</div>
</article>"""
    out = OUT_CASES / p["slug"] / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(f"{title} · 정원석", body, p["summary"]), encoding="utf-8")
    p["title"] = title
    p["tags"] = tags
    return out


def card(p):
    tags = [t for t in p["tags"] if not re.match(r"^\d{4}\.", t) and t != "개인 프로젝트"][:4]
    tag_html = "".join(f'<span class="tag">{html.escape(t)}</span>' for t in tags)
    return (f'<a class="card" href="/cases/{p["slug"]}/">'
            f'<div class="cstat"><div class="stat">{html.escape(p["stat"])}</div>'
            f'<div class="cap">{html.escape(p["stat_cap"])}</div></div>'
            f'<div class="cmain"><div class="meta">{p["period"]} · {html.escape(p["label"])}</div>'
            f'<div class="title">{html.escape(p["title"])}</div>'
            f'<p class="summary">{html.escape(p["summary"])}</p>'
            f'<div class="tags">{tag_html}</div></div></a>')


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
<div class="flow">
  <div class="step"><span class="who">회사</span>8GB 기기에 2차 검증기를 올릴 수 있나</div>
  <div class="arrow">→</div>
  <div class="step"><span class="who">개인</span>2GB 안에서 상시로 돌리려면</div>
  <div class="arrow">→</div>
  <div class="step"><span class="who">개인</span>서버로 모으면 카메라 몇 대까지</div>
</div>
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
