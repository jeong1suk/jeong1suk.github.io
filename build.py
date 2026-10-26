#!/usr/bin/env python3
"""정적 사이트 빌드: src/ 마크다운 → 저장소 루트 HTML (GitHub Pages가 그대로 서빙).

사용:  .venv/bin/python build.py
- 원고는 src/ko/cases/*.md. 원고를 고치고 다시 빌드한다. 생성된 HTML은 직접 고치지 않는다.
- 썸네일: tools/make_thumbs.py / CAUCAFall 갤러리: tools/make_caucafall_gallery.py
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
GITHUB = "https://github.com/jeong1suk"

# 홈 카드의 수치·요약은 각 케이스 원고에 있는 사실만 옮긴다(새 수치를 만들지 않는다).
# hook = 카드 제목(궁금증을 만드는 질문). 원고 제목은 상세 페이지에서 쓴다.
PROJECTS = [
    dict(slug="edge-deploy", group="main", period="2026.04", accent="#4f46e5",
         kind="회사 프로젝트", label="회사 프로젝트 · 코드 비공개",
         hook="빠른 모델이 왜 탈락했나",
         stat="1.8초 → 300ms", stat_cap="VLM 2차 검증 지연",
         summary="8GB 공유 메모리에 2차 검증기를 추가할 수 있는지 판정했다. "
                 "25ms짜리 경량 모델은 쓰러짐과 앉음을 0.02 차이로밖에 구분하지 못했다.",
         figs={0: ["fig8_cascade"], 1: ["fig2_memory_budget"], 2: ["fig1_memory_timeline"],
               3: ["fig5_score_separation"], 4: ["fig4_prompt_generations", "fig3_threshold_sweep"],
               5: ["fig7_decode_refutation", "fig7b_splitting_lever"], 6: ["fig6_latency_trajectory"]}),
    dict(slug="edge-vlm-2gb", group="main", period="2026.10", accent="#0d9488",
         kind="업무 연장 연구", label="업무 연장 자체 연구 · 공개 데이터 · 코드 공개",
         hook="4bit로 줄여도 안 들어갔다. 그럼 뭘 줄여야 하나",
         stat="2,810 → 1,755MB", stat_cap="낙상 AUROC 0.960 유지",
         summary="회사에서 남은 질문을 공개 데이터로 다시 풀었다. 양자화보다 런타임 교체가 컸고, "
                 "오탐은 모델보다 흑백(IR) 영상에서 났다.",
         figs={5: ["gallery:small-model"], 6: ["gallery:ir"]}),
    dict(slug="vlm-serving", group="main", period="2026.10", accent="#2563eb",
         kind="업무 연장 연구", label="업무 연장 자체 연구 · 공개 데이터",
         hook="GPU 한 장으로 카메라 몇 대까지 버티나",
         stat="25 → 95건/초", stat_cap="같은 GPU, 배칭만 바꿔서",
         summary="2차 검증을 서버 한 대로 모았다. 처리량은 배칭이 바꿨고 AWQ는 바꾸지 못했다. "
                 "모델 교체는 61.5초 중단이었다."),
    dict(slug="mlops-retrain", group="main", period="2026.02~05", accent="#7c3aed",
         kind="회사 프로젝트", label="회사 프로젝트 · 단독 설계·구현 · 코드 비공개",
         hook="현장마다 다르게 틀리는 모델, 사람 없이 고칠 수 있나",
         stat="구조 4회 전환", stat_cap="수집부터 배포·평가까지 단독",
         summary="카메라 환경별 자동 재학습 파이프라인. 구조를 네 번 갈아엎었고, "
                 "미탐률 이상의 원인은 모델이 아니라 펌웨어였다.",
         figs={0: ["fig_mlops1_pipeline"], 4: ["fig_mlops2_states"], 6: ["fig_mlops3_threshold"]}),
    dict(slug="senior-principles", group="more", period="2026.04~05", accent="#0f766e",
         kind="AI 도구", label="회사 프로젝트 · 단독 개발 · 코드 비공개",
         hook="AI 에이전트의 \"완료했습니다\"를 믿을 수 있나",
         stat="이전 수치 철회", stat_cap="측정 파이프라인 결함을 스스로 발견",
         summary="14개 도메인의 시니어 판단 원칙을 Claude Code 플러그인으로 만들어 카메라·VMS 연동 시스템 개발에 실제로 썼고, 함정 시나리오 64종으로 평가했다. "
                 "\"위반 0%\"는 수정 전 플러그인을 채점한 결과였다."),
    dict(slug="fire-lora", group="more", period="2026.10", accent="#ea580c",
         kind="실험", label="실험 · 회사 업무 데이터 사용 · 코드·데이터 비공개",
         hook="13/13 복구는 암기였다",
         stat="88/88 오탐", stat_cap="처음 보는 카메라의 정상 장면",
         summary="VLM에 화재 LoRA를 붙였다. 홀드아웃으로 암기를 걸러냈더니, "
                 "처음 보는 카메라에서는 정상 장면이 전부 화재가 됐다."),
]

HERO_STATS = [("1.8초 → 300ms", "Jetson 8GB, VLM 검증 지연"),
              ("2,810 → 1,755MB", "정확도 유지, 런타임 교체"),
              ("25 → 95건/초", "GPU 한 장, 연속 배칭")]

HABITS = [
    ("측정 전에 기준을 먼저 적는다", "P95 35ms · 여유 700MB를 설정 파일에 먼저 적었다. 그리고 전송까지 포함하면 미달이라는 걸 나중에 스스로 찾았다.", "edge-deploy", 2),
    ("좋은 숫자를 먼저 의심한다", "26/26 복구가 학습 데이터에 있던 이벤트였다. 13개를 떼어 다시 쟀다.", "fire-lora", 1),
    ("증명하지 못한 것을 남긴다", "트리거된 이벤트만 기록돼 재현율은 측정할 수 없었다. 측정한 것처럼 쓰지 않았다.", "edge-deploy", 8),
]

LEAK_PATTERNS = [
    r"<!--", r"Claude(가|의 판단| 판단| 초안)", r"\[Claude", r"\[확인", r"<계정>", r"C00_\d", r"review_(codex|gpt)",
    r"FIRE_LORA", r"/home/", r"Desktop", r"(?i)aimatix", r"에이아이매틱스",
    r"best_alpha", r"\.md\b", r"맑은에스티", r"(?i)malgeun", r"010-?\d{4}-?\d{4}", r"하남시",
]

MERMAID_JS = """<script type="module">
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
mermaid.initialize({ startOnLoad: true, theme: "neutral", fontFamily: "Pretendard Variable, Pretendard, sans-serif" });
</script>"""

FONT = "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"

CSS = r"""
:root { --fg:#0f172a; --muted:#64748b; --line:#e2e8f0; --soft:#f8fafc; --accent:#4f46e5; --dark:#0b1020; }
* { box-sizing:border-box; }
html { scroll-behavior:smooth; }
body { margin:0; font-family:"Pretendard Variable","Pretendard","Noto Sans KR","Apple SD Gothic Neo",sans-serif;
       color:var(--fg); line-height:1.7; font-size:16px; word-break:keep-all; background:#fff; }
a { color:inherit; }
.wrap { max-width:1080px; margin:0 auto; padding:0 24px; }
.narrow { max-width:760px; }

/* nav */
header.site { position:sticky; top:0; z-index:10; background:rgba(11,16,32,.85); backdrop-filter:blur(8px); }
header.site .wrap { display:flex; justify-content:space-between; align-items:center; height:58px; }
header.site a { color:#e2e8f0; text-decoration:none; font-size:15px; }
header.site .brand { font-weight:800; letter-spacing:-.3px; color:#fff; }
header.site nav a { margin-left:22px; opacity:.8; } header.site nav a:hover { opacity:1; }

/* hero */
.hero { background:radial-gradient(1200px 500px at 15% -10%, #3730a3 0%, transparent 60%),
                   radial-gradient(900px 500px at 100% 0%, #0e7490 0%, transparent 55%), var(--dark);
        color:#fff; padding:84px 0 72px; }
.hero .eyebrow { color:#a5b4fc; font-weight:700; font-size:14px; letter-spacing:.5px; margin:0 0 14px; }
.hero h1 { font-size:44px; line-height:1.25; margin:0 0 18px; letter-spacing:-1px; font-weight:800; max-width:820px; }
.hero h1 em { font-style:normal; background:linear-gradient(90deg,#a5b4fc,#67e8f9); -webkit-background-clip:text; background-clip:text; color:transparent; }
.hero .lead { font-size:18px; color:#cbd5e1; max-width:680px; margin:0 0 34px; }
.hstats { display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin:0 0 34px; }
.hstat { background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.12); border-radius:14px; padding:18px 20px; }
.hstat .n { font-size:28px; font-weight:800; letter-spacing:-.5px; color:#fff; white-space:nowrap; }
.hstat .c { font-size:13.5px; color:#94a3b8; margin-top:2px; }
.btns a { display:inline-block; padding:12px 22px; border-radius:999px; font-weight:700; font-size:15px;
          text-decoration:none; margin:0 10px 10px 0; transition:transform .15s; }
.btns a:hover { transform:translateY(-2px); }
.btn-primary { background:#fff; color:var(--dark); }
.btn-ghost { border:1px solid rgba(255,255,255,.35); color:#fff; }

/* sections */
section.block { padding:72px 0 8px; }
.sec-h { font-size:28px; font-weight:800; letter-spacing:-.6px; margin:0 0 6px; }
.sec-sub { color:var(--muted); margin:0 0 28px; }

/* flow */
.flow { display:grid; grid-template-columns:1fr auto 1fr auto 1fr; align-items:stretch; gap:10px; margin:0 0 28px; }
.flow a { text-decoration:none; background:var(--soft); border:1px solid var(--line); border-radius:12px; padding:14px 16px; font-size:15px; transition:border-color .15s; }
.flow a:hover { border-color:var(--fg); }
.flow .who { display:block; font-size:12px; font-weight:800; color:var(--accent); }
.flow .arr { align-self:center; color:#94a3b8; font-size:20px; }

/* cards */
.grid { display:grid; grid-template-columns:repeat(2,1fr); gap:22px; }
.card { display:flex; flex-direction:column; text-decoration:none; color:var(--fg); background:#fff; border:1px solid var(--line);
        border-radius:16px; overflow:hidden; transition:transform .18s, box-shadow .18s; }
.card:hover { transform:translateY(-4px); box-shadow:0 18px 40px -18px rgba(15,23,42,.35); }
.thumb { position:relative; aspect-ratio:16/9; background:var(--c); overflow:hidden; }
.thumb img { width:100%; height:100%; object-fit:cover; display:block; transition:transform .4s; }
.card:hover .thumb img { transform:scale(1.04); }
.thumb::after { content:""; position:absolute; inset:0; background:linear-gradient(180deg, transparent 35%, rgba(2,6,23,.82) 100%); }
.thumb.graph { background:var(--c); }
.thumb.graph img { filter:grayscale(1) contrast(1.15); mix-blend-mode:multiply; }
.thumb.graph::after { background:linear-gradient(180deg, transparent 30%, rgba(2,6,23,.75) 100%); }
.thumb.noimg { background:linear-gradient(135deg, var(--c), #0b1020); }
.thumb.noimg::after { background:none; }
.thumb .kind { position:absolute; top:14px; left:14px; z-index:2; background:rgba(255,255,255,.92); color:var(--c);
               font-size:12px; font-weight:800; padding:3px 10px; border-radius:999px; }
.thumb .st { position:absolute; left:18px; bottom:14px; z-index:2; color:#fff; }
.thumb .st .n { font-size:30px; font-weight:800; letter-spacing:-.6px; line-height:1.15; }
.thumb .st .c { font-size:13px; opacity:.85; }
.cbody { padding:18px 20px 20px; display:flex; flex-direction:column; flex:1; }
.cbody .hook { font-size:20px; font-weight:800; letter-spacing:-.4px; line-height:1.4; margin:0 0 8px; }
.cbody .sum { color:#475569; font-size:15px; margin:0 0 14px; flex:1; }
.cbody .foot { display:flex; justify-content:space-between; align-items:center; font-size:13px; color:var(--muted); }
.cbody .go { color:var(--c); font-weight:800; font-size:14px; }
.card.wide { grid-column:1 / -1; flex-direction:row; }
.card.wide .thumb { width:42%; aspect-ratio:auto; min-height:200px; }
.card.wide .cbody { width:58%; }

/* habits */
.habits { display:grid; grid-template-columns:repeat(3,1fr); gap:18px; }
.habit { border:1px solid var(--line); border-radius:16px; padding:22px; background:var(--soft); text-decoration:none; transition:border-color .15s; }
.habit:hover { border-color:var(--fg); }
.habit .no { font-size:13px; font-weight:800; color:var(--accent); }
.habit h3 { font-size:18px; margin:6px 0 8px; letter-spacing:-.3px; }
.habit p { margin:0 0 10px; color:#475569; font-size:14.5px; }
.habit .src { font-size:13px; font-weight:700; color:var(--fg); }

/* contact band */
.band { margin:80px 0 0; background:var(--dark); color:#fff; padding:56px 0; }
.band h2 { margin:0 0 8px; font-size:26px; letter-spacing:-.5px; }
.band p { color:#94a3b8; margin:0 0 22px; }

footer.site { color:var(--muted); font-size:13px; padding:22px 0 40px; }

/* case page */
.chero { background:linear-gradient(135deg, var(--c), var(--dark) 75%); color:#fff; padding:56px 0 44px; }
.chero .back { color:#e2e8f0; font-size:14px; text-decoration:none; opacity:.85; }
.chero .badge { display:inline-block; margin:18px 0 10px; font-size:12.5px; font-weight:700; background:rgba(255,255,255,.15);
                border:1px solid rgba(255,255,255,.25); padding:3px 10px; border-radius:999px; }
.chero h1 { font-size:34px; line-height:1.3; letter-spacing:-.8px; margin:0 0 14px; font-weight:800; }
.chero .st { display:flex; gap:14px; align-items:baseline; flex-wrap:wrap; margin:0 0 14px; }
.chero .st .n { font-size:30px; font-weight:800; }
.chero .st .c { color:#cbd5e1; font-size:14px; }
.tags { margin:4px 0 0; }
.tag { display:inline-block; font-size:12px; border-radius:999px; padding:2px 10px; margin:0 6px 6px 0;
       background:rgba(255,255,255,.12); color:#e2e8f0; border:1px solid rgba(255,255,255,.18); }
article { padding:36px 0 20px; }
article p { margin:12px 0; }
blockquote { margin:0 0 20px; padding:14px 18px; border-left:4px solid var(--c); background:var(--soft); color:#334155; border-radius:0 10px 10px 0; }
blockquote p { margin:6px 0; }
.intro > p > sub { display:block; padding:10px 14px; background:#eef2ff; border-radius:10px; color:#334155; font-size:14px; }
strong { background:linear-gradient(transparent 62%, #fde68a 62%); font-weight:700; }
.toc strong, h3 strong, .hook strong { background:none; }
.toc { border:1px solid var(--line); border-radius:14px; padding:16px 20px 8px; margin:26px 0 30px; background:#fff; }
.toc-h { font-weight:800; font-size:13px; color:var(--muted); margin-bottom:6px; letter-spacing:.3px; }
.toc ol { margin:0; padding-left:22px; } .toc li { margin:0 0 8px; font-size:15px; }
.toc a { text-decoration:none; } .toc a:hover { color:var(--c); }
.item { display:flex; gap:16px; padding:24px 0; border-top:1px solid var(--line); scroll-margin-top:70px; }
.num { flex:0 0 34px; height:34px; border-radius:50%; background:var(--c); color:#fff; font-weight:800;
       display:flex; align-items:center; justify-content:center; font-size:15px; }
.ibody { flex:1; min-width:0; }
.ibody ul, .ibody ol { padding-left:22px; } .ibody li { margin:4px 0; }
.ibody table { border-collapse:collapse; width:100%; font-size:14px; margin:12px 0; } .ibody th, .ibody td { border:1px solid var(--line); padding:7px 10px; text-align:left; } .ibody th { background:var(--soft); }
.ibody h3 { margin:3px 0 8px; font-size:19px; line-height:1.45; letter-spacing:-.3px; }
pre.mermaid { background:#fff; border:1px solid var(--line); border-radius:10px; padding:14px; overflow-x:auto; text-align:center; margin:16px 0; }
figure { margin:16px 0; } figure img { width:100%; display:block; border:1px solid var(--line); border-radius:10px; cursor:zoom-in; }
details { margin-top:10px; font-size:14px; color:var(--muted); }
summary { cursor:pointer; color:var(--c); font-size:13.5px; font-weight:700; user-select:none; }
details p { margin:8px 0 0; padding:10px 12px; background:var(--soft); border-radius:8px; line-height:1.65; }
.tailnote { border-top:1px solid var(--line); margin-top:8px; padding-top:14px; font-size:13.5px; color:var(--muted); }
.tailnote a { color:var(--c); font-weight:700; }
.next { display:block; margin:36px 0 70px; padding:22px 24px; border-radius:16px; text-decoration:none; color:#fff;
        background:linear-gradient(135deg, var(--nc), var(--dark)); transition:transform .15s; }
.next:hover { transform:translateY(-3px); }
.next .l { font-size:13px; opacity:.8; font-weight:700; } .next .t { font-size:21px; font-weight:800; letter-spacing:-.4px; }

/* gallery */
.gallery { margin:16px 0; padding:14px; border:1px solid var(--line); border-radius:12px; background:#fff; }
.gtitle { font-weight:800; font-size:14.5px; margin-bottom:10px; }
.tiles { display:grid; grid-template-columns:repeat(auto-fill, minmax(140px, 1fr)); gap:10px; }
.tile img { width:100%; aspect-ratio:248/360; object-fit:cover; display:block; border-radius:8px; }
.tcap { font-size:12.5px; line-height:1.5; margin-top:5px; color:#334155; }
.tcap .tt { font-weight:800; color:var(--fg); }
.yes { color:#dc2626; } .no { color:#16a34a; }
.gfoot { font-size:13px; color:#334155; margin:10px 0 2px; }
.credit { font-size:11.5px; color:var(--muted); margin:2px 0 0; } .credit a { color:var(--muted); }

@media (max-width:760px) {
  .hero { padding:56px 0 48px; } .hero h1 { font-size:30px; } .hero .lead { font-size:16px; }
  .habits, .grid { grid-template-columns:1fr; }
  .hstats { grid-template-columns:1fr; gap:8px; } .hstat { padding:12px 16px; display:flex; justify-content:space-between; align-items:baseline; gap:10px; }
  .hstat .n { font-size:20px; } .hstat .c { font-size:12px; text-align:right; margin:0; }
  .flow a { padding:10px 14px; font-size:14px; } .flow .arr { font-size:16px; line-height:1; }
  .flow { grid-template-columns:1fr; } .flow .arr { transform:rotate(90deg); justify-self:center; }
  .card.wide { flex-direction:column; } .card.wide .thumb, .card.wide .cbody { width:100%; } .card.wide .thumb { aspect-ratio:16/9; }
  .chero h1 { font-size:26px; } .item { gap:12px; } .num { flex-basis:28px; height:28px; font-size:13px; }
  header.site nav a { margin-left:14px; }
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
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:image" content="/assets/img/thumbs/edge-vlm-2gb.jpg">
<link rel="stylesheet" href="{FONT}">
<link rel="stylesheet" href="/assets/style.css">
</head>
<body>
<header class="site"><div class="wrap">
  <a class="brand" href="/">정원석</a>
  <nav><a href="/#work">작업</a><a href="/#how">일하는 방식</a><a href="{GITHUB}">GitHub</a></nav>
</div></header>
{body}
<footer class="site"><div class="wrap">
수치는 모두 측정 조건과 함께 적었습니다. 회사 프로젝트는 제품 구조·내부 경로·고객 정보를 빼고 정리했습니다.
</div></footer>
{MERMAID_JS if 'class="mermaid"' in body else ""}
</body>
</html>
"""


def strip_comments(text):
    return re.sub(r"<!--.*?-->\s*", "", text, flags=re.S)


MERMAID_RE = re.compile(r"```mermaid\n(.*?)```", re.S)


def md(text):
    """마크다운 → HTML. ```mermaid 블록은 그대로 보존해 브라우저에서 그린다(nl2br가 줄바꿈을 망치지 않게)."""
    blocks = []

    def keep(m):
        blocks.append(m.group(1))
        return f"\n\nMERMAIDBLOCK{len(blocks) - 1}\n\n"

    out = markdown.markdown(MERMAID_RE.sub(keep, text.strip()), extensions=["tables", "nl2br"])
    for k, code in enumerate(blocks):
        out = out.replace(f"<p>MERMAIDBLOCK{k}</p>", f'<pre class="mermaid">{html.escape(code)}</pre>')
    return out


def inline(text):
    return md(text)[3:-4]


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
    intro = re.sub(r"^---[ \t]*$", "", raw[:items[0].start()], flags=re.M)
    tail = re.sub(r"^---[ \t]*$", "", raw[items[-1].end():], flags=re.M)
    parsed = []
    for it in items:
        body = it.group(3)
        notes = re.findall(r"<sub>(.*?)</sub>", body, flags=re.S)
        body = re.sub(r"<sub>.*?</sub>", "", body, flags=re.S)
        parsed.append(dict(n=int(it.group(1)), head=it.group(2).strip(), body=body, notes=notes))
    return title, tags, intro, parsed, tail


def fig_html(names):
    out = []
    for n in names:
        if n.startswith("gallery:"):
            out.append((SRC / "galleries" / f"{n[8:]}.html").read_text(encoding="utf-8"))
        else:
            out.append(f'<figure><a href="/assets/img/{n}.png" target="_blank">'
                       f'<img src="/assets/img/{n}.png" loading="lazy" alt="{n}"></a></figure>')
    return "".join(out)


def load(p):
    raw = strip_comments((SRC / "cases" / f"{p['slug']}.md").read_text(encoding="utf-8"))
    p["title"], p["tags"], p["intro"], p["items"], p["tail"] = split_case(raw)


def render_case(p, nxt):
    figs = p.get("figs", {})
    tag_html = "".join(f'<span class="tag">{html.escape(t)}</span>' for t in p["tags"])
    toc = "\n".join(f'<li><a href="#s{i["n"]}">{inline(i["head"])}</a></li>' for i in p["items"])
    blocks = []
    for i in p["items"]:
        notes = ""
        if i["notes"]:
            notes = '<details><summary>측정 조건</summary>' + "".join(f"<p>{n.strip()}</p>" for n in i["notes"]) + "</details>"
        blocks.append(f'<section class="item" id="s{i["n"]}"><div class="num">{i["n"]}</div><div class="ibody">'
                      f'<h3>{inline(i["head"])}</h3>{md(i["body"])}{fig_html(figs.get(i["n"], []))}{notes}</div></section>')
    tail_html = md(p["tail"].replace("<sub>", "").replace("</sub>", ""))
    body = f"""<div class="chero" style="--c:{p['accent']}"><div class="wrap narrow">
<a class="back" href="/#work">← 전체 작업</a><br>
<span class="badge">{html.escape(p['label'])}</span>
<h1>{html.escape(p['title'])}</h1>
<div class="st"><span class="n">{html.escape(p['stat'])}</span><span class="c">{html.escape(p['stat_cap'])}</span></div>
<div class="tags">{tag_html}</div>
</div></div>
<main style="--c:{p['accent']}"><div class="wrap narrow"><article>
<div class="intro">{md(p['intro'])}{fig_html(figs.get(0, []))}</div>
<nav class="toc"><div class="toc-h">한눈에 보기 · 항목을 누르면 이동합니다</div><ol>
{toc}
</ol></nav>
{"".join(blocks)}
<div class="tailnote">{tail_html}</div>
</article>
<a class="next" style="--nc:{nxt['accent']}" href="/cases/{nxt['slug']}/"><div class="l">다음 작업 →</div><div class="t">{html.escape(nxt['hook'])}</div></a>
</div></main>"""
    out = OUT_CASES / p["slug"] / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(f"{p['title']} · 정원석", body, p["summary"]), encoding="utf-8")
    return out


def card(p, wide=False):
    thumb = ROOT / "assets" / "img" / "thumbs" / f"{p['slug']}.jpg"
    img = f'<img src="/assets/img/thumbs/{p["slug"]}.jpg" alt="" loading="lazy">' if thumb.exists() else ""
    return (f'<a class="card{" wide" if wide else ""}" style="--c:{p["accent"]}" href="/cases/{p["slug"]}/">'
            f'<div class="thumb{" graph" if img and p["slug"] != "edge-vlm-2gb" else ""}{"" if img else " noimg"}">{img}<span class="kind">{html.escape(p["kind"])}</span>'
            f'<div class="st"><div class="n">{html.escape(p["stat"])}</div><div class="c">{html.escape(p["stat_cap"])}</div></div></div>'
            f'<div class="cbody"><div class="hook">{html.escape(p["hook"])}</div>'
            f'<p class="sum">{html.escape(p["summary"])}</p>'
            f'<div class="foot"><span>{p["period"]} · {html.escape(p["label"].split(" · ")[1] if " · " in p["label"] else "")}</span>'
            f'<span class="go">읽기 →</span></div></div></a>')


def render_index():
    by = {p["slug"]: p for p in PROJECTS}
    stats = "".join(f'<div class="hstat"><div class="n">{html.escape(n)}</div><div class="c">{html.escape(c)}</div></div>'
                    for n, c in HERO_STATS)
    main_cards = "\n".join(card(p) for p in PROJECTS if p["group"] == "main")
    more_cards = "\n".join(card(p, wide=True) for p in PROJECTS if p["group"] == "more")
    habits = "".join(
        f'<a class="habit" href="/cases/{slug}/#s{n}"><div class="no">0{k+1}</div><h3>{html.escape(h)}</h3>'
        f'<p>{html.escape(t)}</p><div class="src">{html.escape(by[slug]["hook"])} · {n}번 →</div></a>'
        for k, (h, t, slug, n) in enumerate(HABITS))
    flow = "".join([
        f'<a href="/cases/edge-deploy/"><span class="who">회사</span>8GB 기기에 2차 검증기를 올릴 수 있나</a><span class="arr">→</span>',
        f'<a href="/cases/edge-vlm-2gb/"><span class="who">업무 연장 연구</span>2GB 안에서 상시로 돌리려면</a><span class="arr">→</span>',
        f'<a href="/cases/vlm-serving/"><span class="who">업무 연장 연구</span>서버로 모으면 카메라 몇 대까지</a>'])
    body = f"""<section class="hero"><div class="wrap">
<p class="eyebrow">VISION · VLM · EDGE AI ENGINEER</p>
<h1>모델이 현장에서 <em>왜 틀리는지</em> 찾아내고,<br>제한된 장비에서 돌아가게 만듭니다</h1>
<p class="lead">오프라인에서 좋아 보이던 모델이 실제 환경에서 무너지는 지점을 측정으로 찾고,
프롬프트·입력·모델·런타임을 바꿔 되돌립니다.</p>
<div class="hstats">{stats}</div>
<div class="btns"><a class="btn-primary" href="#work">작업 보기</a><a class="btn-ghost" href="{GITHUB}">GitHub</a></div>
</div></section>

<section class="block" id="work"><div class="wrap">
<h2 class="sec-h">대표 작업</h2>
<p class="sec-sub">회사에서 남은 질문을 직접 이어서 풀었습니다. 카드를 누르면 과정과 실패까지 볼 수 있습니다.</p>
<div class="flow">{flow}</div>
<div class="grid">
{main_cards}
</div>
</div></section>

<section class="block"><div class="wrap">
<h2 class="sec-h">그 밖의 작업</h2>
<p class="sec-sub">결과가 좋아 보일 때 측정을 다시 의심한 기록입니다.</p>
<div class="grid more">{more_cards}</div>
</div></section>

<section class="block" id="how"><div class="wrap">
<h2 class="sec-h">일하는 방식</h2>
<p class="sec-sub">말이 아니라 기록으로 보여드립니다. 누르면 해당 항목으로 이동합니다.</p>
<div class="habits">{habits}</div>
</div></section>

<section class="band"><div class="wrap">
<h2>코드와 판단 기록은 GitHub에 있습니다</h2>
<p>공개 데이터로 다시 푼 연구는 실험 스크립트와 결정 기록까지 공개했습니다.</p>
<div class="btns"><a class="btn-primary" href="{GITHUB}">GitHub 보기</a></div>
</div></section>
"""
    out = ROOT / "index.html"
    out.write_text(page("정원석 · Vision·VLM·Edge AI 엔지니어", body,
                        "모델이 현장에서 왜 틀리는지 찾아내고, 제한된 장비에서 돌아가게 만드는 엔지니어 정원석의 포트폴리오"),
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
    for p in PROJECTS:
        load(p)
    order = [p for p in PROJECTS if p["group"] == "main"] + [p for p in PROJECTS if p["group"] == "more"]
    outputs = [render_case(p, order[(k + 1) % len(order)]) for k, p in enumerate(order)]
    outputs.append(render_index())
    sources = list((ROOT / "src").rglob("*.md")) + list((ROOT / "src").rglob("*.html"))
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
