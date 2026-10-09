"""FloodOps 최종발표 슬라이드 (v3).

BASEMENT 2차 발표자료(먼저 가야 할 집)와 같은 도구·구성으로 다시 만들었다. 수치는 2026-10-10 로컬 API·테스트 결과와
TODO.md / docs/data-quality.md 기준이다. 각 함수는 no(장 번호)를 받아 (Canvas, images, notes) 를 돌려준다.
images 는 PowerPoint 그림으로 올릴 캡처 [(파일, x, y, w, h, crop)] (px, 1600x900 기준).
"""
from __future__ import annotations

import math

from svgkit import Canvas, width, wrap

# ---- 색 ------------------------------------------------------------------
INK = "#0F1E2E"
MUTED = "#566676"
SOFT = "#8494A3"
LINE = "#D6DEE6"
PAPER = "#F2F5F8"
TEAL = "#0B8577"
TEAL_L = "#E1F2EF"
RED = "#B42318"
RED_L = "#FBEAE8"
AMBER = "#B7791F"
AMBER_L = "#FAF0DC"
NAVY = "#0B1B2B"
MINT = "#5EEAD4"
DMUTED = "#9DB2C6"
WHITE = "#FFFFFF"
HERO_BG = "#070D1A"
HERO_RED = "#F87171"
HERO_MUTED = "#9DB2C6"
WATER = "#2B8FD6"
CELL = "#F87171"

SHOTS = "assets/shots"
URL = "floodops.duckdns.org"

SOURCES: list[tuple[int, str, str]] = []
_CUR = {"no": 0, "title": ""}


# ---- 공통 틀 -------------------------------------------------------------
def header(c: Canvas, no: int, section: str, title: str, sub: str | None = None):
    _CUR.update(no=no, title=section)
    c.text(80, 86, f"{no:02d}", 20, 700, TEAL)
    c.text(80 + width(f"{no:02d}", 20, 700) + 14, 86, section, 20, 500, MUTED)
    assert width(title, 50, 700) <= 1440, title
    c.text(80, 160, title, 50, 700, INK)
    if sub:
        assert width(sub, 24) <= 1440, sub
        c.text(80, 208, sub, 24, 400, MUTED)


def footer(c: Canvas, s: str):
    for prefix in ("출처: ", "화면: ", "기준: ", "검증: "):
        if s.startswith(prefix):
            s = s[len(prefix):]
    SOURCES.append((_CUR["no"], _CUR["title"], s))


def badge(c: Canvas, cx, cy, n, r=22, fill=TEAL, fg=WHITE, size=22):
    c.circle(cx, cy, r, fill=fill)
    c.text(cx, cy + size * 0.36, str(n), size, 700, fg, anchor="middle")


def card(c: Canvas, x, y, w, h, fill=PAPER, stroke="none", r=14, sw=1):
    c.rect(x, y, w, h, fill=fill, stroke=stroke, r=r, sw=sw)


def chip(c: Canvas, x, y, label, fg=TEAL, bg=TEAL_L, size=17, anchor="start"):
    w = width(label, size, 700) + 26
    h = size + 17
    x0 = x - w if anchor == "end" else x
    c.rect(x0, y, w, h, fill=bg, r=h / 2)
    c.text(x0 + 13, y + h / 2 + size * 0.36, label, size, 700, fg)
    return w


def frame(c: Canvas, x, y, w, h):
    c.rect(x - 6, y - 6, w + 12, h + 12, fill="#E3E9EF", r=10)
    c.rect(x, y, w, h, fill=NAVY, r=4)


def note_bar(c: Canvas, y, text, bg=AMBER_L, color=AMBER):
    c.rect(80, y, 1440, 56, fill=bg, r=12)
    icon_warn(c, 114, y + 28, color)
    assert width(text, 19, 500) <= 1340, text
    c.text(144, y + 35, text, 19, 500, INK)


# ---- 아이콘 ----------------------------------------------------------------
def icon_person(c, cx, cy, color):
    a = c.art(cx - 20, cy - 20, 40, 40, "아이콘 사람")
    a.circle(20, 11, 9, fill=color)
    a.path("M4,38 Q4,22 20,22 Q36,22 36,38 Z", fill=color)


def icon_office(c, cx, cy, color):
    a = c.art(cx - 20, cy - 20, 40, 40, "아이콘 기관")
    a.rect(5, 2, 30, 36, fill="none", stroke=color, sw=3, r=2)
    for dx in (13, 27):
        for dy in (11, 20, 29):
            a.rect(dx - 3, dy - 3, 6, 5, fill=color)


def icon_team(c, cx, cy, color):
    a = c.art(cx - 20, cy - 20, 40, 40, "아이콘 교육")
    for dx in (10, 30):
        a.circle(dx, 12, 6.6, fill=color)
        a.path(f"M{dx-13},37 Q{dx-13},23 {dx},23 Q{dx+13},23 {dx+13},37 Z", fill=color)


def icon_warn(c, cx, cy, color):
    a = c.art(cx - 16, cy - 16, 32, 32, "아이콘 주의")
    a.circle(16, 16, 15, fill=color)
    a.rect(14.2, 7, 3.6, 11, fill=WHITE, r=1.5)
    a.circle(16, 22.5, 2.2, fill=WHITE)


# ---- 표지 그림: 단계 재생 패널 ------------------------------------------
def hero_left_kicker(c, text):
    c.circle(104, 146, 5, fill="#991B1B")
    c.text(120, 152, text, 18, 700, "#AEBBCB")


def hero_panel(c, stage=4):
    """오른쪽 «사건 단계 재생» 패널: 격자 위 하천·붉은 셀·지하차도와 아래 시간축."""
    x0, y0, w, h = 880, 90, 640, 720
    a = c.art(x0, y0, w, h, "사건 단계 재생 패널")
    a.rect(0, 0, w, h, fill="#0C1626", stroke="#1E2F47", sw=1.5, r=22)
    a.rect(1, 1, w - 2, 70, fill="#0F1C30", r=21)
    a.rect(1, 36, w - 2, 36, fill="#0F1C30")
    # 격자
    gx, gy, cols, rows, cs = 36, 100, 14, 10, 40.6
    for i in range(cols + 1):
        a.line(gx + i * cs, gy, gx + i * cs, gy + rows * cs, "#1B2A3F", 1)
    for j in range(rows + 1):
        a.line(gx, gy + j * cs, gx + cols * cs, gy + j * cs, "#1B2A3F", 1)
    # 하천(미호강) 사선
    rx = gx + 468
    a.path(f"M{rx},{gy - 4} C{rx - 30},{gy + 140} {rx + 50},{gy + 240} {rx + 10},{gy + rows * cs + 4}", stroke="#1D6FA5", sw=26, opacity=0.9)
    a.path(f"M{rx},{gy - 4} C{rx - 30},{gy + 140} {rx + 50},{gy + 240} {rx + 10},{gy + rows * cs + 4}", stroke="#7DD3FC", sw=2)
    # 단계별 붉은 셀(안쪽부터 바깥으로)
    rings = [
        [(10, 2), (10, 3), (11, 3), (10, 4), (11, 4), (10, 5), (11, 5), (10, 6)],
        [(9, 3), (9, 4), (9, 5), (9, 6), (12, 4), (10, 7), (11, 6), (11, 7)],
        [(8, 4), (8, 5), (8, 6), (8, 7), (9, 7), (12, 5), (10, 8), (9, 8)],
        [(7, 5), (7, 6), (7, 7), (8, 8), (6, 6), (12, 6), (11, 8), (7, 8)],
        [(6, 5), (6, 7), (5, 6), (5, 7), (6, 8), (10, 9), (12, 7), (4, 7)],
    ]
    for k, ring in enumerate(rings[:stage]):
        op = 0.55 - k * 0.07
        for (i, j) in ring:
            a.rect(gx + i * cs + 1, gy + j * cs + 1, cs - 2, cs - 2, fill=CELL, opacity=op)
            a.rect(gx + i * cs + 1, gy + j * cs + 1, cs - 2, cs - 2, fill="none", stroke=CELL, sw=1, opacity=0.9)
    # 지하차도 마커
    ux, uy = gx + 4.5 * cs, gy + 6.5 * cs
    a.circle(ux, uy, 16, fill=CELL, opacity=0.25)
    a.circle(ux, uy, 7, fill=WHITE, stroke=CELL, sw=3)
    # 시간축
    ty = gy + rows * cs + 70
    a.rect(36, ty - 44, w - 72, 110, fill="#0F1C30", r=14)
    a.line(70, ty + 18, w - 70, ty + 18, "#2A3B52", 4)
    pos = [70 + (w - 140) * t for t in (0.0, 0.22, 0.52, 0.66, 0.82, 0.9, 1.0)]
    a.line(70, ty + 18, pos[stage], ty + 18, CELL, 4)
    for k, px in enumerate(pos):
        a.circle(px, ty + 18, 7 if k == stage else 5, fill=CELL if k <= stage else "#2A3B52", stroke="#0F1C30", sw=2)
    # 범례
    ly = h - 46
    a.rect(60, ly - 9, 14, 14, fill=CELL, opacity=0.6)
    a.rect(240, ly - 9, 14, 14, fill="#1D6FA5")
    a.circle(392, ly - 2, 6, fill=WHITE, stroke=CELL, sw=2.5)
    # 글자(편집 가능한 글상자)
    c.text(x0 + 32, y0 + 32, "STAGE REPLAY", 13, 700, HERO_RED)
    c.text(x0 + 32, y0 + 56, "사건 단계 재생 · 2023 오송 궁평2지하차도", 17, 700, "#E2E8F0")
    c.text(x0 + w - 32, y0 + 56, "OSONG · HAND", 12, 500, "#6F8197", anchor="end")
    c.text(x0 + ux - 14, y0 + uy - 22, "궁평2지하차도", 14, 700, WHITE, anchor="end")
    c.text(x0 + gx + 500, y0 + gy + 40, "미호강", 14, 700, "#7DD3FC")
    labels = ["04:10", "06:40", "07:50", "08:09", "08:27", "08:35", "08:40"]
    for k, (px, lab) in enumerate(zip(pos, labels)):
        c.text(x0 + px, y0 + ty + 48, lab, 12, 700 if k == stage else 400, CELL if k == stage else "#6F8197", anchor="middle")
    c.text(x0 + 70, y0 + ty - 16, "지하차도 유입 시작 · 08:27", 14, 700, "#E2E8F0")
    c.text(x0 + w - 70, y0 + ty - 16, "완전 침수까지 13분", 14, 700, HERO_RED, anchor="end")
    c.text(x0 + 82, y0 + ly + 4, "침수 추정 범위(HAND 근사)", 13, 500, "#AEBBCB")
    c.text(x0 + 262, y0 + ly + 4, "관측 수위 기준 하천", 13, 500, "#AEBBCB")
    c.text(x0 + 408, y0 + ly + 4, "통제 판단 지점", 13, 500, "#AEBBCB")


