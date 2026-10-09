"""발표 장면 기록 도구.

장면은 1600 x 900 px 좌표로 그린다(PowerPoint 13.333in 폭 기준 1px = 0.6pt).

- Canvas: 글자·사각형·원·선·화살표를 **PowerPoint 기본 개체**로 남긴다. 발표 파일에서 바로 고칠 수 있다.
- Art: 단면도·아이콘처럼 도형이 복잡한 그림만 SVG 로 그린다. 그림 안 글자는 Noto Sans KR 윤곽선이다.

글자 폭은 Noto Sans KR 글리프 폭으로 재서 배치와 줄바꿈을 계산한다.
"""
from __future__ import annotations

import math
from html import escape
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

W, H = 1600, 900
HERE = Path(__file__).resolve().parent
CACHE = HERE / ".fontcache"
FONT_DIR = Path("C:/Windows/Fonts")
FAMILY = "Noto Sans KR"


def _load(weight: int) -> TTFont:
    static = {400: "NotoSansKR-Regular.ttf", 700: "NotoSansKR-Bold.ttf"}
    if weight in static:
        return TTFont(FONT_DIR / static[weight])
    CACHE.mkdir(exist_ok=True)
    cached = CACHE / f"NotoSansKR-w{weight}.ttf"
    if not cached.exists():
        from fontTools.varLib.instancer import instantiateVariableFont

        vf = TTFont(FONT_DIR / "NotoSansKR-VF.ttf")
        instantiateVariableFont(vf, {"wght": weight}, inplace=True)
        vf.save(cached)
    return TTFont(cached)


class _Face:
    def __init__(self, weight: int):
        self.font = _load(weight)
        self.cmap = self.font.getBestCmap()
        self.gs = self.font.getGlyphSet()
        self.hmtx = self.font["hmtx"]
        self.upm = self.font["head"].unitsPerEm

    def glyph(self, ch: str) -> str:
        return self.cmap.get(ord(ch)) or ".notdef"

    def advance(self, text: str) -> float:
        return sum(self.hmtx[self.glyph(c)][0] for c in text)

    def outline(self, text: str) -> str:
        pen = SVGPathPen(self.gs)
        x = 0.0
        for ch in text:
            g = self.glyph(ch)
            self.gs[g].draw(TransformPen(pen, (1, 0, 0, -1, x, 0)))
            x += self.hmtx[g][0]
        return pen.getCommands()


_FACES: dict[int, _Face] = {}


def face(weight: int) -> _Face:
    # 발표 파일은 Regular·Bold 두 굵기만 쓴다(PowerPoint 가 가변 폰트 굵기를 고르지 못한다).
    weight = 700 if weight >= 600 else 400
    if weight not in _FACES:
        _FACES[weight] = _Face(weight)
    return _FACES[weight]


def width(text: str, size: float, weight: int = 400) -> float:
    f = face(weight)
    return f.advance(text) * size / f.upm


def wrap(text: str, size: float, maxw: float, weight: int = 400) -> list[str]:
    """공백 단위로 줄을 나눈다. 줄바꿈 없는 공백(U+00A0)은 나누지 않는다."""
    out: list[str] = []
    for para in text.split("\n"):
        line = ""
        for word in para.split(" "):
            cand = f"{line} {word}" if line else word
            if line and width(cand, size, weight) > maxw:
                out.append(line)
                line = word
            else:
                line = cand
        out.append(line)
    return out


