#!/usr/bin/env python3
"""Generate the layan dark, light and darker cursor themes from the installed Breeze Dark cursors.

Stage 1 recolors Breeze's scalable SVG sources (primary color -> layan accent,
outline stays white) and swaps the arrow for a rounded, diagonally symmetric
one. Stage 2 renders every frame with rsvg-convert and packs Xcursor files.

Needs: python3 with fontTools, lxml, numpy and Pillow, rsvg-convert, and the breeze-cursors
package. The generated theme is checked in, so users never need to run this.

Usage: generate.py [--breeze /usr/share/icons/breeze_cursors]
"""
import argparse
import copy
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
from io import BytesIO

import numpy as np
from fontTools.pens.recordingPen import RecordingPen
from fontTools.svgLib.path import parse_path
from lxml import etree
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DARK_DIR = os.path.join(HERE, "layan-dark-cursors")
LIGHT_DIR = os.path.join(HERE, "layan-light-cursors")
DARKER_DIR = os.path.join(HERE, "layan-darker-cursors")

PRIMARY = "#5657f5"
PRIMARY_TINT = "#a9aaf9"
PRIMARY_TINT2 = "#cccdfc"  # the same mix toward white, 70% instead of 49%
OUTLINE = "#fff"

# Breeze fill -> layan fill. Anything not listed (white, semantic status
# colors, gradients) is kept as is.
FILL_MAP = {
    "#333": PRIMARY,
    "#0d0d0d": PRIMARY,
    "#3daee9": PRIMARY,
    "#46a7ac": PRIMARY,
    "#d4497f": PRIMARY_TINT,
}

# Breeze cursor sizes: nominal size -> pixel size of the 32x32 canvas.
NOMINAL_SIZES = [12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72]
CANVAS = 32
BASE_NOMINAL = 24

SVG_NS = "http://www.w3.org/2000/svg"

# Arrow geometry. The tip angle is 45 degrees like Breeze's, the left edge is
# vertical, and the shape is mirror symmetric about its own axis, which runs
# from the tip at 22.5 degrees off vertical. u runs along that axis and v
# across it. The wings are 16 long, as in Breeze.
PHI = (1 + math.sqrt(5)) / 2
HALF_ANGLE = math.pi / 8
WING = 16.0                                    # length of the left and right edges
WING_U = WING * math.cos(HALF_ANGLE)           # reach of the wing ends along the axis
TAIL_BASE = WING / PHI ** 2                    # golden tail length
TAIL_EXTRA = 1.28                              # makes the outlined arrow as tall as Breeze's (20.1 px)
TAIL_LEN = TAIL_BASE + TAIL_EXTRA              # how far the tail runs past the notch
TAIL_HALF = TAIL_BASE / PHI ** 2 / 2           # half width of the tail
JUNCTION_U = WING_U - WING_U / PHI ** 5        # where the wings meet the tail
TAIL_U = JUNCTION_U + TAIL_LEN                 # tip to end of tail, along the axis
R_TIP = TAIL_BASE / PHI ** 4
R_WING = TAIL_BASE / PHI ** 4
R_JUNCTION = TAIL_BASE / PHI ** 4            # where the tail meets the wings
# Rounding pulls the visible tip back along the axis; start higher so it lands
# on the hotspot row.
TIP = (4.0, 4.0 - R_TIP * (1 / math.sin(HALF_ANGLE) - 1))
SHADOW_SHIFT = 0.8  # along the axis, so the shadow keeps the symmetry
OUTLINE_STROKE = 2.0

# Sharp convex corners of the other cursors are rounded to this radius. Outline
# and shadow layers get 1 more, so the outline keeps an even thickness.
R_CORNER = TAIL_BASE / PHI ** 4  # every cursor: the arrow's radius
CORNER_MIN_TURN = math.radians(25)

# The badge next to the arrow (help, copy, progress, ...) is scaled down and
# moved from Breeze's slot so it keeps Breeze's 1 px gap to the arrow outline.
BADGE_SCALE = PHI ** -0.5
BADGE_SLOT = (20.5, 22.5)    # badge center in Breeze
BADGE_CENTER = (19.6, 22.5)  # badge center here

# Breeze's own arrow, as it appears in the sources (start point of each path).
OLD_ARROW_STARTS = {
    "shadow": (3.93, 3.75),
    "outline": (3.93, 2.75),
    "body": (4.0, 3.873),
}


def rounded_polygon(points, radii):
    """SVG path data for a closed polygon with per-vertex corner radii.

    Two corners on one edge may ask for more than the edge has. Both are then
    scaled back by the same factor, so the curves meet instead of overlapping.
    """
    n = len(points)
    geo = []
    for i in range(n):
        p, a, b = points[i], points[i - 1], points[(i + 1) % n]
        va = (a[0] - p[0], a[1] - p[1])
        vb = (b[0] - p[0], b[1] - p[1])
        la, lb = math.hypot(*va), math.hypot(*vb)
        va = (va[0] / la, va[1] / la)
        vb = (vb[0] / lb, vb[1] / lb)
        theta = math.acos(max(-1.0, min(1.0, va[0] * vb[0] + va[1] * vb[1])))
        cross = (p[0] - a[0]) * (b[1] - p[1]) - (p[1] - a[1]) * (b[0] - p[0])
        geo.append((va, vb, theta, 1 if cross > 0 else 0))
    want = [radii[i] / math.tan(geo[i][2] / 2) for i in range(n)]  # distance each corner eats
    scale = [1.0] * n
    for _ in range(8):  # settle: scaling one corner back can free room for its neighbour
        for i in range(n):
            j = (i + 1) % n
            length = math.dist(points[i], points[j])
            used = want[i] * scale[i] + want[j] * scale[j]
            if used > length * (1 + 1e-9):
                f = length / used
                scale[i] *= f
                scale[j] *= f
    corners = []
    for i in range(n):
        va, vb, theta, sweep = geo[i]
        d = want[i] * scale[i]
        r = d * math.tan(theta / 2)
        p = points[i]
        corners.append(((p[0] + va[0] * d, p[1] + va[1] * d), (p[0] + vb[0] * d, p[1] + vb[1] * d), r, sweep))

    def f(v):
        return ("%.3f" % v).rstrip("0").rstrip(".")

    out = ["M%s %s" % (f(corners[0][1][0]), f(corners[0][1][1]))]
    for i in list(range(1, n)) + [0]:
        t1, t2, r, sweep = corners[i]
        out.append("L%s %s" % (f(t1[0]), f(t1[1])))
        out.append("A%s %s 0 0 %d %s %s" % (f(r), f(r), sweep, f(t2[0]), f(t2[1])))
    out.append("Z")
    return "".join(out)