# =========================================================================
def s_cover(no):
    c = Canvas(HERO_BG)
    hero_left_kicker(c, "FloodOps 최종발표 · 홍수 대응 의사결정 디지털 트윈")
    c.text(96, 292, "FloodOps", 104, 900, WHITE)
    c.text(100, 362, "과거 홍수를 재생하고, 대응 시점을 비교합니다", 34, 700, "#E2E8F0")
    c.lines(100, 434, ["관측·공간·사건 기록을 한 시간축과 한 지도에 올려", "통제가 몇 분 빨랐다면 무엇이 달라졌을지", "근거와 가정을 함께 보여주는 서비스입니다"], 22, 400, HERO_MUTED, 1.6)
    c.rect(100, 612, 236, 38, fill="none", stroke="#991B1B", sw=1.5, r=19)
    c.text(218, 638, "반사실 사건 디지털 트윈", 17, 700, HERO_RED, anchor="middle")
    c.text(100, 718, "팀 「만약에, 침수」 · 발표 박소영", 26, 700, WHITE)
    c.text(100, 756, "최종발표 · 2026. 12.", 19, 400, "#8FA0B3")
    c.text(100, 818, URL, 22, 700, HERO_RED)
    hero_panel(c)
    notes = (
        "[10초]\n"
        "안녕하십니까. FloodOps를 발표할 박소영입니다.\n"
        "FloodOps는 과거 홍수 사건을 지도와 시간축에서 다시 재생하고, 통제나 경보가 몇 분 빨랐다면 무엇이 달라졌을지를 근거와 가정과 함께 보여주는 서비스입니다."
    )
    return c, [], notes


def s_agenda(no):
    c = Canvas()
    header(c, no, "목차", "사건에서 서비스까지, 다섯 단계로 설명합니다", "각 단계가 답하는 질문을 함께 적었습니다")
    stages = [
        ("배경과 문제", "왜 시간이고, 무엇이 비어 있나",
         "2023년 7월 오송 · 유입에서 완전 침수까지 13분 · 흩어진 관측·공간·사건 기록",
         ["s_incidents", "s_timeline", "s_sources"]),
        ("해결과 결과", "무엇을 연결했고, 무엇이 나왔나",
         "한 시간축·한 지도 · 통제 18분 전 · 단계별 침수 추정 셀 · 네 사례 선행 시간",
         ["s_solution", "s_closure", "s_hand", "s_cases", "s_case_levels"]),
        ("근거와 한계", "무엇을 계산하지 않았나",
         "공식 침수범위 없이 노출 KPI 없음 · 서울 DSM 근사 기각 · 출처·한계 화면",
         ["s_honesty", "s_provenance", "s_agent"]),
        ("서비스와 활용", "누가, 어떤 화면으로 쓰나",
         "화면 4개 · 관제 · 시나리오 비교 · 네 사례 · 훈련과 사후 검토",
         ["s_service", "s_screen_console", "s_screen_compare", "s_screen_cases", "s_users"]),
        ("실현과 확장", "검증됐고, 넓힐 수 있나",
         "테스트 154개 · 서버 한 대 · 같은 명령으로 재생성 · 사례 추가 계약",
         ["s_realism", "s_sustain", "s_ripple"]),
    ]
    order = [fn.__name__ for fn in SLIDES]
    y0, rh = 262, 114
    for i, (name, q, items, fns) in enumerate(stages):
        nums = [order.index(f) + 1 for f in fns if f in order]
        assert nums and nums == list(range(nums[0], nums[-1] + 1)), (name, nums)
        y = y0 + i * rh
        if i:
            c.line(80, y, 1520, y, LINE, 1.5)
        c.text(80, y + 62, f"{i + 1:02d}", 46, 900, TEAL)
        c.text(190, y + 44, name, 26, 700, INK)
        c.text(190, y + 76, q, 18, 500, TEAL)
        assert width(items, 15) <= 1080, (name, width(items, 15))
        c.text(190, y + 102, items, 15, 400, SOFT)
        chip(c, 1520, y + 30, f"{nums[0]}–{nums[-1]}장" if len(nums) > 1 else f"{nums[0]}장", fg=MUTED, bg=PAPER, size=16, anchor="end")
    notes = (
        "[15초]\n"
        "발표는 다섯 단계입니다. 왜 «시간»을 보는지와 무엇이 비어 있는지, 기록을 어떻게 연결했고 어떤 숫자가 나왔는지, "
        "무엇을 계산하지 않았는지, 누가 어떤 화면으로 쓰는지, 그리고 검증과 확장입니다."
    )
    return c, [], notes


# ---- 01 배경과 문제 ----------------------------------------------------------
def s_incidents(no):
    c = Canvas()
    header(c, no, "배경과 문제", "2023년 7월 15일 아침, 오송",
           "물이 들어온 뒤 완전히 잠기기까지, 판단할 시간은 몇 분이었을까요")
    w = c.text(76, 420, "13", 150, 900, TEAL)
    c.text(88 + w, 420, "분", 44, 700, TEAL)
    c.text(82, 480, "궁평2지하차도 유입(08:27) → 완전 침수(08:40)", 26, 700, INK)
    c.lines(82, 520, ["제방 붕괴(08:09)부터는 31분,", "홍수경보(04:10)부터는 4시간 30분이었습니다."], 19, 400, MUTED, 1.45)
    c.line(82, 600, 640, 600, LINE, 1.5)
    c.text(82, 646, "시간은 있었습니다. 다만 어디에, 얼마나 있는지 보이지 않았습니다.", 22, 700, INK)
    cases = [
        ("2023. 7. 15. 08:40경", "청주 오송 궁평2지하차도", "미호강 임시제방 붕괴 · 지하차道 침수", "14", "명"),
        ("2022. 8. 8. 밤", "서울 관악구 신림동", "반지하 주택 침수", "3", "명"),
        ("2022. 9. 6. 06:45", "경북 포항 인덕동", "아파트 지하주차장 침수", "7", "명"),
    ]
    cases[0] = ("2023. 7. 15. 08:40경", "청주 오송 궁평2지하차도", "미호강 임시제방 붕괴 · 지하차도 침수", "14", "명")
    for i, (when, where, what, n, unit) in enumerate(cases):
        y = 262 + i * 140
        card(c, 720, y, 800, 118)
        c.text(752, y + 36, when, 16, 700, TEAL)
        c.text(752, y + 72, where, 24, 700, INK)
        c.text(752, y + 100, what, 17, 400, MUTED)
        c.rect(1350, y + 20, 150, 78, fill=RED_L, r=12)
        w = width(n, 44, 900) + width(unit, 18, 700) + 6
        c.text(1425 - w / 2, y + 73, n, 44, 900, RED)
        c.text(1425 - w / 2 + width(n, 44, 900) + 6, y + 73, unit, 18, 700, RED)
    c.text(1520, 700, "사망자는 공식 발표·보도 수치 · 세 사건 합계가 아닌 대표 사례", 15, 400, SOFT, anchor="end")
    c.text(80, 800, "세 사건 모두 «언제 막았어야 했나»가 뒤늦게 질문됐습니다. FloodOps는 그 질문을 사건이 끝난 뒤 다시 재생해 봅니다.", 23, 700, INK)
    footer(c, "출처: 오송 사건 시각은 국무조정실 감찰 결과 발표(2023-07-28)와 사건 재구성 타임라인(출처 쪽수 확인 필요) · 사망자 수는 국무조정실·소방 발표 보도 · 서울·포항은 언론 보도")
    notes = (
        "[35초]\n"
        "2023년 7월 15일 아침 오송입니다. 궁평2지하차도에 물이 들어온 08시 27분부터 완전히 잠긴 08시 40분까지 13분이었습니다. "
        "임시제방이 무너진 08시 09분부터 세면 31분, 홍수경보가 난 새벽 4시 10분부터 세면 네 시간 반입니다.\n"
        "시간은 있었습니다. 문제는 그 시간이 어디에 얼마나 있는지가 당시에는 보이지 않았다는 점입니다. "
        "서울 신림동 반지하, 포항 지하주차장도 같은 질문이 사고 뒤에야 나왔습니다."
    )
    return c, [], notes


def s_timeline(no):
    c = Canvas()
    header(c, no, "배경과 문제", "판단할 시간은 어떻게 줄었나",
           "오송 사건을 7단계로 재구성하면, 통제 요건이 갖춰진 뒤에도 107분이 흘렀습니다")
    stages = [
        ("04:10", "홍수경보 발령", "사건 기록", TEAL),
        ("06:40", "미호강 계획홍수위 도달", "국무조정실 발표", TEAL),
        ("07:50", "월류 시작", "사건 기록", AMBER),
        ("08:09", "임시제방 붕괴", "사건 기록", AMBER),
        ("08:27", "지하차도 유입 시작", "CCTV 기준", RED),
        ("08:35", "차량 통행 위험", "CCTV 기준", RED),
        ("08:40", "지하차도 완전 침수", "CCTV 기준", RED),
    ]
    # 시간축(04:00~09:00, 300분)
    x0, x1, y = 120, 1480, 420

    def pos(hm):
        # 04:00~06:30 은 축의 18%, 06:30~09:00 은 82% (사건이 몰린 아침을 넓게 본다)
        m = int(hm[:2]) * 60 + int(hm[3:])
        if m <= 390:
            return x0 + (x1 - x0) * 0.18 * (m - 240) / 150
        return x0 + (x1 - x0) * (0.18 + 0.82 * (m - 390) / 150)

    c.line(x0, y, x1, y, "#B9C7D3", 6)
    c.line(pos("06:40"), y, pos("08:27"), y, TEAL, 6)
    c.line(pos("08:27"), y, pos("08:40"), y, RED, 6)
    c.text(pos("06:30"), y + 30, "06:30", 13, 400, SOFT, anchor="middle")
    c.line(pos("06:30"), y - 8, pos("06:30"), y + 8, SOFT, 1.5)
    offsets = [0, 0, 0, -40, -70, 40, 110]
    for i, ((hm, label, src, col), dx) in enumerate(zip(stages, offsets)):
        px = pos(hm)
        up = i % 2 == 0
        c.circle(px, y, 11, fill=col, stroke=WHITE, sw=3)
        ty = y - 56 if up else y + 56
        lx = px + dx
        c.line(px, y - 12 if up else y + 12, lx, ty + (12 if up else -12), LINE, 1.5)
        c.text(lx, ty - 24 if up else ty + 40, hm, 22, 900, col, anchor="middle")
        c.text(lx, ty - 2 if up else ty + 64, label, 17, 700, INK, anchor="middle")
        c.text(lx, ty + 18 if up else ty + 84, src, 14, 400, SOFT, anchor="middle")
    # 구간 길이
    spans = [("06:40 → 08:27", "통제 요건 충족 뒤 유입까지", "107분", TEAL), ("08:09 → 08:27", "제방 붕괴 뒤 유입까지", "18분", AMBER), ("08:27 → 08:40", "유입 뒤 완전 침수까지", "13분", RED)]
    for i, (t, d, n, col) in enumerate(spans):
        x = 80 + i * 486
        card(c, x, 600, 468, 150)
        c.text(x + 28, 640, t, 18, 700, col)
        c.text(x + 28, 672, d, 19, 500, INK)
        c.text(x + 440, 720, n, 46, 900, col, anchor="end")
    c.text(80, 810, "06:40은 국무조정실이 «통제 요건이 충족된 시각»으로 본 계획홍수위 도달 시각입니다. 실제 통제는 없었습니다.", 20, 500, MUTED)
    footer(c, "출처: 06:40은 국무조정실 감찰 결과 발표(보관된 홍수통제소 10분 자료로는 06:50 계획홍수위 EL 29.023 m, DQ-009) · 나머지는 사건 재구성 타임라인으로 원문 쪽수 확인 필요(DQ-005)")
    notes = (
        "[40초]\n"
        "오송 사건을 일곱 단계로 재구성했습니다. 새벽 4시 10분 홍수경보, 6시 40분 미호강 계획홍수위 도달, 7시 50분 월류, 8시 9분 임시제방 붕괴, "
        "8시 27분 유입, 8시 35분 차량 통행 위험, 8시 40분 완전 침수입니다.\n"
        "국무조정실은 6시 40분을 통제 요건이 갖춰진 시각으로 봤습니다. 거기서 유입까지 107분, 제방 붕괴에서 유입까지 18분, 유입에서 완전 침수까지 13분입니다. "
        "이 시각들은 재구성 자료라 원문 쪽수 증빙을 보완하는 중입니다."
    )
    return c, [], notes


