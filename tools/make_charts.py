#!/usr/bin/env python3
"""카드·페이지용 그래프. 수치는 각 케이스 원고(src/ko/cases/*.md)에 적힌 값만 쓴다."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

SITE = Path(__file__).resolve().parent.parent
OUT = SITE / "assets" / "img"
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f or "NotoSansCJK-Bold" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK KR", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "axes.titlesize": 13, "font.size": 11})


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ONVIF RAG — onvif-rag.md 4번: 0.074 → 0.395 → 0.467 → 0.712 → 0.894, 검증 12문항 0.917
fig, ax = plt.subplots(figsize=(8, 4.2))
ys = [0.074, 0.395, 0.467, 0.712, 0.894]
xs = ["시작", "개선 1", "개선 2", "개선 3", "개발 종료"]
ax.plot(xs, ys, marker="o", lw=2.5, color="#be123c")
for x, y in zip(xs, ys):
    off = (0, -20) if x == "개발 종료" else (0, 9)
    ax.annotate(f"{y:.3f}", (x, y), textcoords="offset points", xytext=off, ha="center", fontsize=11, fontweight="bold")
ax.scatter(["개발 종료"], [0.917], marker="D", s=60, color="#0f172a", zorder=3)
ax.annotate("수정에 쓰지 않은 검증 12문항 0.917", ("개발 종료", 0.917), textcoords="offset points", xytext=(-12, 2), ha="right", va="bottom", fontsize=10, color="#0f172a")
ax.set_ylim(0, 1.05); ax.set_ylabel("원문 체크리스트 충족률")
ax.set_title("로컬 7B RAG: 자체 평가 9문항 충족률 (5회 평균)")
fig.text(0.01, -0.04, "작성자가 만든 소규모 평가셋 기준. 같은 코드도 ±0.06 흔들려 여러 번 돌린 평균으로만 판단. 팀 실사용 검증 없음.", fontsize=9, color="#64748b")
save(fig, "onvif_rag_score")

# 화재 LoRA — fire-lora.md 3·5번: 하드 홀드아웃 0/13 → 13/13, 처음 보는 카메라 음성 88장: base 0.002~0.013(threshold 0.55 미만) → 3ep 전부 Yes
fig, ax = plt.subplots(figsize=(8, 4.2))
labels = ["홀드아웃 화재 이벤트\n복구 (13개)", "처음 보는 카메라\n정상 장면 오탐 (88장)"]
base = [0, 0]; lora = [13 / 13, 88 / 88]
x = range(len(labels)); w = 0.36
b1 = ax.bar([i - w / 2 for i in x], base, w, label="기본 모델", color="#94a3b8")
b2 = ax.bar([i + w / 2 for i in x], lora, w, label="LoRA 3 epoch", color="#ea580c")
for i, (a, b) in enumerate(zip(["0/13", "0/88"], ["13/13", "88/88"])):
    ax.text(i - w / 2, 0.03, a, ha="center", fontsize=11, fontweight="bold")
    ax.text(i + w / 2, 1.02, b, ha="center", fontsize=11, fontweight="bold")
ax.set_xticks(list(x)); ax.set_xticklabels(labels); ax.set_ylim(0, 1.18); ax.set_yticks([0, .5, 1]); ax.set_yticklabels(["0%", "50%", "100%"])
ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
ax.set_title("복구는 됐다. 처음 보는 카메라의 정상 장면도 전부 화재가 됐다", pad=30)
fig.text(0.01, -0.04, "threshold 0.55. 기본 모델의 정상 장면 점수 0.002~0.013 → LoRA 후 0.93~1.00. 테스트는 기본 모델 실패 사례로 고른 조건부 평가.", fontsize=9, color="#64748b")
save(fig, "fire_lora_tradeoff")
print("ok")

# PM — pm-requirements.md 2~6번 수치만 사용
from matplotlib.patches import FancyBboxPatch
fig, ax = plt.subplots(figsize=(10, 3.2)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 3.2)
steps = [("배우기", "PMBOK·애자일\n35 PDU 강의\n코넬노트"), ("헌장", "목표 7 · 마일스톤 7\n성공 기준"),
         ("WBS", "38항목\n담당·기한·선행 작업"), ("요구사항", "100건 이상\n수용 기준·검증 방법"),
         ("미확정 관리", "5칸 표 + 잠정값\n비싼 결정부터")]
for i, (h, b) in enumerate(steps):
    x = 0.15 + i * 1.98
    ax.add_patch(FancyBboxPatch((x, 0.35), 1.62, 2.3, boxstyle="round,pad=0.02,rounding_size=0.12",
                                fc="#f1f5f9" if i else "#e2e8f0", ec="#475569", lw=1.4))
    ax.text(x + 0.81, 2.22, h, ha="center", va="center", fontsize=13, fontweight="bold", color="#0f172a")
    ax.text(x + 0.81, 1.25, b, ha="center", va="center", fontsize=10.5, color="#334155", linespacing=1.5)
    if i < 4:
        ax.annotate("", (x + 1.95, 1.5), (x + 1.66, 1.5), arrowprops=dict(arrowstyle="-|>", color="#475569", lw=1.6))
ax.set_title("PM이 없던 프로젝트: 배운 순서대로 세운 것", pad=4)
save(fig, "pm_flow")

fig, ax = plt.subplots(figsize=(10, 2.6)); ax.axis("off")
cols = ["무엇이", "누구에게서 나왔고", "누가 정하고", "언제까지", "그동안 쓸 잠정값"]
rows = [["정해지지 않은 값·결정", "요청한 쪽 / 근거", "결정권자", "결정 기한", "결정 전까지 작업에 쓸 값"],
        ["예: 라인크로싱 판정 위치\n(모델 쪽 vs 후처리 쪽)", "연동 시 필요", "관련 담당 합의", "되돌리기 비싼 결정\n→ 회의 우선 상정", "잠정 기준으로 개발 진행"]]
t = ax.table(cellText=rows, colLabels=cols, loc="center", cellLoc="center")
t.auto_set_font_size(False); t.set_fontsize(10); t.scale(1, 2.6)
for (r, c), cell in t.get_celld().items():
    cell.set_edgecolor("#cbd5e1")
    if r == 0: cell.set_facecolor("#475569"); cell.get_text().set_color("white"); cell.get_text().set_fontweight("bold")
    elif r == 1: cell.set_facecolor("#f8fafc"); cell.get_text().set_color("#64748b")
ax.set_title("미확정 항목을 비워 두지 않고 적은 5칸 (공개용 일반화 예시)", pad=2)
save(fig, "pm_open_items")
print("ok2")