def arrow_path(dx, dy, shift=0.0):
    """Rounded arrow path, tip at TIP + (dx, dy), moved along the axis by shift."""
    sin_a, cos_a = math.sin(HALF_ANGLE), math.cos(HALF_ANGLE)

    def uv(u, v):
        return u * sin_a + v * cos_a, u * cos_a - v * sin_a

    pts_rel = [
        (0.0, 0.0),
        (0.0, WING),
        uv(JUNCTION_U, -TAIL_HALF),
        uv(TAIL_U, -TAIL_HALF),
        uv(TAIL_U, TAIL_HALF),
        uv(JUNCTION_U, TAIL_HALF),
        uv(WING_U, WING * sin_a),
    ]
    ox = TIP[0] + dx + shift * sin_a
    oy = TIP[1] + dy + shift * cos_a
    pts = [(ox + x, oy + y) for x, y in pts_rel]
    radii = [R_TIP, R_WING, R_JUNCTION, TAIL_HALF, TAIL_HALF, R_JUNCTION, R_WING]
    return rounded_polygon(pts, radii)


# The small arrow in the side and corner resize cursors (top_side, top_left_corner,
# ...) is the cursor arrow at a smaller scale: the same 45 degree tip, golden
# head to tail and tail width, and the same corner radius. Scaled so it is as long
# as Breeze's glyph is once rounded (8.465 px, tip to end of tail), and pointing
# up with its tail end where Breeze's is, 1012.156, and centered on x = 40.5.
GLYPH_LEN = 8.465
GLYPH_X = 40.5
GLYPH_BOTTOM = 1012.156
GLYPH_SCALE = (GLYPH_LEN + R_TIP * (1 / math.sin(HALF_ANGLE) - 1)) / TAIL_U
GLYPH_CURSORS = tuple(n + ".svg" for n in (
    "top_side", "bottom_side", "left_side", "right_side",
    "top_left_corner", "top_right_corner", "bottom_left_corner", "bottom_right_corner"))


def glyph_path(dx=0.0, dy=0.0):
    """The scaled arrow, pointing up, as path data; moved by (dx, dy)."""
    k = GLYPH_SCALE
    half = TAIL_HALF * k
    top = GLYPH_BOTTOM - TAIL_U * k
    sin_a = math.sin(HALF_ANGLE)
    wing_v = WING * sin_a * k

    def pt(u, v):
        return GLYPH_X + dx + v, top + dy + u * k

    # down the right side and back up the left, the order arrow_path uses
    pts = [pt(0, 0), pt(WING_U, wing_v), pt(JUNCTION_U, half), pt(TAIL_U, half),
           pt(TAIL_U, -half), pt(JUNCTION_U, -half), pt(WING_U, -wing_v)]
    radii = [R_TIP, R_WING, R_JUNCTION, half, half, R_JUNCTION, R_WING]
    return rounded_polygon(pts, radii)


def replace_glyph(root):
    """Swap Breeze's glyph for ours, in its shadow, outline and body layers."""
    for el in root.iter("{%s}path" % SVG_NS):
        d = el.get("d") or ""
        if "l-3.027 6.054" in d:
            if el.get("filter") is not None:
                # the shadow is the outline shape moved by some offset, which
                # differs on the rotated corner cursors; read it off its start
                m = re.match(r"m([\d.]+) ([\d.]+)c", d)
                el.set("d", glyph_path(float(m.group(1)) - 40.5, float(m.group(2)) - 1001.406))
                el.set("stroke", "#000")
            else:
                el.set("d", glyph_path())
                el.set("stroke", OUTLINE)
            el.set("stroke-width", "%g" % OUTLINE_STROKE)
            el.set("stroke-linejoin", "round")
        elif "-3 5.75h2.25v3" in d:
            el.set("d", glyph_path())


def path_start(d):
    m = re.match(r"\s*m\s*(-?[\d.]+)[ ,]\s*(-?[\d.]+)", d)
    return (float(m.group(1)), float(m.group(2))) if m else None


def classify_arrow(el):
    """Return (kind, dx, dy) when a path is one of Breeze's arrow paths."""
    d = el.get("d", "")
    if "a.92.92 0 0 0 -.552-.1" in d:
        if el.get("filter") is not None:
            kind = "shadow"
        elif "m.07 1.122" in d:
            kind = "ring"  # outline with the body cut out (context-menu)
        else:
            kind = "outline"
    elif "15.977" in d and "3.352-1.766" in d:
        kind = "body"
    else:
        return None
    start = path_start(d)
    if start is None:
        return None
    x0, y0 = OLD_ARROW_STARTS["outline" if kind == "ring" else kind]
    return kind, start[0] - x0, start[1] - y0


def replace_arrow(el, kind, dx, dy):
    for attr in ("d", "fill", "stroke", "stroke-width", "stroke-linejoin"):
        if attr in el.attrib:
            del el.attrib[attr]
    if kind == "shadow":
        el.set("d", arrow_path(dx, dy, SHADOW_SHIFT))
        el.set("stroke", "#000")
    elif kind == "outline":
        el.set("d", arrow_path(dx, dy))
        el.set("fill", OUTLINE)
        el.set("stroke", OUTLINE)
    else:  # body, or the ring: its hole shows Breeze's body, so draw the body
        el.set("d", arrow_path(dx, dy))
        el.set("fill", PRIMARY)
    if kind in ("shadow", "outline"):
        el.set("stroke-width", "%g" % OUTLINE_STROKE)
        el.set("stroke-linejoin", "round")


def inherited_fill(el):
    node = el
    while node is not None:
        fill = node.get("fill")
        if fill is not None:
            return fill
        node = node.getparent()
    return None