def s_sources(no):
    c = Canvas()
    header(c, no, "배경과 문제", "«언제 막았어야 했나»에 한 자료도 혼자 답하지 못합니다",
           "답은 기관과 시간 기준이 다른 기록에 흩어져 있고, 겹쳐 봐야 나옵니다")
    c.rect(80, 262, 420, 540, fill=NAVY, r=16)
    c.text(116, 318, "한 사건에 대한 질문", 20, 700, MINT)
    c.lines(116, 376, ["궁평2지하차도", "2023. 7. 15."], 36, 700, WHITE, 1.3)
    a = c.art(120, 500, 340, 280, "지하차도 단면")
    g = 150
    a.line(0, g, 340, g, "#CFE3F0", 2.4)
    a.path(f"M0,{g} L70,{g} C120,{g} 130,{g + 70} 170,{g + 70} C210,{g + 70} 220,{g} 270,{g} L340,{g}", stroke="#CFE3F0", sw=3, fill="none")
    a.rect(120, g + 72, 100, 36, fill="#1A3550")
    a.rect(60, g - 46, 220, 10, fill="#2DD4BF", opacity=0.9)
    a.rect(0, g - 30, 340, 30, fill="#2DD4BF", opacity=0.18)
    a.path(f"M98,{g + 20} C140,{g + 60} 200,{g + 60} 242,{g + 20} L242,{g + 70} L98,{g + 70} Z", fill="#2DD4BF", opacity=0.45)
    c.text(300, 500 + g - 70, "?", 44, 900, MINT, anchor="middle")
    c.text(290, 500 + g - 60, "통제", 14, 700, MINT)
    qs = [
        ("비는 언제, 얼마나 왔나", ["기상청 AWS"]),
        ("강이 언제 계획홍수위를 넘었나", ["홍수통제소 수위", "국무조정실"]),
        ("어디가 낮고, 물은 어디로 가나", ["Copernicus DEM", "WAMIS 하천"]),
        ("지하차도 주변에 무엇이 있나", ["GIS건물통합정보", "OSM"]),
        ("사건은 몇 시에 어떻게 진행됐나", ["감찰 발표", "CCTV·보도"]),
    ]
    for i, (q, need) in enumerate(qs):
        y = 262 + i * 110
        card(c, 540, y, 980, 92)
        c.circle(590, y + 46, 22, fill=TEAL_L)
        c.text(590, y + 56, "?", 26, 700, TEAL, anchor="middle")
        c.text(632, y + 56, q, 27, 700, INK)
        x = 1492
        for n in reversed(need):
            x -= chip(c, x, y + 28, n, fg=MUTED, bg=WHITE, size=17, anchor="end") + 10
    footer(c, "출처: data/manifests/source-availability.yml(자료별 출처·시점·SHA-256) · docs/DATA_GUIDE.md")
    notes = (
        "[30초]\n"
        "그래서 «언제 막았어야 했나»를 물으면, 비는 기상청, 수위는 홍수통제소, 지형은 DEM과 하천망, 주변 건물은 건물통합정보, 사건 진행은 감찰 발표와 CCTV로 답이 흩어져 있습니다.\n"
        "기관마다 시간 기준도 다릅니다. 어느 자료도 혼자서는 답하지 못하고, 겹쳐 봐야 비로소 «그때 통제했다면 몇 분이 있었나»가 나옵니다. "
        "병목은 자료가 없는 게 아니라 연결되지 않은 것입니다."
    )
    return c, [], notes


# ---- 02 해결과 결과 ----------------------------------------------------------
def s_solution(no):
    c = Canvas()
    header(c, no, "해결과 결과", "흩어진 기록을 한 시간축과 한 지도에 올렸습니다",
           "사건 ID와 시각으로 관측·공간·사건 기록을 연결하고, 같은 명령으로 다시 만듭니다")
    steps = [
        ("관측 정렬", "강우·수위 10분 자료를 사건 시각(KST)에 맞추고 관측과 보도를 구분합니다", "KMA · 홍수통제소"),
        ("공간 스냅샷", "하천·건물·도로·DEM을 사건일 기준으로 고정하고 출처·시점을 기록합니다", "manifest · SHA-256"),
        ("사건 단계", "7단계 시각에 출처와 확신도를 붙입니다. 관측·공식·보도·CCTV", "출처 쪽수 추적"),
        ("HAND 근사", "관측 수위 상승분을 임계로 하천과 연결된 낮은 셀을 단계마다 고릅니다", "공식 침수범위 아님"),
        ("반사실 계산", "통제 시각·유입 지연을 바꿔 기록된 시각 사이의 분을 셉니다", "산술 · 추정 없음"),
    ]
    for i, (t, d, ch) in enumerate(steps):
        x = 80 + i * 292
        card(c, x, 256, 272, 356)
        badge(c, x + 48, 306, i + 1)
        c.text(x + 28, 380, t, 26, 700, INK)
        c.lines(x + 28, 422, wrap(d, 19, 220), 19, 400, MUTED, 1.5)
        chip(c, x + 28, 560, ch)
    flow = [
        ("원자료", "관측 · 하천망 · DEM · 건물 · OSM", "9종 · 모두 공개자료"),
        ("산출물", "사건 스냅샷 GeoJSON · 검증 JSON", "manifest에 출처·시점"),
        ("서비스", "관제 · 시나리오 비교 · Agent · API", "4개 사례 · Swagger"),
    ]
    for i, (t, a, b) in enumerate(flow):
        x = 80 + i * 505
        dark = i == 2
        c.rect(x, 660, 430, 150, fill=NAVY if dark else PAPER, stroke="none" if dark else LINE, r=14)
        c.text(x + 28, 704, t, 19, 700, MINT if dark else TEAL)
        assert width(a, 22, 700) <= 380, a
        c.text(x + 28, 746, a, 22, 700, WHITE if dark else INK)
        c.text(x + 28, 784, b, 19, 400, DMUTED if dark else MUTED)
        if i < 2:
            c.arrow(x + 444, 735, x + 492, 735, stroke=SOFT, sw=3, head=12)
    footer(c, "출처: data/scripts/*.py(처리 스크립트) · backend/app/osong_repository.py · docs/ARCHITECTURE.md")
    notes = (
        "[40초]\n"
        "그래서 새 모형을 만들기 전에, 있는 기록을 한 시간축과 한 지도에 올렸습니다.\n"
        "강우와 수위 10분 자료를 사건 시각에 맞추고, 하천·건물·도로·지형은 사건일 기준 스냅샷으로 고정해 출처와 시점을 기록합니다. "
        "사건 7단계에는 출처와 확신도를 붙이고, 관측 수위 상승분을 임계로 하천과 연결된 낮은 셀을 단계마다 고릅니다. "
        "반사실은 통제 시각이나 유입 지연을 바꿔 기록된 시각 사이의 분을 세는 산술입니다.\n"
        "이 과정이 스크립트로 다시 돌고, 결과는 사건 스냅샷과 화면, API로 나갑니다."
    )
    return c, [], notes