# =========================================================================
class Canvas:
    """PowerPoint 기본 개체로 옮길 장면."""

    def __init__(self, bg: str = "#FFFFFF"):
        self.bg = bg
        self.items: list[dict] = []
        self.texts: list[str] = []

    # ---- 도형 --------------------------------------------------------------
    def rect(self, x, y, w, h, fill="none", stroke="none", sw=1, r=0, opacity=1.0, dash=None, name=None):
        self.items.append(dict(kind="rect", x=x, y=y, w=w, h=h, fill=fill, stroke=stroke, sw=sw, r=r,
                               opacity=opacity, dash=dash, name=name))

    def circle(self, cx, cy, r, fill="none", stroke="none", sw=1, opacity=1.0, dash=None):
        self.items.append(dict(kind="oval", x=cx - r, y=cy - r, w=2 * r, h=2 * r, fill=fill, stroke=stroke,
                               sw=sw, opacity=opacity, dash=dash))

    def line(self, x1, y1, x2, y2, stroke="#000", sw=1, dash=None, cap="round"):
        self.items.append(dict(kind="line", x1=x1, y1=y1, x2=x2, y2=y2, stroke=stroke, sw=sw, dash=dash, arrow=False))

    def arrow(self, x1, y1, x2, y2, stroke="#000", sw=2, head=10):
        self.items.append(dict(kind="line", x1=x1, y1=y1, x2=x2, y2=y2, stroke=stroke, sw=sw, dash=None, arrow=True))

    def art(self, x, y, w, h, name="그림") -> "Art":
        a = Art(w, h)
        self.items.append(dict(kind="art", x=x, y=y, w=w, h=h, art=a, name=name))
        return a

    def svgfile(self, path, x, y, w, h, png=None, name="그림"):
        self.items.append(dict(kind="svgfile", path=Path(path), png=Path(png) if png else None, x=x, y=y, w=w, h=h, name=name))

    # ---- 글자 --------------------------------------------------------------
    def _text_item(self, x, y, rows, size, anchor, lh, wrapw=None):
        """rows: [[(문자열, weight, fill), ...], ...]. y 는 첫 줄 기준선."""
        for row in rows:
            self.texts.append("".join(s for s, _, _ in row))
        widths = [sum(width(s, size, w) for s, w, _ in row) for row in rows]
        self.items.append(dict(kind="text", x=x, y=y, rows=rows, size=size, anchor=anchor, lh=lh,
                               w=wrapw or (max(widths) if widths else 0), wrap=wrapw is not None))
        return max(widths) if widths else 0

    def text(self, x, y, s, size, weight=400, fill="#000", anchor="start", track=0.0, opacity=1.0):
        if not s:
            return 0.0
        return self._text_item(x, y, [[(s, weight, fill)]], size, anchor, 1.2)

    def lines(self, x, y, rows, size, weight=400, fill="#000", lh=1.45, anchor="start"):
        self._text_item(x, y, [[(r, weight, fill)] for r in rows], size, anchor, lh)
        return y + (len(rows) - 1) * size * lh

    def para(self, x, y, s, size, maxw, weight=400, fill="#000", lh=1.5, anchor="start"):
        rows = wrap(s, size, maxw, weight)
        # PowerPoint 는 한글을 글자 단위로 끊으므로, 계산한 위치에 줄바꿈(<a:br/>)을 넣은 한 문단으로 둔다.
        self.texts.append(s)
        nb = " "
        self.items.append(dict(kind="text", x=x, y=y, rows=[[(s.replace(nb, " "), weight, fill)]], size=size,
                               anchor=anchor, lh=lh, w=maxw * 1.06 + 10, wrap=True, nlines=len(rows),
                               brk=[r.replace(nb, " ") for r in rows]))
        return len(rows)

    def runs(self, x, y, parts, size, anchor="start"):
        return self._text_item(x, y, [list(parts)], size, anchor, 1.2)


# =========================================================================
class Art:
    """SVG 로 남기는 그림. 좌표는 그림 안의 지역 좌표."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.parts: list[str] = []
        self.defs: list[str] = []

    def raw(self, svg: str):
        self.parts.append(svg)

    def rect(self, x, y, w, h, fill="none", stroke="none", sw=1, r=0, opacity=1.0, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        op = f' opacity="{opacity}"' if opacity != 1 else ""
        self.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" ry="{r}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}{op}/>')

    def circle(self, cx, cy, r, fill="none", stroke="none", sw=1, opacity=1.0, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        op = f' opacity="{opacity}"' if opacity != 1 else ""
        self.raw(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}{op}/>')

    def line(self, x1, y1, x2, y2, stroke="#000", sw=1, dash=None, cap="round"):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.raw(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" '
                 f'stroke-width="{sw}" stroke-linecap="{cap}"{d}/>')

    def path(self, d, fill="none", stroke="none", sw=1, opacity=1.0, join="round", dash=None):
        op = f' opacity="{opacity}"' if opacity != 1 else ""
        ds = f' stroke-dasharray="{dash}"' if dash else ""
        self.raw(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="{join}" '
                 f'stroke-linecap="round"{op}{ds}/>')

    def arrow(self, x1, y1, x2, y2, stroke="#000", sw=2, head=10, dash=None):
        self.line(x1, y1, x2, y2, stroke, sw, dash)
        a = math.atan2(y2 - y1, x2 - x1)
        p1 = (x2 - head * math.cos(a - 0.45), y2 - head * math.sin(a - 0.45))
        p2 = (x2 - head * math.cos(a + 0.45), y2 - head * math.sin(a + 0.45))
        self.path(f"M{p1[0]:.1f},{p1[1]:.1f} L{x2:.1f},{y2:.1f} L{p2[0]:.1f},{p2[1]:.1f} Z", fill=stroke, stroke=stroke, sw=1)

    def text(self, x, y, s, size, weight=400, fill="#000", anchor="start"):
        f = face(weight)
        w = width(s, size, weight)
        x0 = x - w if anchor == "end" else x - w / 2 if anchor == "middle" else x
        k = size / f.upm
        self.raw(f'<path transform="translate({x0:.2f},{y:.2f}) scale({k:.5f})" d="{f.outline(s)}" fill="{fill}"/>')
        return w

    def svg(self) -> str:
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w:.0f}" height="{self.h:.0f}" '
                f'viewBox="0 0 {self.w:.1f} {self.h:.1f}">{defs}\n' + "\n".join(self.parts) + "\n</svg>\n")