def recolor(root, skip):
    for el in root.iter():
        if not isinstance(el.tag, str) or el in skip:
            continue
        tag = etree.QName(el).localname
        if tag == "stop" and el.get("stop-color") is None:
            el.set("stop-color", PRIMARY)
            continue
        if tag == "g" and el.get("fill") in FILL_MAP:
            el.set("fill", FILL_MAP[el.get("fill")])
            continue
        if tag not in ("path", "circle", "rect", "ellipse", "polygon"):
            continue
        if el.get("id") == "hotspot" or el.get("display") == "none":
            continue
        if el.get("filter") is not None:
            continue
        fill = el.get("fill")
        if fill is None:
            fill = inherited_fill(el)
            if fill is None:  # SVG default is black: Breeze's dark body
                el.set("fill", PRIMARY)
                continue
        if fill in FILL_MAP:
            el.set("fill", FILL_MAP[fill])


def add_menu_badge(root):
    """Breeze draws the menu lines inside the arrow, which our arrow can't
    hold, so move them into a round badge like the help and copy cursors."""
    lines = next(el for el in root.iter("{%s}path" % SVG_NS) if el.get("id") == "path5285")
    cx, cy = 20.5, 22.5
    badge = [
        ("circle", {"cx": str(cx), "cy": str(cy + 1), "r": "6.5", "filter": "url(#filter7078)", "opacity": ".2"}),
        ("circle", {"cx": str(cx), "cy": str(cy), "r": "6.5", "fill": OUTLINE}),
        ("circle", {"cx": str(cx), "cy": str(cy), "r": "5.5", "fill": PRIMARY}),
    ]
    for tag, attrs in badge:
        el = etree.Element("{%s}%s" % (SVG_NS, tag))
        for k, v in attrs.items():
            el.set(k, v)
        lines.addprevious(el)
    lines.set("fill", OUTLINE)
    lines.set("transform", "translate(%g %g) scale(.8) translate(-10.3 -12.5)" % (cx, cy))


def badge_elements(root, arrow_els):
    """Top-level elements that are neither the arrow nor shared definitions."""
    skip = {"filter", "linearGradient", "defs", "style", "title", "desc"}
    badge = []
    for el in root:
        if not isinstance(el.tag, str) or etree.QName(el).localname in skip:
            continue
        if el.get("id") == "hotspot" or any(e in arrow_els for e in el.iter()):
            continue
        badge.append(el)
    return badge


def shrink(badge, to, frm):
    """Wrap elements in a group scaled about `frm` and moved so `frm` lands on `to`."""
    if not badge:
        return
    group = etree.Element("{%s}g" % SVG_NS)
    group.set("id", "badge")
    group.set("transform", "translate(%g %g) scale(%.4f) translate(%g %g)" % (to[0], to[1], BADGE_SCALE, -frm[0], -frm[1]))
    badge[0].addprevious(group)
    for el in badge:
        group.append(el)


def _lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def _split(seg, t):
    """Split a ('L', p0, p1) or ('C', p0, c1, c2, p1) segment at t."""
    if seg[0] == "L":
        m = _lerp(seg[1], seg[2], t)
        return ("L", seg[1], m), ("L", m, seg[2])
    _, p0, c1, c2, p1 = seg
    a, b, c = _lerp(p0, c1, t), _lerp(c1, c2, t), _lerp(c2, p1, t)
    d, e = _lerp(a, b, t), _lerp(b, c, t)
    m = _lerp(d, e, t)
    return ("C", p0, a, d, m), ("C", m, e, c, p1)


def _point(seg, t):
    return _split(seg, t)[0][-1]


def _length(seg):
    pts = [_point(seg, i / 32) for i in range(33)]
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(32))


def _t_at(seg, dist, from_end):
    """Parameter at which the segment is `dist` away (along it) from an end."""
    n = 64
    pts = [_point(seg, i / n) for i in range(n + 1)]
    if from_end:
        pts.reverse()
    run = 0.0
    for i in range(n):
        step = math.dist(pts[i], pts[i + 1])
        if run + step >= dist:
            u = (i + (dist - run) / step) / n if step else i / n
            return 1 - u if from_end else u
        run += step
    return 0.0 if from_end else 1.0


def _tangent(seg, at_end):
    if seg[0] == "L":
        v = (seg[2][0] - seg[1][0], seg[2][1] - seg[1][1])
    elif at_end:
        pts = [seg[4], seg[3], seg[2], seg[1]]
        v = next(((seg[4][0] - p[0], seg[4][1] - p[1]) for p in pts[1:] if math.dist(p, seg[4]) > 1e-9), (1, 0))
    else:
        v = next(((p[0] - seg[1][0], p[1] - seg[1][1]) for p in seg[2:] if math.dist(p, seg[1]) > 1e-9), (1, 0))
    n = math.hypot(*v) or 1.0
    return v[0] / n, v[1] / n


def _subpaths(d):
    pen = RecordingPen()
    parse_path(d, pen)
    subs = []
    cur = None
    pos = None
    for op, args in pen.value:
        if op == "moveTo":
            cur, pos = [], args[0]
            start = pos
        elif op == "lineTo":
            cur.append(("L", pos, args[0]))
            pos = args[0]
        elif op == "curveTo":
            cur.append(("C", pos, args[0], args[1], args[2]))
            pos = args[2]
        elif op == "qCurveTo":
            q, e = args[0], args[-1]
            c1 = (pos[0] + 2 / 3 * (q[0] - pos[0]), pos[1] + 2 / 3 * (q[1] - pos[1]))
            c2 = (e[0] + 2 / 3 * (q[0] - e[0]), e[1] + 2 / 3 * (q[1] - e[1]))
            cur.append(("C", pos, c1, c2, e))
            pos = e
        elif op in ("closePath", "endPath"):
            closed = op == "closePath"
            if closed and math.dist(pos, start) > 1e-6:
                cur.append(("L", pos, start))
            cur = [sg for sg in cur if math.dist(sg[1], sg[-1]) > 1e-6 or sg[0] == "C"]
            if cur:
                subs.append((cur, closed))
            cur = None
    return subs