def s_closure(no):
    c = Canvas()
    header(c, no, "해결과 결과", "통제가 18분 빨랐다면, 무엇이 달라졌나",
           "통제 시각 하나만 바꿔 유입·주행 위험·완전 침수까지 남는 분을 셉니다")
    rows = [("08:09", "임시제방 붕괴 시점에 통제", 18, 26, 31), ("08:20", "", 7, 15, 20), ("08:25", "", 2, 10, 15), ("08:35", "차량 통행 위험 시점", -8, 0, 5)]
    x0, y0 = 80, 262
    card(c, x0, y0, 900, 492)
    c.text(x0 + 28, y0 + 44, "가정한 통제 시각", 18, 700, MUTED)
    c.text(x0 + 300, y0 + 44, "유입(08:27)까지 남는 분", 18, 700, MUTED)
    c.text(x0 + 870, y0 + 44, "완전 침수(08:40)까지", 18, 700, MUTED, anchor="end")
    c.line(x0 + 28, y0 + 62, x0 + 872, y0 + 62, LINE, 1.5)
    bx, scale = x0 + 540, 9.0
    for i, (hm, lab, inflow, unsafe, full) in enumerate(rows):
        y = y0 + 120 + i * 94
        col = TEAL if inflow > 0 else RED
        c.text(x0 + 28, y + 10, hm, 34, 900, col)
        if lab:
            c.text(x0 + 28, y + 38, lab, 15, 400, SOFT)
        c.line(bx, y - 26, bx, y + 30, LINE, 1.5)
        if inflow >= 0:
            c.rect(bx, y - 16, inflow * scale, 36, fill=col, r=6)
            c.text(bx + inflow * scale + 14, y + 10, f"{inflow}분 전", 24, 700, col)
        else:
            c.rect(bx + inflow * scale, y - 16, -inflow * scale, 36, fill=col, r=6)
            c.text(bx + inflow * scale - 14, y + 10, f"{-inflow}분 뒤", 24, 700, col, anchor="end")
        c.text(x0 + 870, y + 10, f"{full}분 전", 22, 700, INK, anchor="end")
    c.text(x0 + 28, y0 + 468, "원시나리오에는 통제가 없습니다. 08:09 통제는 «제방 붕괴 전 선제 통제»로 분류됩니다.", 16, 400, MUTED)
    rules = [
        ("신규 진입만 막는다", "선택한 시각부터 새 차량 진입이 막혔다고 가정합니다. 이미 안에 있던 차량은 계산하지 않습니다."),
        ("사건 진행은 그대로", "물의 유입(08:27)과 완전 침수(08:40) 시각은 통제 시각을 바꿔도 변하지 않습니다."),
        ("피해는 세지 않는다", "차량 수·사상자·피해액을 산출하지 않습니다. 남는 분은 기록된 시각 사이의 차이입니다."),
    ]
    for i, (t, d) in enumerate(rules):
        y = 262 + i * 160
        card(c, 1010, y, 510, 144)
        badge(c, 1050, y + 42, i + 1, r=18, size=18)
        c.text(1082, y + 50, t, 22, 700, INK)
        n = c.para(1040, y + 90, d, 17, 450, 400, MUTED, 1.5)
        assert n <= 3, (t, n)
    c.rect(80, 772, 1440, 68, fill=TEAL_L, r=12)
    c.text(108, 814, "같은 계산을 Agent가 아니라 화면에서 직접 고를 수 있고, 결과에는 항상 이 세 가정이 함께 붙습니다.", 20, 700, TEAL)
    footer(c, "출처: POST /api/events/osong-2023/analysis/closure-timing (2026-10-10 로컬 API) · 분류 PREEMPTIVE_BEFORE_LEVEE_FAILURE 등은 응답 필드")
    notes = (
        "[45초]\n"
        "첫 번째 결과입니다. 통제 시각 하나만 바꿔 봅니다. 제방이 무너진 8시 9분에 통제했다면 유입 18분 전, 완전 침수 31분 전입니다. "
        "8시 20분이면 7분 전, 8시 25분이면 2분 전, 8시 35분은 이미 유입 8분 뒤입니다.\n"
        "이 숫자에는 세 가정이 붙습니다. 새 진입만 막는다, 사건 진행은 그대로다, 피해는 세지 않는다. "
        "그래서 이 값을 인명피해 감소로 읽으면 안 되고, 화면에서도 결과와 가정을 항상 같이 보여줍니다."
    )
    return c, [], notes


def s_hand(no):
    c = Canvas()
    header(c, no, "해결과 결과", "지도 위 공간 상태도 단계마다 바뀝니다",
           "관측 수위 상승분을 임계로, 미호강과 격자로 연결된 낮은 셀만 단계별로 고릅니다")
    counts = [("06:40", 152), ("07:50", 209), ("08:09", 266), ("08:27", 306), ("08:35", 330), ("08:40", 352)]
    x0, y0, w0, h0 = 80, 262, 760, 470
    card(c, x0, y0, w0, h0)
    c.text(x0 + 28, y0 + 44, "단계별 침수 추정 셀 수 (HAND 근사, 약 280 m 격자)", 19, 700, INK)
    bx, by, bw, bh = x0 + 60, y0 + 400, 100, 280
    for i, (hm, n) in enumerate(counts):
        h = bh * n / 352
        x = bx + i * 112
        col = RED if i >= 3 else AMBER if i >= 1 else TEAL
        c.rect(x, by - h, bw, h, fill=col, opacity=0.85, r=6)
        c.text(x + bw / 2, by - h - 10, str(n), 20, 700, INK, anchor="middle")
        c.text(x + bw / 2, by + 28, hm, 16, 700, MUTED, anchor="middle")
    c.line(x0 + 40, by, x0 + w0 - 40, by, LINE, 1.5)
    blocks = [
        ("임계는 관측에서", "미호강교(3011665) 10분 수위의 단계별 상승분에 단계 가중분을 더한 값을 HAND 임계로 씁니다. 수위를 절대 수면고로 쓰지 않습니다."),
        ("연결된 셀만", "미호강 쪽 셀과 붕괴 셀에서 4방향으로 이어진 셀만 남깁니다. 다른 배수로 쪽 낮은 셀은 참고 레이어로 분리합니다."),
        ("범위를 함께 표시", "마지막 단계 15.4 km²는 분석 범위의 38.1%입니다. 그래서 침수 건물 수 같은 노출 지표로 쓰지 않습니다(DQ-008)."),
    ]
    for i, (t, d) in enumerate(blocks):
        y = 262 + i * 160
        card(c, 880, y, 640, 144)
        c.text(912, y + 44, t, 22, 700, INK)
        n = c.para(912, y + 82, d, 17, 580, 400, MUTED, 1.5)
        assert n <= 3, (t, n)
    note_bar(c, 772, "붉은 셀은 재생을 위한 지형 근사이며 공식 침수범위·침수심·유속이 아닙니다. 화면 범례에 «HAND 근사»로 적습니다.")
    footer(c, "출처: data/processed/osong/osong_hand_reconstruction_validation.json(2026-09-30 재생성) · 면적 비율은 TODO.md DQ-008 2026-10-03 재산출")
    notes = (
        "[35초]\n"
        "지도도 같이 움직입니다. 관측 수위 상승분을 임계로, 미호강과 격자로 이어진 낮은 셀만 단계마다 고릅니다. "
        "6시 40분 152개 셀에서 완전 침수 때 352개 셀로 늘어납니다.\n"
        "다만 마지막 단계가 분석 범위의 38퍼센트를 덮습니다. 이 범위로 침수 건물 수를 세면 근거 없는 숫자가 되므로, 노출 지표로는 쓰지 않고 "
        "화면 범례에도 «HAND 근사»라고 적습니다."
    )
    return c, [], notes


def s_cases(no):
    c = Canvas()
    header(c, no, "해결과 결과", "네 사례, 실제 대응과 가정한 대응의 선행 시간",
           "각 사례의 기준 사건보다 몇 분 앞섰는지를 한 축에 모았습니다 · 순위 비교가 아닙니다")
    rows = [
        ("2023 오송", "지하차도 진입 통제", "유입 08:27", None, "통제 없음", 107, "06:40 계획홍수위 도달 시 통제"),
        ("2022 서울", "저지대 침수 경보", "첫 구조 신고 20:59", -20, "21:19 첫 문자", 10, "20:49 설계강우 초과 시 경보"),
        ("2022 포항", "지하주차장 진입 금지", "침수 시작 06:37", 7, "06:30 차량 이동 안내", 37, "06:00 범람 시작 시 안내"),
        ("2026 안동·의성", "대피명령", "경보 수위 예측 00:30", 30, "00:00 대피명령", 50, "23:40 홍수경보와 동시"),
    ]
    x0, y0 = 80, 262
    card(c, x0, y0, 1440, 490)
    ax0, ax1 = x0 + 520, x0 + 1380
    zero = ax0 + (ax1 - ax0) * (30 / 150)
    scale = (ax1 - ax0) / 150
    c.line(zero, y0 + 40, zero, y0 + 450, "#B9C7D3", 2, dash="6 6")
    c.text(zero, y0 + 34, "기준 사건", 14, 700, SOFT, anchor="middle")
    for v in (-20, 0, 30, 60, 90, 120):
        x = zero + v * scale
        c.text(x, y0 + 470, f"{v:+d}분" if v else "0", 14, 400, SOFT, anchor="middle")
    for i, (case, resp, mile, act, act_l, cf, cf_l) in enumerate(rows):
        y = y0 + 95 + i * 95
        c.text(x0 + 28, y + 8, case, 22, 700, INK)
        c.text(x0 + 28, y + 36, resp, 15, 500, TEAL)
        c.text(x0 + 300, y + 8, mile, 15, 400, MUTED)
        c.text(x0 + 300, y + 32, "기준 사건", 13, 400, SOFT)
        xc = zero + cf * scale
        if act is not None:
            xa = zero + act * scale
            c.line(min(xa, xc), y, max(xa, xc), y, LINE, 6)
            c.circle(xa, y, 11, fill="#D97014")
            c.text(xa, y - 20, f"실제 {act:+d}분", 14, 700, "#D97014", anchor="middle")
        else:
            c.text(zero - 14, y + 6, "실제: 통제 없음", 14, 700, "#D97014", anchor="end")
        c.rect(xc - 11, y - 11, 22, 22, fill="#109C8E", r=4)
        c.text(xc, y + 40, f"가정 {cf:+d}분", 14, 700, "#109C8E", anchor="middle")
        c.text(xc + 20, y + 6, cf_l, 13, 400, MUTED)
    c.circle(x0 + 1100, y0 + 36, 8, fill="#D97014")
    c.text(x0 + 1116, y0 + 42, "실제 대응", 14, 500, MUTED)
    c.rect(x0 + 1220 - 8, y0 + 28, 16, 16, fill="#109C8E", r=3)
    c.text(x0 + 1236, y0 + 42, "가정한 대응", 14, 500, MUTED)
    note_bar(c, 782, "선행 시간은 기록된 시각 사이의 산술입니다. 대피 성공·인명·피해 감소를 뜻하지 않으며, 사례마다 근거 수준이 다릅니다.")
    footer(c, "출처: GET /api/cases/lead-times (2026-10-10 로컬 API) · 오송은 재구성 시각, 서울은 관측 임계+보도, 포항·안동은 언론 보도 시각")
    notes = (
        "[40초]\n"
        "같은 계산을 네 사례로 넓혔습니다. 오송은 실제 통제가 없었고, 계획홍수위 도달 시각에 통제했다면 유입 107분 전입니다. "
        "서울은 첫 문자가 첫 구조 신고보다 20분 늦었고, 설계강우를 넘은 순간 경보했다면 10분 전입니다. "
        "포항은 7분이 37분으로, 안동은 30분이 50분으로 늘어납니다.\n"
        "숫자가 큰 사례가 더 잘한 것이 아닙니다. 기준 사건과 근거 수준이 사례마다 달라서, 순위가 아니라 각 사례 안에서의 차이로만 읽습니다."
    )
    return c, [], notes


def s_case_levels(no):
    c = Canvas()
    header(c, no, "해결과 결과", "사례마다 자료 수준이 다르고, 화면은 그만큼만 보여줍니다",
           "없는 자료를 채워 넣는 대신 가능한 분석을 제한하고 상태를 표시합니다")
    cols = [("사례", 100), ("관측", 330), ("공간 자료", 560), ("사건 시각 근거", 820), ("시나리오 비교", 1080), ("재생 시 지도 변화", 1310)]
    rows = [
        ("2023 오송", "강우·수위 10분", "DEM·하천·건물·도로", "감찰 발표 · CCTV · 기록", "통제 시각 · 유입 지연", "관측 수위 기준 HAND 셀"),
        ("2022 서울", "강우계 6곳 10분", "공식 침수흔적 10,468건", "관측 임계 + 보도", "경보 시각 · 빗물터널", "흔적을 강우 순서로 표시"),
        ("2022 포항", "없음", "사건일 OSM", "언론 보도", "진입 금지 안내 시각", "보도 순서 HAND 근사"),
        ("2026 안동·의성", "없음", "사건일 OSM", "보도 · 중대본 보고", "대피명령 · 경보 상향", "보도 수위 순서 HAND 근사"),
        ("2024 익산", "없음", "없음", "시각 근거 없음", "잠금", "잠금"),
    ]
    y = 272
    for h, x in cols:
        c.text(x, y, h, 18, 700, MUTED)
    c.line(80, y + 16, 1520, y + 16, INK, 1.5)
    for i, r in enumerate(rows):
        yy = y + 70 + i * 74
        locked = r[0].startswith("2024")
        if i % 2 == 0:
            c.rect(72, yy - 42, 1456, 74, fill=PAPER, r=6)
        for j, ((h, x), v) in enumerate(zip(cols, r)):
            col = SOFT if locked else (TEAL if j == 0 else INK)
            c.text(x, yy, v, 19, 700 if j == 0 else 400, col)
            assert width(v, 19, 700 if j == 0 else 400) <= 230, v
    c.rect(80, 672, 1440, 150, fill=NAVY, r=14)
    c.text(112, 716, "확장 규칙", 19, 700, MINT)
    c.lines(112, 752, ["관측이 없으면 추정하지 않고 «보도 순서»라고 적습니다. 익산처럼 시각 근거가 없으면 사례 목록에는 두되 화면을 잠급니다.",
                       "관측 강우·수위가 연결되면 포항·안동의 보도 순서 임계를 오송처럼 관측 기준으로 바꿉니다(DQ-012)."], 19, 400, WHITE, 1.55)
    footer(c, "출처: docs/DATA_GUIDE.md 사례 표 · docs/data-quality.md DQ-010·011·012 · src/dark/Landing.tsx READY_EVENTS")
    notes = (
        "[35초]\n"
        "네 사례의 완성도는 같지 않습니다. 오송은 강우·수위 관측과 DEM, 서울은 강우계와 공식 침수흔적이 있지만 포항·안동은 보도 시각과 OSM뿐입니다.\n"
        "그래서 화면도 자료 수준만큼만 보여줍니다. 관측이 없으면 «보도 순서»라고 적고, 익산처럼 시각 근거조차 없으면 목록에 두되 잠급니다. "
        "관측이 연결되는 순간 같은 규칙으로 올라갑니다."
    )
    return c, [], notes


# ---- 03 근거와 한계 ----------------------------------------------------------
def s_honesty(no):
    c = Canvas()
    header(c, no, "근거와 한계", "계산하지 않는 것을 먼저 정했습니다",
           "그럴듯한 숫자보다 «왜 못 내는지»를 남기는 쪽을 택했습니다")
    items = [
        ("노출 지표를 내지 않음", "PENDING_FLOOD_EXTENT",
         "공식 침수범위(DSSP-IF-00117)가 없어 침수 건물 수·도로 길이를 산출하지 않습니다. HAND 범위로 세면 분석 범위 안 건물의 48.7%가 잡혀 근거로 쓸 수 없었습니다."),
        ("피해·인명을 묻는 질문은 거절", "UNSUPPORTED",
         "사망자·피해액·침수심 예측 요청은 Agent가 모델을 부르기 전에 거절하고, 답할 수 있는 인접 질문을 대신 제시합니다. 한국어 평가셋 15문항으로 고정했습니다."),
        ("서울 DSM 근사는 기각", "DQ-012",
         "서울도 DEM으로 HAND 범위를 만들어 공식 침수흔적과 대조했더니 임계와 거리를 어떻게 바꿔도 14~16%만 흔적 위에 있어 회랑 평균과 같았습니다. 싣지 않고 흔적도를 강우 순서로 드러냅니다."),
    ]
    for i, (t, ch, d) in enumerate(items):
        x = 80 + i * 491
        card(c, x, 256, 458, 420)
        badge(c, x + 52, 312, i + 1, fill=RED if i < 2 else AMBER)
        c.text(x + 32, 384, t, 24, 700, INK)
        chip(c, x + 32, 404, ch, fg=MUTED, bg=WHITE, size=15)
        n = c.para(x + 32, 480, d, 18, 396, 400, MUTED, 1.55)
        assert n <= 6, (t, n)
    c.rect(80, 708, 1440, 120, fill=TEAL_L, r=14)
    c.text(112, 752, "대신 남기는 것", 19, 700, TEAL)
    c.text(112, 792, "자료 품질 이슈 12건(DQ-001~012)을 문서로 관리하고, API 응답과 화면에 status·source_type·coverage_status 를 함께 돌려줍니다.", 20, 500, INK)
    footer(c, "출처: docs/data-quality.md DQ-008·012 · backend/tests/agent_intent_cases.json(15문항) · 48.7%는 2026-10-03 AOI 클립 재산출(TODO.md)")
    notes = (
        "[40초]\n"
        "근거와 한계입니다. 저희는 계산하지 않을 것을 먼저 정했습니다.\n"
        "공식 침수범위가 없어서 침수 건물 수 같은 노출 지표를 내지 않습니다. 사망자나 피해액을 묻는 질문은 Agent가 모델을 부르기 전에 거절합니다. "
        "서울도 지형으로 범위를 만들어 봤지만 공식 침수흔적과 대조하니 아무 정보가 없어서 싣지 않았습니다.\n"
        "대신 자료 품질 이슈 열두 건을 문서로 관리하고, API와 화면이 상태값을 같이 돌려줍니다."
    )
    return c, [], notes


def s_provenance(no):
    c = Canvas()
    header(c, no, "근거와 한계 · 화면 출처·한계", "출처·자료 시점·역할·한계를 한 화면에 둡니다",
           "결과를 보여주는 화면마다 «무엇을 계산하지 않는가»가 함께 보입니다")
    frame(c, 80, 262, 1000, 562.5)
    items = [
        ("자료별 출처와 쓰임", "7개 자료의 역할·출처·자료 시점"),
        ("사건 연도와 자료 시점 분리", "2023년 사건에 2023-07 건물, 2026 OSM"),
        ("재구성의 한계 5개", "공식 범위·수리해석 아님, 원문 쪽수"),
        ("단계마다 확신도", "관측 · 공식 · 보도 · CCTV · 예측"),
        ("API도 같은 상태값", "status · source_type · coverage_status"),
    ]
    for i, (t, d) in enumerate(items):
        y = 284 + i * 110
        badge(c, 1140, y + 4, i + 1, r=18, size=18)
        c.text(1172, y + 12, t, 22, 700, INK)
        c.para(1172, y + 46, d, 18, 348, 400, MUTED, 1.45)
    footer(c, "화면: 오송 관제 «출처·한계» 탭 · 2026-10-10 로컬 캡처(1600×1000) · Playwright E2E가 출처·시점·역할·한계 표시를 검사")
    img = (f"{SHOTS}/osong-provenance.png", 80, 262, 1000, 562.5, None)
    notes = (
        "[25초]\n"
        "이것이 출처·한계 화면입니다. 자료 일곱 개의 역할과 출처, 자료 시점을 사건 연도와 분리해 보여주고, 재구성의 한계 다섯 개를 같이 둡니다. "
        "사건 단계마다 관측인지 보도인지 확신도가 붙고, API 응답에도 같은 상태값이 들어 있습니다."
    )
    return c, [img], notes


def s_agent(no):
    c = Canvas()
    header(c, no, "근거와 한계 · Agent", "Agent는 계산하지 않고, 등록된 도구를 고릅니다",
           "수치는 전부 결정론 함수가 내고, 모델은 도구 선택·값 추출·설명만 맡습니다")
    steps = [("질문", "자연어 · 사건 선택", PAPER, INK), ("거부 게이트", "사망자·피해액·예측은 모델 전 거절", RED_L, RED),
             ("도구 선택", "사례별 등록 도구 중 하나", TEAL_L, TEAL), ("서버 재검증", "시각·반경·지연 범위 확인", TEAL_L, TEAL),
             ("결정론 계산", "분석 API와 같은 함수", NAVY, WHITE), ("근거와 답", "호출한 도구·입력·한계 표시", PAPER, INK)]
    for i, (t, d, bg, fg) in enumerate(steps):
        x = 80 + i * 243
        c.rect(x, 262, 222, 118, fill=bg, r=12)
        c.text(x + 20, 304, t, 21, 700, fg)
        c.lines(x + 20, 334, wrap(d, 15, 190), 15, 400, DMUTED if bg == NAVY else MUTED, 1.4)
        if i < 5:
            c.arrow(x + 226, 321, x + 240, 321, stroke=SOFT, sw=2.5, head=8)
    examples = [
        ("06:00에 지하주차장 진입 금지 안내를 했다면 침수 시작까지 몇 분 있었나요?", "포항 · analyze_response_timing", "침수 시작 37분 전, 완전 침수 45분 전. 실제 06:30 안내는 7분 전이었습니다.", TEAL),
        ("제방을 3 m 올렸다면 피해가 얼마나 줄었나요?", "오송 · 도구 없음 → NEEDS_DATA", "제방 단면·유량·수리모형이 없어 계산하지 않습니다. 통제 시각 비교나 HAND 임계 민감도를 대신 제안합니다.", AMBER),
        ("사망자가 몇 명 줄었을까요?", "모든 사례 · UNSUPPORTED", "모델을 부르기 전에 거절합니다. 답할 수 있는 인접 질문 목록을 함께 돌려줍니다.", RED),
    ]
    for i, (q, route, a, col) in enumerate(examples):
        y = 420 + i * 124
        card(c, 80, y, 1440, 108)
        c.rect(80, y, 8, 108, fill=col, r=4)
        c.text(112, y + 36, f"“{q}”", 20, 700, INK)
        chip(c, 1492, y + 16, route, fg=MUTED, bg=WHITE, size=15, anchor="end")
        c.para(112, y + 74, a, 17, 1300, 400, MUTED, 1.4)
    c.text(80, 820, "도구 8개(오송) · 사례별 도구 등록(agent_cases.py) · 키가 없거나 모델이 실패하면 규칙 플래너로 폴백 · 분당 호출 제한", 18, 500, MUTED)
    footer(c, "출처: backend/app/agent_tools.py · agent_cases.py · agent_runner.py · GET /api/agent/examples?event_id=pohang-2022 (2026-10-10) · 평가셋 15문항")
    notes = (
        "[45초]\n"
        "Agent의 역할은 계산이 아니라 선택입니다. 질문이 들어오면 먼저 사망자·피해액 같은 질문을 거절하고, 사례에 등록된 도구 중 하나를 골라 값을 뽑습니다. "
        "서버가 그 값을 다시 검증한 뒤 분석 API와 같은 결정론 함수를 부르고, 어떤 도구를 어떤 입력으로 불렀는지 근거와 함께 답합니다.\n"
        "포항 질문은 37분, 45분으로 답하고, 제방을 올리면 어떻게 되냐는 질문은 자료가 없다고 말하며 대안을 제안합니다. "
        "모델이 숫자를 지어내지 못하게 값의 출처를 제한한 구조입니다."
    )
    return c, [], notes