def round_path(d, radius, close_open=False):
    """Round the sharp convex corners of a path with arcs of the given radius.

    close_open treats a subpath with no 'z' as closed, as a fill would."""
    def f(v):
        return ("%.3f" % v).rstrip("0").rstrip(".")

    def pt(p):
        return "%s %s" % (f(p[0]), f(p[1]))

    out = []
    changed = False
    for segs, closed in _subpaths(d):
        if not closed and close_open:
            closed = True
            if math.dist(segs[0][1], segs[-1][-1]) > 1e-6:
                segs = segs + [("L", segs[-1][-1], segs[0][1])]
        n = len(segs)
        if not closed or n < 2:
            out.append("M" + pt(segs[0][1]) + "".join(
                ("L" + pt(sg[2])) if sg[0] == "L" else "C%s %s %s" % (pt(sg[2]), pt(sg[3]), pt(sg[4]))
                for sg in segs))
            continue
        poly = [_point(sg, i / 8) for sg in segs for i in range(8)]
        area = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                   for i in range(len(poly)))
        lens = [_length(sg) for sg in segs]
        corners = [None] * n  # corner after segment i: (distance, effective radius, sweep)
        for i in range(n):
            j = (i + 1) % n
            t1, t2 = _tangent(segs[i], True), _tangent(segs[j], False)
            cross = t1[0] * t2[1] - t1[1] * t2[0]
            turn = math.atan2(abs(cross), t1[0] * t2[0] + t1[1] * t2[1])
            if turn < CORNER_MIN_TURN or cross * area <= 0:
                continue
            dist = radius * math.tan(turn / 2)
            dist = min(dist, 0.45 * lens[i], 0.45 * lens[j])
            changed = True
            corners[i] = (dist, dist / math.tan(turn / 2), 1 if cross > 0 else 0)
        trimmed = []
        for i, sg in enumerate(segs):
            before = corners[i - 1]
            after = corners[i]
            if before:
                sg = _split(sg, _t_at(sg, before[0], False))[1]
            if after:
                rem = _length(sg)
                sg = _split(sg, _t_at(sg, after[0], True))[0] if rem > after[0] else sg
            trimmed.append(sg)
        parts = ["M" + pt(trimmed[0][1])]
        for i, sg in enumerate(trimmed):
            parts.append("L" + pt(sg[2]) if sg[0] == "L" else "C%s %s %s" % (pt(sg[2]), pt(sg[3]), pt(sg[4])))
            if corners[i]:
                nxt = trimmed[(i + 1) % n]
                parts.append("A%s %s 0 0 %d %s" % (f(corners[i][1]), f(corners[i][1]), corners[i][2], pt(nxt[1])))
        parts.append("Z")
        out.append("".join(parts))
    return "".join(out), changed


# Breeze leaves the pointing hand's body path without a 'z', so it is only
# rounded (thumb, bottom right) when told to close it. Other cursors lean on
# their white layer being a solid fill, so they stay as they were.
CLOSE_OPEN_PATHS = ("pointer",)

# Cursors whose white layer is part of the design, not just an outline.
KEEP_BREEZE_SHAPES = ("wait", "crosshair", "wayland-cursor", "x-cursor", "zoom-")


SHAPE_TAGS = ("path", "circle", "rect", "ellipse", "polygon")


def _is_shape(el):
    if not isinstance(el.tag, str) or etree.QName(el).localname not in SHAPE_TAGS:
        return False
    if el.get("id") == "hotspot" or el.get("display") == "none":
        return False
    return etree.QName(el).localname != "path" or bool(el.get("d"))


def _is_outline(el):
    return _is_shape(el) and el.get("filter") is None and el.get("fill") == OUTLINE


def _is_body(el):
    fill = el.get("fill")
    return _is_shape(el) and el.get("filter") is None and fill is not None \
        and fill != OUTLINE and not fill.startswith("url(")


def _edge_of(body):
    """White 1 px edge for a body: the body itself, stroked."""
    edge = copy.deepcopy(body)
    if "id" in edge.attrib:
        del edge.attrib["id"]
    edge.set("fill", OUTLINE)
    edge.set("stroke", OUTLINE)
    edge.set("stroke-width", "%g" % OUTLINE_STROKE)
    edge.set("stroke-linejoin", "round")
    return edge


def round_corners(root, close_open=False, radius=R_CORNER):
    """Round the sharp corners of the bodies, then rebuild each outline from its
    rounded bodies as a 1 px stroke so the border has an even thickness."""
    for parent in root.iter():
        kids = [k for k in parent if _is_shape(k)]
        i = 0
        while i < len(kids):
            outline = kids[i]
            if not _is_outline(outline):
                i += 1
                continue
            j = i + 1
            bodies = []
            while j < len(kids) and _is_body(kids[j]):
                bodies.append(kids[j])
                j += 1
            i = j
            changed = False
            for body in bodies:
                if etree.QName(body).localname != "path":
                    continue
                d, did = round_path(body.get("d"), radius, close_open)
                if did:
                    body.set("d", d)
                    changed = True
            if not changed:
                continue
            for body in bodies:
                outline.addprevious(_edge_of(body))
            # bodies in a trailing group (a center dot, say) get their edge inside it
            for sib in list(outline.itersiblings()):
                if not isinstance(sib.tag, str):
                    continue
                if sib.get("filter") is not None or _is_outline(sib):
                    break  # next cursor part
                if etree.QName(sib).localname == "g":
                    for shape in [e for e in sib.iter() if _is_body(e)]:
                        shape.addprevious(_edge_of(shape))
            outline.getparent().remove(outline)
    for el in root.iter("{%s}path" % SVG_NS):
        # shadows follow the outline, so they get the same extra radius
        if el.get("filter") is not None and _is_shape(el):
            d, did = round_path(el.get("d"), radius + 1, close_open)
            if did:
                el.set("d", d)


ARROW_SVG = """<svg id="svg11024" height="32" width="32" xmlns="http://www.w3.org/2000/svg">
  <filter id="filter7078" color-interpolation-filters="sRGB">
    <feGaussianBlur id="feGaussianBlur7080" stdDeviation=".657"/>
  </filter>
  <g transform="%(transform)s">
    <path id="shadow" d="%(shadow)s" filter="url(#filter7078)" opacity=".2" stroke="#000" stroke-width="%(stroke)g" stroke-linejoin="round"/>
    <path id="outline" d="%(body)s" fill="%(outline)s" stroke="%(outline)s" stroke-width="%(stroke)g" stroke-linejoin="round"/>
    <path id="body" d="%(body)s" fill="%(primary)s"/>
  </g>
</svg>
"""