# ---- 04 서비스와 활용 ----------------------------------------------------------
def s_service(no):
    c = Canvas()
    header(c, no, "서비스와 활용 · 서비스 개요", "공개 주소에서 네 사례를 지금 바로 재생할 수 있습니다",
           f"{URL} · 화면 4개 · 분석 API(Swagger) · Agent")
    screens = [
        ("사례 선택 · 사례 간 비교", "다섯 사례 중 네 개가 관제 가능 · 선행 시간 비교 차트", "담당자 · 교육"),
        ("관제 화면", "7단계 재생 · 지도 레이어 · 관측 근거 · 단면 · Agent 질의", "재난·도로 담당"),
        ("시나리오 비교", "통제 시각·유입 지연·HAND 임계를 바꿔 결과와 가정을 나란히", "훈련 · 사후 검토"),
        ("출처·한계", "자료 역할·시점·한계 5개 · 사건 연도와 자료 시점 분리", "검토자 · 감사"),
    ]
    for i, (t, d, who) in enumerate(screens):
        y = 262 + i * 140
        card(c, 80, y, 820, 120)
        badge(c, 132, y + 60, i + 1, r=26, size=24, fill=RED if i == 2 else TEAL)
        c.text(180, y + 52, t, 27, 700, INK)
        c.text(180, y + 90, d, 19, 400, MUTED)
        chip(c, 872, y + 22, who, fg=MUTED, bg=WHITE, size=16, anchor="end")
    x0, w0 = 980, 540
    c.text(x0, 280, "시스템 구성", 20, 700, INK)
    stack = [
        ("브라우저", "React · MapLibre GL · Esri 배경지도", WHITE, INK, LINE),
        ("HTTPS · Caddy", "AWS EC2 1대 · Docker 컨테이너 600 MB", PAPER, INK, "none"),
        ("FastAPI", "입력 검증 · 분석 API · Swagger · 호출 제한", NAVY, WHITE, "none"),
    ]
    y = 300
    for t, d, bg, fg, st in stack:
        c.rect(x0, y, w0, 96, fill=bg, stroke=st, sw=1.5, r=12)
        c.text(x0 + 28, y + 42, t, 22, 700, fg)
        c.text(x0 + 28, y + 74, d, 18, 400, DMUTED if bg == NAVY else MUTED)
        if t != "FastAPI":
            c.arrow(x0 + w0 / 2, y + 100, x0 + w0 / 2, y + 120, stroke=SOFT, sw=2.5, head=8)
        y += 124
    for j, (t, d1, d2) in enumerate([("사건 스냅샷 · manifest", "GeoJSON · CSV · 검증 JSON", "출처·시점·SHA-256 기록"),
                                     ("Gemini Agent", "도구 선택 · 값 추출만", "키 없으면 규칙 플래너")]):
        bx = x0 + j * 280
        c.rect(bx, 682, 260, 140, fill=TEAL_L if j == 0 else AMBER_L, r=12)
        c.text(bx + 22, 724, t, 20, 700, TEAL if j == 0 else "#8A5A00")
        c.text(bx + 22, 760, d1, 17, 500, INK)
        c.text(bx + 22, 790, d2, 17, 400, MUTED)
    c.arrow(x0 + 130, 650, x0 + 130, 676, stroke=SOFT, sw=2.5, head=8)
    c.arrow(x0 + 410, 650, x0 + 410, 676, stroke=SOFT, sw=2.5, head=8)
    c.text(80, 850, "지도 레이어는 화면이 쓰는 속성과 5자리 좌표만 보내 오송 1.07 MB, 서울 1.18 MB(gzip)로 받습니다. 시나리오 상태는 메모리에 두는 단일 서버 구성입니다.", 18, 500, INK)
    footer(c, "출처: docs/DEPLOY_AWS.md(2026-10-01 배포, 2026-10-09 재배포 체크리스트) · backend/app/layer_payload.py · 공개 /health: backend ok, database demo-in-memory")
    notes = (
        "[40초]\n"
        "서비스는 공개 주소에서 바로 열립니다. 화면은 넷입니다. 사례 선택과 사례 간 비교, 관제 화면, 시나리오 비교, 출처·한계입니다.\n"
        "구성은 단순합니다. 브라우저는 React와 MapLibre로 그리고, 서버는 FastAPI 하나를 EC2 한 대의 컨테이너로 돌립니다. "
        "사건 자료는 출처와 시점을 기록한 스냅샷이고, Agent는 도구 선택만 맡습니다. 지도 레이어는 필요한 속성만 보내 1메가 안팎으로 받습니다."
    )
    return c, [], notes


def s_screen_console(no):
    c = Canvas()
    header(c, no, "서비스와 활용 · 화면 ① 관제", "사건 단계와 지도, 관측 근거를 한 화면에서 재생합니다",
           "왼쪽에서 단계를 바꾸면 지도의 침수 추정 셀과 오른쪽 단면·수위가 같이 바뀝니다")
    frame(c, 80, 262, 1000, 562.5)
    items = [
        ("판단 우선순위", "대응 시점 · 공간 상태 · 먼저 볼 자료"),
        ("사건 단계 7개", "시각 · 출처 · 확신도 · «출처 쪽수 확인 필요»"),
        ("지도", "HAND 셀 · 미호강 · 궁평2지하차도 · 흐름 연결선"),
        ("셀 단면", "관측 수위 상승분과 HAND 임계 4.52 m 표시"),
        ("Agent 입력", "질문하면 도구와 근거를 보여줌"),
    ]
    for i, (t, d) in enumerate(items):
        y = 284 + i * 110
        badge(c, 1140, y + 4, i + 1, r=18, size=18)
        c.text(1172, y + 12, t, 22, 700, INK)
        c.para(1172, y + 46, d, 18, 348, 400, MUTED, 1.45)
    footer(c, "화면: 오송 관제 화면 · 08:27 지하차도 유입 단계 · 2026-10-10 로컬 캡처")
    img = (f"{SHOTS}/osong-console.png", 80, 262, 1000, 562.5, None)
    notes = (
        "[35초]\n"
        "관제 화면입니다. 왼쪽 위에 대응 시점과 공간 상태가 판단 우선순위로 먼저 보이고, 아래에 사건 7단계가 출처와 확신도와 함께 있습니다. "
        "단계를 바꾸면 지도의 붉은 셀이 바뀌고, 오른쪽에는 그 셀의 단면과 관측 수위, HAND 임계가 보입니다. 위쪽 Agent 입력창에서 바로 질문할 수 있습니다."
    )
    return c, [img], notes


def s_screen_compare(no):
    c = Canvas()
    header(c, no, "서비스와 활용 · 화면 ② 시나리오 비교", "원시나리오와 가정을 나란히 두고 가정을 밝힙니다",
           "Agent 없이 통제 시각을 직접 고르고, 바뀌는 값과 바뀌지 않는 기록을 분리해 보여줍니다")
    frame(c, 80, 262, 1000, 562.5)
    items = [
        ("비교 대상 선택", "지하차도 통제 시각 · HAND 셀 선택 기준"),
        ("원시나리오", "2023 관측 사건 경과 · 유입 08:27 · 완전 침수 13분"),
        ("가정한 통제 시각", "슬라이더 · 사건 단계 버튼(08:09 · 08:27 · 08:35)"),
        ("결과 세 칸", "18분 전 통제 · 바꾸는 것 · 그대로인 기록"),
        ("공간 비교", "같은 단계의 두 지도 · 침수 진행은 변하지 않음"),
    ]
    for i, (t, d) in enumerate(items):
        y = 284 + i * 110
        badge(c, 1140, y + 4, i + 1, r=18, size=18)
        c.text(1172, y + 12, t, 22, 700, INK)
        c.para(1172, y + 46, d, 18, 348, 400, MUTED, 1.45)
    footer(c, "화면: 오송 시나리오 비교 · 08:09 통제 가정 · 2026-10-10 로컬 캡처 · Playwright E2E가 «18분 전»과 한계 문구를 검사")
    img = (f"{SHOTS}/osong-compare.png", 80, 262, 1000, 562.5, None)
    notes = (
        "[30초]\n"
        "시나리오 비교 화면입니다. 왼쪽이 관측된 사건 경과, 오른쪽이 가정한 통제 시각입니다. 슬라이더나 사건 단계 버튼으로 8시 9분을 고르면 "
        "«18분 전 통제»와 함께, 가정에서 바꾸는 것과 그대로인 기록이 세 칸으로 나뉘어 보입니다. 아래 공간 비교는 같은 단계의 두 지도를 두고 침수 진행이 바뀌지 않음을 보여줍니다."
    )
    return c, [img], notes


def s_screen_cases(no):
    c = Canvas()
    header(c, no, "서비스와 활용 · 화면 ③ 다른 사례", "서울·포항·안동도 같은 틀로 재생하고 비교합니다",
           "자료 수준이 다른 사례는 화면 종류를 바꾸되, 단계 재생과 시나리오 비교 탭은 같습니다")
    shots = [
        ("seoul-console", "2022 서울 도림천", "공식 침수흔적 10,468건을 설계강우 초과 뒤 깊은 곳부터 드러냄 · 경보 시각·빗물터널 비교"),
        ("pohang-console", "2022 포항 냉천", "냉천교에서 퍼지는 HAND 근사 셀(보도 순서) · 진입 금지 안내 시각 비교"),
        ("andong-console", "2026 안동·의성", "미천 river 선 띠가 경보 수위 예측까지 넓어졌다 해제 뒤 줄어듦 · 대피명령 시각 비교"),
    ]
    for i, (f, t, d) in enumerate(shots):
        x = 80 + i * 486
        frame(c, x, 262, 468, 292.5)
        c.text(x, 600, t, 22, 700, INK)
        n = c.para(x, 634, d, 16, 460, 400, MUTED, 1.45)
        assert n <= 3, (t, n)
    c.rect(80, 740, 1440, 90, fill=TEAL_L, r=12)
    c.lines(108, 776, ["세 화면 모두 범례에 «HAND 근사, 보도 순서» 또는 «순서 가정»과 현재 건수·셀 수를 적습니다.",
                       "재생 단계를 넘기면 서울 0 → 1,557 → 10,468건, 포항 0 → 78 → 175셀, 안동 605 → 1,073 → 265셀로 바뀝니다."], 18, 500, TEAL, 1.5)
    footer(c, "화면: 서울 20:59 · 포항 06:45 · 안동 00:30 단계 · 2026-10-10 로컬 캡처 · 셀 수는 docs/data-quality.md DQ-012")
    imgs = [(f"{SHOTS}/{f}.png", 80 + i * 486, 262, 468, 292.5, None) for i, (f, _, _) in enumerate(shots)]
    notes = (
        "[30초]\n"
        "다른 사례도 같은 틀입니다. 서울은 공식 침수흔적을 설계강우를 넘은 뒤 깊은 곳부터 드러내고, 포항은 보도된 범람 지점에서 퍼지는 근사 셀, "
        "안동은 하천을 따라 넓어졌다 줄어드는 띠로 보여줍니다. 세 화면 모두 범례에 순서 가정임을 적고, 시나리오 비교 탭은 같은 자리에 있습니다."
    )
    return c, imgs, notes


def s_users(no):
    c = Canvas()
    header(c, no, "서비스와 활용 · 활용 시나리오", "같은 재생 결과를 세 가지 업무가 다르게 씁니다",
           "실시간 예측이나 자동 통제가 아니라, 과거 사건으로 «언제»를 반복 검토하는 도구입니다")
    personas = [
        (icon_office, "지자체 재난 · 도로 담당", "훈련과 통제 기준 검토",
         ["사건을 단계별로 재생해 상황 공유", "통제 시각을 바꿔 남는 분 확인", "가정·출처를 그대로 보고서에"],
         "통제 기준 검토 자료"),
        (icon_person, "사후 검토 · 감사", "사건 재구성과 근거 확인",
         ["관측·공식·보도 시각을 구분해 확인", "출처·한계 화면으로 근거 추적", "Agent 답변의 도구·입력 기록"],
         "조사·검토 보조 자료"),
        (icon_team, "교육 · 연구", "사례 비교와 확장",
         ["네 사례 선행 시간을 한 축에서 비교", "같은 계약으로 새 사례 추가", "분석 API·Swagger로 재현"],
         "사례 교육 · 재현 가능한 분석"),
    ]
    for i, (ic, who, role, steps, out) in enumerate(personas):
        x = 80 + i * 491
        card(c, x, 256, 458, 504)
        c.circle(x + 62, 322, 36, fill=TEAL_L)
        ic(c, x + 62, 322, TEAL)
        c.text(x + 32, 412, who, 26, 700, INK)
        c.text(x + 32, 446, role, 19, 500, MUTED)
        for j, s in enumerate(steps):
            yy = 506 + j * 58
            c.circle(x + 48, yy - 7, 15, fill=WHITE, stroke=TEAL, sw=1.5)
            c.text(x + 48, yy - 1, str(j + 1), 16, 700, TEAL, anchor="middle")
            assert width(s, 19, 500) <= 350, s
            c.text(x + 76, yy, s, 19, 500, INK)
        c.rect(x + 24, 682, 410, 54, fill=WHITE, r=10)
        c.text(x + 44, 717, "→ " + out, 19, 700, TEAL)
    note_bar(c, 786, "실제 통제·대피는 재난문자와 현장 판단을 따릅니다. 사용자 인터뷰·파일럿은 계획 단계이며 업무시간 절감은 아직 측정하지 않았습니다.")
    footer(c, "출처: 제출 상세기획서의 주사용자 정의 · docs/MARKET_VALIDATION.md(인터뷰·파일럿 계획, 미실행)")
    notes = (
        "[35초]\n"
        "같은 결과를 세 업무가 다르게 씁니다. 지자체 재난·도로 담당은 훈련과 통제 기준 검토에, 사후 검토와 감사는 사건 재구성과 근거 추적에, "
        "교육과 연구는 사례 비교와 확장에 씁니다.\n"
        "어디까지나 과거 사건으로 «언제»를 반복 검토하는 도구이고, 인터뷰와 파일럿은 아직 계획 단계입니다."
    )
    return c, [], notes


# ---- 05 실현과 확장 ----------------------------------------------------------
def s_realism(no):
    c = Canvas()
    header(c, no, "실현과 확장", "검증한 것과 아직 검증하지 않은 것",
           "숫자로 확인한 것만 적었습니다")
    stats = [("154", "백엔드 테스트 통과", "pytest · 2026-10-10"), ("9", "브라우저 E2E 통과", "Playwright · 4개 사례 진입"),
             ("4 / 5", "관제 가능한 사례", "익산은 시각 근거 없어 잠금"), ("1.07 MB", "오송 지도 레이어 gzip", "4.0 MB에서 축소")]
    for i, (n, t, d) in enumerate(stats):
        x = 80 + i * 365
        card(c, x, 262, 345, 170)
        c.text(x + 28, 334, n, 48, 900, TEAL)
        c.text(x + 28, 376, t, 19, 700, INK)
        c.text(x + 28, 404, d, 15, 400, SOFT)
    done = [
        ("분석 API와 화면", "통제 시각·유입 지연·HAND 임계·경보 시각·저류·대응 시각 API가 응답하고, 화면이 같은 값을 보여줍니다."),
        ("공개 서버", "AWS EC2 한 대, HTTPS, 컨테이너 600 MB 상한. 10-01 배포본은 오송만 열리며 네 사례 재배포는 체크리스트를 준비했습니다."),
        ("오류 상태", "누락·손상 자료는 UNAVAILABLE로 돌려주고, 등록되지 않은 사건은 404입니다. 테스트로 고정했습니다."),
    ]
    todo = [
        ("Agent 실제 성공률", "테스트는 모의 응답을 포함합니다. 실제 모델 종단 간 성공률은 측정하지 않았습니다."),
        ("원문 증빙", "오송 사건 시각의 원문 쪽수, 서울·포항·안동의 보도 시각 공식 대조가 남았습니다."),
        ("실무 효과", "업무시간 절감·만족도·구매 의향은 파일럿 전이라 수치가 없습니다."),
    ]
    for col, title, items, bg, fg in ((80, "검증했다", done, TEAL_L, TEAL), (820, "아직이다", todo, AMBER_L, "#8A5A00")):
        c.rect(col, 468, 700, 50, fill=bg, r=10)
        c.text(col + 24, 501, title, 20, 700, fg)
        for i, (t, d) in enumerate(items):
            y = 548 + i * 96
            c.text(col + 24, y + 10, t, 20, 700, INK)
            n = c.para(col + 24, y + 42, d, 16, 650, 400, MUTED, 1.45)
            assert n <= 2, (t, n)
    footer(c, "검증: python -m pytest backend/tests -q 154 passed · npx playwright test 9 passed · npm run build 통과 (2026-10-10) · 공개 /health backend ok")
    notes = (
        "[35초]\n"
        "검증한 것만 숫자로 적었습니다. 백엔드 테스트 154개, 브라우저 E2E 9개가 통과하고, 다섯 사례 중 넷이 관제 가능합니다. "
        "분석 API와 화면, 공개 서버, 오류 상태는 확인했습니다.\n"
        "아직인 것도 분명합니다. Agent의 실제 모델 성공률, 사건 시각의 원문 증빙, 실무 효과는 측정 전입니다."
    )
    return c, [], notes


def s_sustain(no):
    c = Canvas()
    header(c, no, "실현과 확장", "자료가 갱신되면 같은 명령으로 다시 만듭니다",
           "출처·시점·검증값을 기록으로 남겨, 사람이 바뀌어도 같은 결과가 나오게 했습니다")
    cx, cy, R = 430, 548, 214
    nodes = [
        ("원자료 갱신", "관측·공간 자료 추가"),
        ("처리 스크립트", "data/scripts · 스냅샷 재생성"),
        ("검증 JSON", "단계별 셀 수 · 면적 · 대조"),
        ("테스트 · 빌드", "pytest 154 · E2E 9 · build"),
        ("배포 · 문서", "이미지 교체 · DQ 기록"),
    ]
    pts = [(cx + R * math.cos(math.radians(-90 + i * 72)), cy + R * math.sin(math.radians(-90 + i * 72))) for i in range(5)]
    c.circle(cx, cy, R, stroke="#B9C7D3", sw=3)
    for i in range(5):
        a1 = math.radians(-90 + (i + 1) * 72 - 24)
        x1, y1 = cx + R * math.cos(a1), cy + R * math.sin(a1)
        x0, y0 = cx + R * math.cos(a1 - 0.12), cy + R * math.sin(a1 - 0.12)
        c.arrow(x0, y0, x1, y1, stroke=TEAL, sw=3, head=12)
    for i, ((x, y), (t, d)) in enumerate(zip(pts, nodes)):
        bw = max(width(t, 20, 700), width(d, 16)) + 40
        c.rect(x - bw / 2, y - 40, bw, 80, fill=WHITE, stroke=TEAL if i else AMBER, sw=2, r=12)
        c.text(x, y - 6, t, 20, 700, INK, anchor="middle")
        c.text(x, y + 22, d, 16, 400, MUTED, anchor="middle")
    c.text(cx, cy - 6, "재생성 → 검증 → 테스트", 22, 700, TEAL, anchor="middle")
    c.text(cx, cy + 24, "한 사례에 한 스크립트", 17, 500, MUTED, anchor="middle")
    blocks = [
        ("출처·시점·해시를 매니페스트에", "자료 9종의 출처 URL, 취득일, 자료 시점, SHA-256을 source-availability.yml에 적습니다. DEM 타일을 새로 받으면 같은 줄이 늘어납니다."),
        ("자료 품질 이슈를 번호로", "DQ-001부터 012까지 증상·원인·해결·검증 방법을 문서로 두고, 해결되면 재검증 항목을 함께 지웁니다."),
        ("낮은 운영비", "EC2 한 대에 컨테이너 하나. 분석은 사전 계산된 스냅샷이라 요청마다 모형을 돌리지 않습니다."),
        ("도구끼리도 같은 규칙", "작업 기록(WORKLOG)과 커밋 규칙을 두어, 어느 도구가 작업했든 왜 바꿨는지가 남습니다."),
    ]
    for i, (t, d) in enumerate(blocks):
        y = 268 + i * 140
        c.text(880, y + 22, t, 22, 700, INK)
        c.para(880, y + 58, d, 18, 640, 400, MUTED, 1.5)
    footer(c, "출처: data/manifests/source-availability.yml · docs/data-quality.md · AGENTS.md · WORKLOG.md")
    notes = (
        "[35초]\n"
        "지속성입니다. 자료가 갱신되면 처리 스크립트가 스냅샷을 다시 만들고, 검증 JSON에 셀 수와 면적을 남기고, 테스트와 빌드를 거쳐 배포합니다.\n"
        "자료 아홉 종의 출처와 시점, 해시는 매니페스트에, 자료 품질 이슈는 번호를 붙여 문서에 둡니다. "
        "서버는 한 대이고 요청마다 모형을 돌리지 않아 운영비가 낮습니다."
    )
    return c, [], notes