# Breeze builds center_ptr by turning its arrow 22.5 degrees, and right_ptr by
# mirroring it across x=16. Do the same with our arrow.
_c, _s = math.cos(HALF_ANGLE), math.sin(HALF_ANGLE)
UPRIGHT = "matrix(%.8f %.8f %.8f %.8f %.3f %.3f)" % (
    _c, _s, -_s, _c, 16.5 - (_c * TIP[0] - _s * TIP[1]), TIP[1] - (_s * TIP[0] + _c * TIP[1]))
MIRRORED = "matrix(-1 0 0 1 32 0)"
DERIVED_ARROWS = {"center_ptr": UPRIGHT, "right_ptr": MIRRORED}


def derived_arrow_svg(transform):
    return ARROW_SVG % dict(
        transform=transform, shadow=arrow_path(0, 0, SHADOW_SHIFT), body=arrow_path(0, 0),
        stroke=OUTLINE_STROKE, outline=OUTLINE, primary=PRIMARY)


# The busy spinner (the wait cursor and the badge on the progress cursor): three
# round-ended arcs, the lead in the accent, then a green and a teal. Each arc
# and its gap split the 120 degree share as phi squared to 1. The
# frames turn by an even 360 / 23 degrees, so the loop has no jump.
SPIN_FRAMES = 23
SPIN_STEP = 360 / SPIN_FRAMES
SPIN_ARC = 120 * PHI ** 2 / (1 + PHI ** 2)
SPIN_START = -90.0  # lead arc's centre in frame 1: straight up
# On the white fill of the dark and light themes. The green and teal are darker
# than on the dark fill so they keep their contrast. The teal sits at hue 194,
# roughly between the accent (240) and the green (160) but pulled toward the
# green, which keeps it from reading as blue while staying apart from the green.
SPIN_GREEN = "#0e9f6e"
SPIN_TEAL = "#0d7ea0"
SPIN_FILLS = (PRIMARY, SPIN_GREEN, SPIN_TEAL)
# One geometry for every theme. Breeze's arcs run 7.6 to 10 px on the 11 px wait
# disc and 3.2 to 5 px on the 6.5 px badge; they are scaled in about their centre
# so they clear the 1 px ring, leaving the wait spinner a golden-ratio gap.
RING = 1.0  # ring thickness, same as the outline
WAIT_GAP = RING * PHI
SPIN_WAIT_SCALE = (10.0 - WAIT_GAP) / 10.0
SPIN_BADGE_SCALE = 0.9
WAIT_R_OUT = 10.0 * SPIN_WAIT_SCALE
WAIT_R_IN = 7.6 * SPIN_WAIT_SCALE
BADGE_SPIN_R_OUT = 5.0 * SPIN_BADGE_SCALE
BADGE_SPIN_R_IN = 3.2 * SPIN_BADGE_SCALE
# Breeze's frame 1 places the wait spinner with a plain translate; later frames
# add a rotation to it, which we do ourselves.
WAIT_GROUP_TRANSFORM = "translate(-459.975 293.962)"


def arc_band(cx, cy, r_in, r_out, centre_deg, sweep_deg):
    """A band along a circle with a round end at each side, as path data."""
    rc = (r_out - r_in) / 2
    mid = (r_out + r_in) / 2
    half = sweep_deg / 2 - math.degrees(rc / mid)  # the caps add the rest of the sweep
    a0, a1 = math.radians(centre_deg - half), math.radians(centre_deg + half)

    def pt(r, a):
        return "%.3f %.3f" % (cx + r * math.cos(a), cy + r * math.sin(a))

    return ("M%s A%g %g 0 0 1 %s A%g %g 0 0 1 %s A%g %g 0 0 0 %s A%g %g 0 0 1 %sZ"
            % (pt(r_out, a0), r_out, r_out, pt(r_out, a1), rc, rc, pt(r_in, a1),
               r_in, r_in, pt(r_in, a0), rc, rc, pt(r_out, a0)))


def recolor_spinner(container, colors):
    """Recolor the spinner arcs in container by the colors map; returns the arcs."""
    arcs = [e for e in container.iter("{%s}path" % SVG_NS)
            if e.get("fill") in SPIN_FILLS and e.get("filter") is None]
    for arc in arcs:
        arc.set("fill", colors[arc.get("fill")])
    return set(arcs)


def spinner_arcs(parent, before, cx, cy, r_in, r_out, frame):
    """Add the three arcs of one frame to parent, ahead of `before`."""
    lead = SPIN_START + frame * SPIN_STEP
    for i, fill in enumerate(SPIN_FILLS):
        arc = etree.Element("{%s}path" % SVG_NS)
        arc.set("d", arc_band(cx, cy, r_in, r_out, lead - i * 120, SPIN_ARC))
        arc.set("fill", fill)
        before.addprevious(arc)


def _frame_of(src):
    return int(re.search(r"(\d+)\.svg$", src).group(1)) - 1


def _spinner_arc_elements(root, skip=()):
    """The two chevron-cut arcs. The arrow's body has the accent fill too, so it is skipped."""
    return [e for e in root.iter("{%s}path" % SVG_NS)
            if e.get("fill") in (PRIMARY, PRIMARY_TINT) and e.get("filter") is None
            and e.get("id") != "hotspot" and e not in skip]


def redraw_wait_arcs(root, frame):
    """The wait cursor: a white disc with the three-arc spinner on it."""
    circle = next(e for e in root.iter("{%s}circle" % SVG_NS) if e.get("fill") == OUTLINE)
    cx, cy = float(circle.get("cx")), float(circle.get("cy"))
    arcs = _spinner_arc_elements(root)
    assert len(arcs) == 2, "expected the two spinner arcs, found %d" % len(arcs)
    arcs[0].getparent().set("transform", WAIT_GROUP_TRANSFORM)
    spinner_arcs(arcs[0].getparent(), arcs[0], cx, cy, WAIT_R_IN, WAIT_R_OUT, frame)
    for el in arcs:
        el.getparent().remove(el)


def _canvas_centre(circle):
    """Where a circle's centre lands once its own matrix transform is applied."""
    cx, cy = float(circle.get("cx")), float(circle.get("cy"))
    m = re.match(r"matrix\(([^)]*)\)", circle.get("transform") or "")
    if not m:
        return cx, cy
    a, b, c, d, e, f = [float(x) for x in m.group(1).replace(",", " ").split()]
    return a * cx + c * cy + e, b * cx + d * cy + f


def redraw_progress_arcs(root, frame, skip):
    """The progress cursor's badge: same spinner, drawn in canvas coordinates."""
    circle = next(e for e in root.iter("{%s}circle" % SVG_NS) if e.get("fill") == OUTLINE)
    cx, cy = _canvas_centre(circle)
    arcs = _spinner_arc_elements(root, skip)
    assert len(arcs) == 2, "expected the two spinner arcs, found %d" % len(arcs)
    spinner_arcs(arcs[0].getparent(), arcs[0], cx, cy, BADGE_SPIN_R_IN, BADGE_SPIN_R_OUT, frame)
    for el in arcs:
        el.getparent().remove(el)


def process_svg(src, dst):
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(src, parser)
    root = tree.getroot()
    arrows = []
    for el in root.iter("{%s}path" % SVG_NS):
        hit = classify_arrow(el)
        if hit:
            arrows.append((el, hit))
    for i, (el, (kind, dx, dy)) in enumerate(arrows):
        replace_arrow(el, kind, dx, dy)
        if kind == "ring":
            # draw the body right above the outline, below any icon details
            arrows[i - 1][0].addnext(el)
    recolor(root, {el for el, _ in arrows})
    if os.path.basename(src).startswith("progress-"):
        redraw_progress_arcs(root, _frame_of(src), {el for el, _ in arrows})
    if os.path.basename(src) == "context-menu.svg":
        add_menu_badge(root)
    if arrows:
        shrink(badge_elements(root, {el for el, _ in arrows}), BADGE_CENTER, BADGE_SLOT)
    elif os.path.basename(src) == "dnd-no-drop.svg":  # hand with a badge, no arrow
        shrink([el for el in root if el.get("id") == "g40166"], (30.0, 29.0), (30.0, 29.0))
    if os.path.basename(src) in GLYPH_CURSORS:
        replace_glyph(root)
    if not arrows and not os.path.basename(src).startswith(KEEP_BREEZE_SHAPES):
        round_corners(root, os.path.basename(src).startswith(CLOSE_OPEN_PATHS))
    if os.path.basename(src).startswith("wait-"):
        redraw_wait_arcs(root, _frame_of(src))
    tree.write(dst, xml_declaration=False, encoding="utf-8")


def stage_scalable(breeze, out):
    src_root = os.path.join(breeze, "cursors_scalable")
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    for name in sorted(os.listdir(src_root)):
        src = os.path.join(src_root, name)
        dst = os.path.join(out, name)
        if os.path.islink(src):
            os.symlink(os.readlink(src), dst)
            continue
        os.makedirs(dst)
        for f in sorted(os.listdir(src)):
            if name in DERIVED_ARROWS and f == name + ".svg":
                with open(os.path.join(dst, f), "w") as fh:
                    fh.write(derived_arrow_svg(DERIVED_ARROWS[name]))
            elif f.endswith(".svg"):
                process_svg(os.path.join(src, f), os.path.join(dst, f))
            else:
                shutil.copy(os.path.join(src, f), os.path.join(dst, f))


# ---- light variant ---------------------------------------------------------
# Built from the finished dark SVGs: the white and the accent swap places, and
# discs (the badges, the wait spinner, ...) become a white disc with an accent
# ring, their glyph taking the old disc color.

# Cursors that are a single disc rather than an arrow with a badge.
DISC_CURSORS = {"not-allowed": 11.0, "wait": 11.0, "wayland-cursor": 11.0}
# Parts that keep their color in the light variant: the zoom lens glass stays
# white and its plus/minus stays accent, so the lens reads white on accent.
KEEP_COLOR_IDS = {"zoom-in": ("g19654", "rect5428"), "zoom-out": ("g21649", "rect5432")}
BADGE_RADIUS = 6.5


def _fill(el):
    return (el.get("fill") or "").lower()


def lighten_disc(container, radius):
    """Turn a white ring circle plus colored disc and glyph into the light version."""
    shapes = [e for e in container.iter() if isinstance(e.tag, str) and etree.QName(e).localname in SHAPE_TAGS
              and e.get("filter") is None and e.get("id") != "hotspot"]
    ring = next((e for e in shapes if etree.QName(e).localname == "circle" and _fill(e) == OUTLINE), None)
    if ring is None:
        return
    inner = copy.deepcopy(ring)
    if "id" in inner.attrib:
        del inner.attrib["id"]
    inner.set("r", "%.6g" % (float(ring.get("r")) * (radius - RING) / radius))
    ring.set("fill", PRIMARY)
    ring.addnext(inner)
    after = shapes[shapes.index(ring) + 1:]
    glyphs = [e for e in container.iter() if isinstance(e.tag, str) and _fill(e) == OUTLINE and e is not inner]
    disc = next((e for e in after if _fill(e) not in ("", OUTLINE)), None)
    if glyphs and disc is not None:
        color = disc.get("fill")
        disc.getparent().remove(disc)
        for g in glyphs:
            g.set("fill", color)


def swap_colors(root, skip=()):
    swap = {OUTLINE: PRIMARY, PRIMARY: OUTLINE}
    for el in root.iter():
        if not isinstance(el.tag, str) or any(a in skip for a in el.iterancestors()) or el in skip:
            continue
        for attr in ("fill", "stroke", "stop-color"):
            v = el.get(attr)
            if v is not None and v.lower() in swap:
                el.set(attr, swap[v.lower()])


# The spinner on the light theme's white fill: the purple, green and teal of the other
# themes at depths that hold their contrast on white (3.9:1, 3.4:1 and 4.7:1).
LIGHT_SPIN = {PRIMARY: "#b74aff", SPIN_GREEN: SPIN_GREEN, SPIN_TEAL: SPIN_TEAL}