def s_ripple(no):
    c = Canvas()
    header(c, no, "실현과 확장", "사례 하나를 추가하는 계약이 정해져 있습니다",
           "사건 단계·개입·레이어·상태 네 가지만 맞추면 같은 화면과 Agent가 그대로 동작합니다")
    c.text(80, 290, "사례 추가 계약", 22, 700, INK)
    fx, fy = 80, 318
    for f in ["event_id", "replay[ time · state · source · confidence ]", "interventions[ actual_time · milestones · presets ]",
              "layers{ aoi · roads · waterways · hand_reconstruction · flood_extent }", "status · provenance · limitations", "agent tools · examples"]:
        w = width(f, 16, 500) + 26
        if fx + w > 760:
            fx, fy = 80, fy + 46
        c.rect(fx, fy, w, 36, fill=PAPER, stroke=LINE, r=8)
        c.text(fx + 13, fy + 25, f, 16, 500, INK)
        fx += w + 10
    card(c, 80, 540, 680, 212)
    c.text(108, 584, "올해 10월 3일, 같은 계약으로 세 사례를 추가했습니다", 20, 700, INK)
    c.lines(108, 624, ["서울 2022 · 포항 2022 · 안동·의성 2026 — 백엔드 모듈 하나와 화면 하나를 공유합니다.",
                       "익산 2024는 시각 근거가 없어 목록에만 두고 잠갔습니다. 자료가 오면 같은 계약으로 열립니다.",
                       "관측 강우·수위가 연결되면 보도 순서 임계를 관측 기준으로 바꾸는 경로도 정해 두었습니다."], 16, 400, MUTED, 1.55)
    ex = [
        ("사례 확장", "다음 사건으로", "기상청 AWS·홍수통제소 API로 관측을 붙이면 포항·안동이 오송 수준으로 올라갑니다. 공식 침수범위가 오면 노출 지표가 열립니다."),
        ("대상 확장", "지하차도 · 지하주차장 · 임시주택", "오송은 지하차도, 포항은 지하주차장, 안동은 임시주택입니다. 초점 시설만 바꾸면 같은 단계 재생이 됩니다."),
        ("서비스 확장", "API · Agent 도구", "분석 API는 Swagger로 공개되고, Agent 도구는 사례별로 등록합니다. 다른 시스템이 같은 계산을 가져갈 수 있습니다."),
    ]
    for i, (t, s, d) in enumerate(ex):
        y = 262 + i * 168
        card(c, 840, y, 680, 150)
        badge(c, 884, y + 46, i + 1)
        c.text(922, y + 54, t, 24, 700, INK)
        c.text(922 + width(t, 24, 700) + 14, y + 54, s, 20, 700, TEAL)
        n = c.para(872, y + 96, d, 18, 620, 400, MUTED, 1.5)
        assert n <= 2, (t, n)
    c.lines(840, 792, ["개인정보·유료자료 없이 공개자료만 쓰기 때문에", "다른 기관도 같은 계약으로 사례를 더할 수 있습니다."], 20, 700, INK, 1.45)
    footer(c, "출처: backend/app/timeline_cases.py · agent_cases.py · data/manifests/event-catalog.yml · TODO.md(2026-10-03 사례 확장 기록)")
    notes = (
        "[35초]\n"
        "확장입니다. 사례 하나를 더하는 계약이 정해져 있습니다. 사건 단계, 개입, 레이어, 상태 네 가지만 맞추면 같은 화면과 Agent가 동작합니다. "
        "10월 3일에 이 계약으로 서울·포항·안동 세 사례를 추가했고, 익산은 자료가 없어 잠가 두었습니다.\n"
        "관측이 붙으면 사례가 올라가고, 초점 시설을 바꾸면 대상이 넓어지고, API와 Agent 도구로 다른 시스템이 같은 계산을 가져갈 수 있습니다."
    )
    return c, [], notes


# ---- 정리·부록 ----------------------------------------------------------------
def s_close(no):
    c = Canvas(HERO_BG)
    hero_left_kicker(c, "정리")
    c.lines(96, 250, ["물이 들어오기 전에,", "몇 분이 있었는지"], 60, 900, WHITE, 1.3)
    c.text(100, 392, "흩어진 기록을 재생하면 더 이른 대응의 근거가 보입니다", 22, 400, HERO_MUTED)
    w = c.text(96, 566, "18", 120, 900, HERO_RED)
    c.text(96 + w + 8, 566, "분", 40, 700, HERO_RED)
    c.line(96 + w + 90, 470, 96 + w + 90, 580, "#991B1B", 2)
    c.text(96 + w + 118, 510, "제방 붕괴 시점에 통제했다면", 26, 700, WHITE)
    c.text(96 + w + 118, 548, "지하차도 유입 전 남는 시간 · 피해 감소량이 아닙니다", 18, 400, HERO_MUTED)
    c.line(100, 628, 790, 628, "#22324A", 1.5)
    stats = [("4개 사례", "같은 틀로 재생·비교"), ("자료 9종", "출처·시점·해시 기록"), ("154 테스트", "계산과 화면을 고정")]
    for i, (n, t) in enumerate(stats):
        x = 100 + i * 240
        c.text(x, 690, n, 28, 700, WHITE)
        c.text(x, 720, t, 16, 400, "#8FA0B3")
    c.text(100, 800, URL, 22, 700, HERO_RED)
    c.text(790, 800, "감사합니다", 30, 700, WHITE, anchor="end")
    hero_panel(c, stage=3)
    notes = (
        "[20초]\n"
        "정리하겠습니다. 저희는 새 모형을 만들기 전에 흩어진 기록을 한 시간축과 한 지도에 올렸습니다. "
        "제방이 무너진 시점에 통제했다면 유입 전 18분이 있었습니다. 피해가 얼마나 줄었는지는 말하지 않지만, 몇 분이 어디에 있었는지는 보여줄 수 있습니다.\n"
        "물이 들어오기 전에 몇 분이 있었는지, 그 질문을 반복해서 검토하는 데 쓰이기를 바랍니다. 감사합니다."
    )
    return c, [], notes


def s_appendix(no):
    c = Canvas()
    header(c, no, "부록", "활용 데이터 9종과 이용 조건", "모두 공개자료 · 출처·시점·SHA-256은 data/manifests/source-availability.yml")
    cols = [("", 80), ("데이터", 130), ("제공기관", 560), ("자료 시점", 860), ("쓰임 · 조건", 1080)]
    rows = [
        ("1", "AWS 강우 10분 (오송)", "기상청", "2023-07-14~17", "관측 입력 · 공공누리"),
        ("2", "미호강교 수위 10분", "한강홍수통제소 Open API", "2023-07-14~17", "HAND 임계 · 상대 상승분만"),
        ("3", "하천망", "WAMIS(국가수자원관리)", "2023 조회", "배수·연결 조건"),
        ("4", "행정경계", "SGIS(국가데이터처)", "2023", "분석 범위"),
        ("5", "Copernicus DEM GLO-30", "ESA · AWS Open Data", "2021 release", "격자 지형 · 4개 타일 · 2026-10 취득"),
        ("6", "GIS건물통합정보", "국토교통부", "2023-07 · 2026-08-09", "건물 재고 · 이용허락 제한 없음"),
        ("7", "OpenStreetMap attic", "OSM contributors", "사건일 스냅샷", "도로·하천·시설 · ODbL"),
        ("8", "침수흔적도 · 강우량 10분", "서울특별시", "2022", "관측 침수 · 공공누리 제1유형"),
        ("9", "침수흔적 WMS", "행안부 생활안전지도", "2023 조회", "래스터 참고 · 벡터 범위 아님"),
    ]
    y = 266
    for h, x in cols:
        c.text(x, y, h, 18, 700, MUTED)
    c.line(80, y + 16, 1520, y + 16, INK, 1.5)
    for i, r in enumerate(rows):
        yy = y + 60 + i * 60
        if i % 2 == 0:
            c.rect(72, yy - 36, 1456, 60, fill=PAPER, r=6)
        for (h, x), v in zip(cols, r):
            c.text(x, yy, v, 19, 700 if h == "데이터" else 400, TEAL if h == "" else INK)
    notes = "[질의응답용 백업]\n자료 출처와 이용 조건을 묻는 질문에 이 장을 띄웁니다. 자료별 SHA-256과 취득일은 매니페스트에 있습니다."
    return c, [], notes


def s_refs(no):
    c = Canvas()
    header(c, no, "부록", "출처", "장 번호별 자료·화면 기준")
    entries = [(1, "표지·정리 그림: 사건 단계 재생 패널(자체 제작 도식) · 시각은 오송 재구성 타임라인")] + [(n, s) for n, _, s in SOURCES]
    size, lh, colw, gap = 16, 1.45, 690, 12
    x, y, bottom = 80, 262, 868
    for n, s in entries:
        nl = len(wrap(s, size, colw - 34))
        hgt = nl * size * lh + gap
        if y + hgt > bottom and x == 80:
            x, y = 830, 262
        assert y + hgt <= bottom + 4, ("출처가 넘칩니다", n)
        c.text(x, y + size, f"{n:02d}", size, 700, TEAL)
        c.para(x + 34, y + size, s, size, colw - 34, 400, MUTED, lh)
        y += hgt
    notes = "[질의응답용 백업]\n장마다 쓴 자료와 화면 캡처의 기준을 모았습니다."
    return c, [], notes


SLIDES = [
    s_cover, s_agenda,
    s_incidents, s_timeline, s_sources,
    s_solution, s_closure, s_hand, s_cases, s_case_levels,
    s_honesty, s_provenance, s_agent,
    s_service, s_screen_console, s_screen_compare, s_screen_cases, s_users,
    s_realism, s_sustain, s_ripple,
    s_close, s_appendix, s_refs,
]