def make_light_svg(src, dst):
    tree = etree.parse(src)
    root = tree.getroot()
    name = os.path.basename(src)
    skip = set()
    disc = next((r for k, r in DISC_CURSORS.items() if name.startswith(k)), None)
    if disc:
        lighten_disc(root, disc)
        if name.startswith("wait-"):
            recolor_spinner(root, LIGHT_SPIN)
        skip.add(root)
        skip.update(root.iter())
    else:
        for badge in [e for e in root.iter() if e.get("id") == "badge"]:
            lighten_disc(badge, BADGE_RADIUS)
            if name.startswith("progress-"):
                recolor_spinner(badge, LIGHT_SPIN)
            skip.add(badge)
    for prefix, ids in KEEP_COLOR_IDS.items():
        if name.startswith(prefix):
            for el in root.iter():
                if isinstance(el.tag, str) and el.get("id") in ids:
                    skip.add(el)
    swap_colors(root, skip)
    tree.write(dst, xml_declaration=False, encoding="utf-8")


def stage_light(dark, out):
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    for name in sorted(os.listdir(dark)):
        src = os.path.join(dark, name)
        dst = os.path.join(out, name)
        if os.path.islink(src):
            os.symlink(os.readlink(src), dst)
            continue
        os.makedirs(dst)
        for f in sorted(os.listdir(src)):
            if f.endswith(".svg"):
                make_light_svg(os.path.join(src, f), os.path.join(dst, f))
            else:
                shutil.copy(os.path.join(src, f), os.path.join(dst, f))


# ---- darker variant --------------------------------------------------------
# The dark theme with the accent replaced by layan's dark window background
# (Window/View/Header in Layan.colors, also Konsole, Kvantum and Aurorae). The
# lighter tone (spinner, center dots) becomes the accent itself, not a grey.
DARKER_BG = "#31313a"
DARKER_MAP = {PRIMARY: DARKER_BG, PRIMARY_TINT: PRIMARY, PRIMARY_TINT2: PRIMARY_TINT}


# The same three hues on the dark fill, lightened to keep their contrast: a vivid
# purple (Layan's #b74aff lightened), mint and sky blue, 4.5:1 or better.
DARKER_SPIN = {PRIMARY: "#d66bff", SPIN_GREEN: "#5ef2b4", SPIN_TEAL: "#4fd0ff"}


def darken_disc(container, radius, fill=DARKER_BG):
    """Give a white disc a new fill, keeping the white as its outline. False if there is none."""
    ring = next((e for e in container.iter("{%s}circle" % SVG_NS) if e.get("fill") == OUTLINE), None)
    if ring is None:
        return False
    inner = copy.deepcopy(ring)
    if "id" in inner.attrib:
        del inner.attrib["id"]
    inner.set("r", "%.6g" % (float(ring.get("r")) * (radius - RING) / radius))
    inner.set("fill", fill)
    ring.addnext(inner)
    return True


def darken_spinner(container, radius, fill=DARKER_BG, colors=DARKER_SPIN):
    """Fill the spinner's disc and recolor its arcs for it; returns the arcs."""
    if not darken_disc(container, radius, fill):
        return set()
    return recolor_spinner(container, colors)


LOGO_ORANGE = "#f67400"


def fill_logo_disc(root, radius, fill):
    """The Wayland disc: the orange gives way to a plain fill inside the white ring, the
    white W staying."""
    if not darken_disc(root, radius, fill):
        return
    for el in root.iter("{%s}circle" % SVG_NS):
        if el.get("fill") == LOGO_ORANGE:
            el.getparent().remove(el)


def fill_x_logo(root, fill, arms):
    """The X cursor: a plain fill inside a 1 px white border (a stroke clipped to the
    silhouette, so the shape keeps its size), the arms in a second tone that stands
    apart from both the border and the fill, and the orange ring."""
    sil = next(e for e in root.iter("{%s}path" % SVG_NS) if e.get("fill") == OUTLINE and e.get("filter") is None)
    clip = etree.Element("{%s}clipPath" % SVG_NS)
    clip.set("id", "silhouette-clip")
    cut = etree.SubElement(clip, "{%s}path" % SVG_NS)
    cut.set("d", sil.get("d"))
    border = copy.deepcopy(sil)
    if "id" in border.attrib:
        del border.attrib["id"]
    border.set("fill", "none")
    border.set("stroke", OUTLINE)
    border.set("stroke-width", "%g" % OUTLINE_STROKE)
    border.set("clip-path", "url(#silhouette-clip)")
    for el in root.iter("{%s}path" % SVG_NS):
        if el.get("fill") == PRIMARY and el.get("filter") is None:
            el.set("fill", arms)
    sil.set("fill", fill)
    sil.addprevious(clip)
    sil.addnext(border)


# The center circle of the size_* cursors keeps the accent as its inner fill.
ACCENT_CIRCLES = ("size_",)


def make_darker_svg(src, dst):
    tree = etree.parse(src)
    root = tree.getroot()
    name = os.path.basename(src)
    accent_circles = name.startswith(ACCENT_CIRCLES)
    held = set()  # the spinner arcs, already coloured for the dark fill
    if name.startswith("wait-"):
        held = darken_spinner(root, DISC_CURSORS["wait"])
    for badge in [e for e in root.iter() if e.get("id") == "badge" and name.startswith("progress-")]:
        held |= darken_spinner(badge, BADGE_RADIUS)
    if name.startswith("wayland-cursor"):
        fill_logo_disc(root, DISC_CURSORS["wayland-cursor"], DARKER_BG)
    if name.startswith("x-cursor"):
        fill_x_logo(root, DARK_GREY_FILL, DARKER_BG)
    if name.startswith("not-allowed"):
        darken_disc(root, DISC_CURSORS["not-allowed"])
    for badge in [e for e in root.iter() if e.get("id") == "badge" and name.startswith(("no-drop", "dnd-no-drop"))]:
        darken_disc(badge, BADGE_RADIUS)
    for el in root.iter():
        if not isinstance(el.tag, str) or el in held:
            continue
        if accent_circles and etree.QName(el).localname == "circle":
            continue
        for attr in ("fill", "stroke", "stop-color"):
            v = el.get(attr)
            if v is not None and v.lower() in DARKER_MAP:
                el.set(attr, DARKER_MAP[v.lower()])
    tree.write(dst, xml_declaration=False, encoding="utf-8")


# The dark theme's spinners sit on the accent instead of white, with a white ring
# like the other themes. The lead arc turns a vivid purple, Layan's #b74aff lightened
# (1.3:1 on the accent as is, 1.8:1 here), and the green and teal are lightened to
# 3.6:1 and 2.9:1 so all three arcs still read on it.
DARK_SPIN = DARKER_SPIN


# The no-entry disc (not-allowed and the no-drop badges), the Wayland disc and the X
# are filled with a mid grey (ForegroundInactive in LayanLight.colors). Behind the red
# ring and slash that is 2.2:1.
DARK_GREY_FILL = "#b4b4b4"


def stage_dark_fills(dark):
    """Refill the dark theme's spinners and no-entry discs, in place.
    Runs after the light and darker themes are derived from these files, which must
    keep the white."""
    for name in sorted(os.listdir(dark)):
        folder = os.path.join(dark, name)
        if os.path.islink(folder):
            continue
        for f in sorted(os.listdir(folder)):
            if not f.endswith(".svg"):
                continue
            wait, progress = f.startswith("wait-"), f.startswith("progress-")
            logo = f in ("wayland-cursor.svg", "x-cursor.svg")
            disc = f == "not-allowed.svg"
            badge_disc = f in ("no-drop.svg", "dnd-no-drop.svg")
            if not (wait or progress or disc or badge_disc or logo):
                continue
            path = os.path.join(folder, f)
            tree = etree.parse(path)
            root = tree.getroot()
            if wait:
                darken_spinner(root, DISC_CURSORS["wait"], PRIMARY, DARK_SPIN)
            if f == "wayland-cursor.svg":
                fill_logo_disc(root, DISC_CURSORS["wayland-cursor"], DARK_GREY_FILL)
            if f == "x-cursor.svg":
                fill_x_logo(root, DARKER_BG, DARK_GREY_FILL)
            if disc:
                darken_disc(root, DISC_CURSORS["not-allowed"], DARK_GREY_FILL)
            for badge in [e for e in root.iter() if e.get("id") == "badge"]:
                if progress:
                    darken_spinner(badge, BADGE_RADIUS, PRIMARY, DARK_SPIN)
                elif badge_disc:
                    darken_disc(badge, BADGE_RADIUS, DARK_GREY_FILL)
            tree.write(path, xml_declaration=False, encoding="utf-8")


def stage_darker(dark, out):
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    for name in sorted(os.listdir(dark)):
        src = os.path.join(dark, name)
        dst = os.path.join(out, name)
        if os.path.islink(src):
            os.symlink(os.readlink(src), dst)
            continue
        os.makedirs(dst)
        for f in sorted(os.listdir(src)):
            if f.endswith(".svg"):
                make_darker_svg(os.path.join(src, f), os.path.join(dst, f))
            else:
                shutil.copy(os.path.join(src, f), os.path.join(dst, f))


def render_frame(svg, px):
    png = subprocess.run(
        ["rsvg-convert", "-w", str(px), "-h", str(px), svg],
        check=True, capture_output=True,
    ).stdout
    rgba = np.asarray(Image.open(BytesIO(png)).convert("RGBA")).astype(np.uint32)
    r, g, b, a = rgba[..., 0], rgba[..., 1], rgba[..., 2], rgba[..., 3]
    # Xcursor stores premultiplied ARGB
    argb = (a << 24) | (((r * a + 127) // 255) << 16) | (((g * a + 127) // 255) << 8) | ((b * a + 127) // 255)
    return argb.astype("<u4").tobytes()


def write_xcursor(path, chunks):
    """chunks: list of (nominal, width, height, xhot, yhot, delay, pixels)."""
    header = 16
    toc = 12 * len(chunks)
    pos = header + toc
    toc_bytes = b""
    body = b""
    for nominal, w, h, xh, yh, delay, pixels in chunks:
        toc_bytes += struct.pack("<III", 0xFFFD0002, nominal, pos + len(body))
        body += struct.pack("<IIIIIIIII", 36, 0xFFFD0002, nominal, 1, w, h, xh, yh, delay)
        body += pixels
    with open(path, "wb") as fh:
        fh.write(b"Xcur" + struct.pack("<III", header, 0x10000, len(chunks)))
        fh.write(toc_bytes)
        fh.write(body)


def stage_xcursor(scalable, out):
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    for name in sorted(os.listdir(scalable)):
        src = os.path.join(scalable, name)
        dst = os.path.join(out, name)
        if os.path.islink(src):
            os.symlink(os.readlink(src), dst)
            continue
        with open(os.path.join(src, "metadata.json")) as fh:
            frames = json.load(fh)
        cache = {}
        chunks = []
        for nominal in NOMINAL_SIZES:
            px = round(nominal * CANVAS / BASE_NOMINAL)
            scale = px / CANVAS
            for fr in frames:
                svg = os.path.join(src, fr["filename"])
                key = (svg, px)
                if key not in cache:
                    cache[key] = render_frame(svg, px)
                chunks.append((
                    nominal, px, px,
                    round(fr["hotspot_x"] * scale), round(fr["hotspot_y"] * scale),
                    fr.get("delay", 50), cache[key],
                ))
        write_xcursor(dst, chunks)
        print("  built", name, file=sys.stderr)


INDEX_THEME = """[Icon Theme]
Name=%s
Comment=%s, derived from Breeze Dark by the KDE VDG
"""


def build(out_dir, name, comment, scalable_stage):
    os.makedirs(out_dir, exist_ok=True)
    scalable = os.path.join(out_dir, "cursors_scalable")
    scalable_stage(scalable)
    stage_xcursor(scalable, os.path.join(out_dir, "cursors"))
    with open(os.path.join(out_dir, "index.theme"), "w") as fh:
        fh.write(INDEX_THEME % (name, comment))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--breeze", default="/usr/share/icons/breeze_cursors")
    args = ap.parse_args()
    if not os.path.isdir(os.path.join(args.breeze, "cursors_scalable")):
        sys.exit("no scalable Breeze cursors under %s" % args.breeze)
    dark = os.path.join(DARK_DIR, "cursors_scalable")
    stage_scalable(args.breeze, dark)
    # the other two are derived from the dark SVGs, before its spinners are refilled
    build(LIGHT_DIR, "layan-light-cursors", "layan accent light cursors",
          lambda out: stage_light(dark, out))
    build(DARKER_DIR, "layan-darker-cursors", "layan darker cursors in the dark window background color",
          lambda out: stage_darker(dark, out))
    stage_dark_fills(dark)
    build(DARK_DIR, "layan-dark-cursors", "layan accent dark cursors", lambda out: None)


if __name__ == "__main__":
    main()
