#!/usr/bin/env python3
"""
FH3ttf2vfont.py  -  convert a TrueType/OpenType font into Forza Horizon 3 (Durango) .vfont

Usage
    pip install fonttools
    python FH3ttf2vfont.py comic.ttf Anthem_A.vfont
    python FH3ttf2vfont.py comic.ttf Anthem_A.vfont --template original/Anthem_A.vfont

Recommended: pass --template with the ORIGINAL .vfont you are replacing. The script then
  * copies the unknown header fields from it,
  * produces the same set of code points the game already expects.

File layout (reverse engineered from Anthem_A.vfont, little endian)
  0x00  char[128]   font name, zero padded
  0x80  u32 glyphCount | 0 | 0 | u32 kernCount | header fields up to 0xC0 (metrics)
  0xC0  glyphCount * 28 bytes : u32 codepoint, f32 advance(em), u32 nVerts, u32 nIdx, 3*u32 (0)
        kernCount  * 12 bytes : u32 left, u32 right, f32 adjustment(em)
        u32 glyphCount
        per glyph  : u32 codepoint, u32 nVerts, u32 nIdx,
                     nVerts * 8 bytes  (4 x half float: x+0.5, y, a, b)
                     nIdx   * 2 bytes  (u16 triangle list)
  Vertex meaning
        b == 1.0           : solid fill triangle (outline inset by FRINGE)
        b  > 0 / b < 0     : anti-alias fringe quad, inner (+b) / outer (-b) vertices;
                             the real glyph edge is where b == 0 (midway)
  All triangles are counter-clockwise (y up).  Em = 1.0, baseline y = 0.

Things that are GUESSED (not verified against the game):
  - header fields other than glyph/kern counts and the space advance
  - the magnitude of b on fringe vertices (--b)
  - the 'a' component, written as 0 (the original only uses it on curved segments)
Test on a COPY of the game files and keep backups.
"""
import argparse, math, os, struct, sys

try:
    from fontTools.ttLib import TTFont
    from fontTools.pens.basePen import BasePen
except ImportError:
    sys.exit("fontTools is required:  pip install fonttools")

# header bytes 0x90..0xBF taken from Anthem_A.vfont (used when no --template is given)
DEFAULT_HDR = bytes.fromhex(
    "ec51383e36504f7de3a57b3fd7030000"
    "cf000000f802000010ffffff3a000000"
    "d703000031ffffff1d000000e8030000")

# Forza Horizon 3 (header is 0xCC bytes, 12 bytes longer than FH2; bytes 0x90..0xCB)
DEFAULT_HDR_FH3 = bytes.fromhex(
    "fa7e6a3e00000000c9767e3f1f000000"
    "e60300000201000000000000ee020000"
    "06ffffffc8000000ee02000006ffffff"
    "c8000000e8030000c2020000")

# --------------------------------------------------------------------------- outline
class FlattenPen(BasePen):
    """Collects flattened closed contours in em units."""
    def __init__(self, glyphSet, upm, tol):
        super().__init__(glyphSet)
        self.s = 1.0 / upm
        self.tol = tol
        self.contours = []
        self.cur = None

    def _moveTo(self, p):
        self.cur = [(p[0] * self.s, p[1] * self.s)]

    def _lineTo(self, p):
        self.cur.append((p[0] * self.s, p[1] * self.s))

    def _qCurveToOne(self, p1, p2):
        p0 = self.cur[-1]
        p1 = (p1[0] * self.s, p1[1] * self.s)
        p2 = (p2[0] * self.s, p2[1] * self.s)
        D = math.hypot(p0[0] - 2 * p1[0] + p2[0], p0[1] - 2 * p1[1] + p2[1])
        n = max(1, min(32, math.ceil(math.sqrt(D / (4 * self.tol)))))
        for i in range(1, n + 1):
            t = i / n
            u = 1 - t
            self.cur.append((u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                             u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]))

    def _curveToOne(self, p1, p2, p3):
        p0 = self.cur[-1]
        p1 = (p1[0] * self.s, p1[1] * self.s)
        p2 = (p2[0] * self.s, p2[1] * self.s)
        p3 = (p3[0] * self.s, p3[1] * self.s)
        D = max(math.hypot(p0[0] - 2 * p1[0] + p2[0], p0[1] - 2 * p1[1] + p2[1]),
                math.hypot(p1[0] - 2 * p2[0] + p3[0], p1[1] - 2 * p2[1] + p3[1]))
        n = max(1, min(48, math.ceil(math.sqrt(0.75 * D / self.tol))))
        for i in range(1, n + 1):
            t = i / n
            u = 1 - t
            self.cur.append((u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
                             u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1]))

    def _closePath(self):
        if self.cur and len(self.cur) > 2:
            self.contours.append(self.cur)
        self.cur = None

    _endPath = _closePath


def area(poly):
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] -
                     poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))


def clean(poly, eps=0.0015):
    out = []
    for p in poly:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > eps:
            out.append(p)
    while len(out) > 1 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= eps:
        out.pop()
    # drop (almost) collinear points
    changed = True
    while changed and len(out) > 3:
        changed = False
        res = []
        n = len(out)
        for i in range(n):
            a, b, c = out[i - 1], out[i], out[(i + 1) % n]
            cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            if abs(cr) < 1e-7:
                changed = True
                continue
            res.append(b)
        out = res
    return out


def point_in_poly(pt, poly):
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def group_contours(contours):
    """-> list of (outer, [holes]); outer CCW, holes CW."""
    cs = [clean(c) for c in contours]
    cs = [c for c in cs if len(c) >= 3 and abs(area(c)) > 1e-6]
    if not cs:
        return []
    big = max(cs, key=lambda c: abs(area(c)))
    outer_sign = 1 if area(big) > 0 else -1
    outers, holes = [], []
    for c in cs:
        (outers if (area(c) > 0) == (outer_sign > 0) else holes).append(c)
    groups = []
    for o in outers:
        groups.append([o if area(o) > 0 else o[::-1], []])
    for h in holes:
        h = h if area(h) < 0 else h[::-1]
        best = None
        for g in groups:
            if point_in_poly(h[0], g[0]):
                if best is None or abs(area(g[0])) < abs(area(best[0])):
                    best = g
        if best is not None:
            best[1].append(h)
    return [(g[0], g[1]) for g in groups]

# --------------------------------------------------------------------------- inset
def offset_ring(ring, d):
    """Miter offset of a CCW-interior-left ring by d to the left (inward). Returns new points."""
    n = len(ring)
    out = []
    for i in range(n):
        a, b, c = ring[i - 1], ring[i], ring[(i + 1) % n]
        e1 = (b[0] - a[0], b[1] - a[1]); l1 = math.hypot(*e1) or 1
        e2 = (c[0] - b[0], c[1] - b[1]); l2 = math.hypot(*e2) or 1
        n1 = (-e1[1] / l1, e1[0] / l1)
        n2 = (-e2[1] / l2, e2[0] / l2)
        k = 1 + n1[0] * n2[0] + n1[1] * n2[1]
        k = max(k, 0.35)                       # miter limit
        out.append((b[0] + d * (n1[0] + n2[0]) / k, b[1] + d * (n1[1] + n2[1]) / k))
    return out

# --------------------------------------------------------------------------- triangulation
def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _seg_intersect(p1, p2, p3, p4):
    d1 = _cross(p3, p4, p1); d2 = _cross(p3, p4, p2)
    d3 = _cross(p1, p2, p3); d4 = _cross(p1, p2, p4)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and d1 * d2 != 0 and d3 * d4 != 0


def _bridge(poly, hole, others):
    """Merge hole (CW) into poly (CCW). poly/hole are lists of (x,y). Returns merged list."""
    mi = max(range(len(hole)), key=lambda i: hole[i][0])
    M = hole[mi]
    edges = [(poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly))]
    for h in [hole] + others:
        edges += [(h[i], h[(i + 1) % len(h)]) for i in range(len(h))]
    order = sorted(range(len(poly)), key=lambda i: (poly[i][0] - M[0]) ** 2 + (poly[i][1] - M[1]) ** 2)
    for vi in order:
        V = poly[vi]
        ok = True
        for a, b in edges:
            if a == V or b == V or a == M or b == M:
                continue
            if _seg_intersect(M, V, a, b):
                ok = False
                break
        if ok:
            ring = hole[mi:] + hole[:mi] + [M]
            return poly[:vi + 1] + ring + [V] + poly[vi + 1:]
    vi = order[0]
    ring = hole[mi:] + hole[:mi] + [M]
    return poly[:vi + 1] + ring + [poly[vi]] + poly[vi + 1:]


def _in_tri(p, a, b, c):
    d1 = _cross(a, b, p); d2 = _cross(b, c, p); d3 = _cross(c, a, p)
    neg = d1 < 0 or d2 < 0 or d3 < 0
    pos = d1 > 0 or d2 > 0 or d3 > 0
    return not (neg and pos)


def ear_clip(pts):
    """pts: CCW simple polygon with possible bridge duplicates. -> list of (i,j,k) indices."""
    n = len(pts)
    idx = list(range(n))
    tris = []
    guard = 0
    i = 0
    while len(idx) > 3 and guard < 20000:
        guard += 1
        m = len(idx)
        found = False
        for s in range(m):
            k = (i + s) % m
            ia, ib, ic = idx[k - 1], idx[k], idx[(k + 1) % m]
            a, b, c = pts[ia], pts[ib], pts[ic]
            if _cross(a, b, c) <= 1e-12:
                continue
            bad = False
            for j in idx:
                if j in (ia, ib, ic):
                    continue
                p = pts[j]
                if p == a or p == b or p == c:
                    continue
                if _in_tri(p, a, b, c):
                    bad = True
                    break
            if not bad:
                tris.append((ia, ib, ic))
                idx.pop(k)
                i = k % len(idx)
                found = True
                break
        if not found:                       # degenerate input: remove flattest vertex
            k = min(range(m), key=lambda q: abs(_cross(pts[idx[q - 1]], pts[idx[q]], pts[idx[(q + 1) % m]])))
            ia, ib, ic = idx[k - 1], idx[k], idx[(k + 1) % m]
            if _cross(pts[ia], pts[ib], pts[ic]) > 0:
                tris.append((ia, ib, ic))
            idx.pop(k)
            i = k % len(idx)
    if len(idx) == 3 and _cross(pts[idx[0]], pts[idx[1]], pts[idx[2]]) > 0:
        tris.append(tuple(idx))
    return tris


def triangulate(outer, holes):
    poly = list(outer)
    hs = sorted(holes, key=lambda h: -max(p[0] for p in h))
    for n, h in enumerate(hs):
        poly = _bridge(poly, h, hs[n + 1:])
    return poly, ear_clip(poly)

# --------------------------------------------------------------------------- glyph mesh
def build_mesh(contours, fringe, bval, scale=1.0):
    """-> (verts[(x,y,a,b)], indices) in vfont convention (x already +0.5)."""
    verts, idx = [], []
    fills = []
    for outer, holes in group_contours([[(x * scale, y * scale) for x, y in c] for c in contours]):
        rings = [outer] + holes
        inner_rings = []
        for r in rings:
            q = offset_ring(r, fringe)
            o = offset_ring(r, -fringe)
            inner_rings.append(q)
            n = len(r)
            for i in range(n):
                j = (i + 1) % n
                base = len(verts)
                for p, b in ((q[i], bval), (o[i], -bval), (q[j], bval), (o[j], -bval)):
                    verts.append((p[0] + 0.5, p[1], 0.0, b))
                idx += [base, base + 1, base + 2, base + 1, base + 3, base + 2]
        fills.append((inner_rings[0], inner_rings[1:]))
    for q_outer, q_holes in fills:
        poly, tris = triangulate(q_outer, q_holes)
        base = len(verts)
        for p in poly:
            verts.append((p[0] + 0.5, p[1], 0.0, 1.0))
        for a, b, c in tris:
            idx += [base + a, base + b, base + c]
    return verts, idx

# --------------------------------------------------------------------------- kerning
def read_kerning(font, cp_of_glyph, upm):
    pairs = {}
    if 'kern' in font:
        for st in font['kern'].kernTables:
            for (l, r), v in getattr(st, 'kernTable', {}).items():
                if l in cp_of_glyph and r in cp_of_glyph:
                    pairs[(cp_of_glyph[l], cp_of_glyph[r])] = v / upm
    if 'GPOS' in font:
        gpos = font['GPOS'].table
        feats = [f for f in (gpos.FeatureList.FeatureRecord if gpos.FeatureList else []) if f.FeatureTag == 'kern']
        lookups = set()
        for f in feats:
            lookups.update(f.Feature.LookupListIndex)
        for li in sorted(lookups):
            lk = gpos.LookupList.Lookup[li]
            for st in lk.SubTable:
                if lk.LookupType == 9:
                    st = st.ExtSubTable
                if getattr(st, 'LookupType', lk.LookupType) != 2 and not hasattr(st, 'Format'):
                    continue
                if not hasattr(st, 'Coverage') or not (hasattr(st, 'PairSet') or hasattr(st, 'Class1Record')):
                    continue
                if st.Format == 1:
                    for g1, ps in zip(st.Coverage.glyphs, st.PairSet):
                        for pvr in ps.PairValueRecord:
                            v = getattr(pvr.Value1, 'XAdvance', 0) if pvr.Value1 else 0
                            if v and g1 in cp_of_glyph and pvr.SecondGlyph in cp_of_glyph:
                                pairs.setdefault((cp_of_glyph[g1], cp_of_glyph[pvr.SecondGlyph]), v / upm)
                elif st.Format == 2:
                    cd1 = st.ClassDef1.classDefs
                    cd2 = st.ClassDef2.classDefs
                    cls2 = {}
                    for g, c in cd2.items():
                        cls2.setdefault(c, []).append(g)
                    cls2.setdefault(0, [])
                    cls1 = {}
                    for g in st.Coverage.glyphs:
                        cls1.setdefault(cd1.get(g, 0), []).append(g)
                    for c1, rec in enumerate(st.Class1Record):
                        for c2, r2 in enumerate(rec.Class2Record):
                            v = getattr(r2.Value1, 'XAdvance', 0) if r2.Value1 else 0
                            if not v:
                                continue
                            if c2 == 0:
                                continue          # class 0 = "everything else": skipped to limit size
                            for g1 in cls1.get(c1, []):
                                for g2 in cls2.get(c2, []):
                                    if g1 in cp_of_glyph and g2 in cp_of_glyph:
                                        pairs.setdefault((cp_of_glyph[g1], cp_of_glyph[g2]), v / upm)
    return {k: v for k, v in pairs.items() if abs(v) > 1e-4}

# --------------------------------------------------------------------------- vfont I/O
def detect_layout(d):
    """Return (header_size, glyph_count, kern_count) for a .vfont (FH2: 0xC0, FH3: 0xCC)."""
    cnt = struct.unpack_from('<I', d, 0x80)[0]
    nk = struct.unpack_from('<I', d, 0x8C)[0]
    for H in (0xC0, 0xCC):
        try:
            recs = [struct.unpack_from('<IfIIIII', d, H + i * 28) for i in range(cnt)]
        except struct.error:
            continue
        total = H + cnt * 28 + nk * 12 + 4 + cnt * 12 + sum(r[2] * 8 + r[3] * 2 for r in recs)
        if total == len(d):
            return H, cnt, nk
    sys.exit("unrecognised .vfont layout (neither FH2 0xC0 nor FH3 0xCC header)")


def read_template(path):
    d = open(path, 'rb').read()
    H, cnt, nk = detect_layout(d)
    cps = [struct.unpack_from('<I', d, H + i * 28)[0] for i in range(cnt)]
    return d[0x90:H], cps, H, nk


def default_charset(font_cps):
    keep = set()
    for lo, hi in ((0x20, 0x7E), (0xA0, 0x24F), (0x2010, 0x2044), (0x20A0, 0x20CF),
                   (0x2122, 0x2122), (0x2190, 0x2193), (0x2200, 0x2200)):
        keep.update(c for c in font_cps if lo <= c <= hi)
    return keep


def convert(a):
    font = TTFont(a.input)
    upm = font['head'].unitsPerEm
    cmap = font.getBestCmap()
    gs = font.getGlyphSet()
    order = font.getGlyphOrder()
    notdef = '.notdef' if '.notdef' in gs else order[0]

    tmpl_hdr, tmpl_cps, H, tmpl_nk = (None, None, 0xCC if a.game == 'fh3' else 0xC0, None)
    if a.template:
        tmpl_hdr, tmpl_cps, H, tmpl_nk = read_template(a.template)
        print("template: %s layout, %d glyphs, %d kerning pairs"
              % ("FH3 (0xCC header)" if H == 0xCC else "FH2 (0xC0 header)", len(tmpl_cps), tmpl_nk))
    if a.chars:
        wanted = {ord(ch) for ch in a.chars}
    elif tmpl_cps:
        wanted = set(tmpl_cps)
    elif a.all:
        wanted = {c for c in cmap if c < 0x10000 and c >= 0x20}
    else:
        wanted = default_charset(cmap.keys())
    wanted |= {10, 13, 0xFFFD}
    placeholder = lambda c: c < 0x20 or c == 0xFFFD     # drawn with the font's .notdef box
    cps = sorted(wanted)

    missing = [c for c in cps if c not in cmap and not placeholder(c)]
    if missing and a.template:
        print("note: %d code points of the template are missing in the TTF (e.g. %s) - skipped"
              % (len(missing), ", ".join("U+%04X" % c for c in missing[:8])))
    cps = [c for c in cps if c in cmap or placeholder(c)]

    cp_of_glyph = {}
    for c in cps:
        if c in cmap:
            cp_of_glyph.setdefault(cmap[c], c)

    fl = a.flatness
    while True:
        glyphs = []
        for n, cp in enumerate(cps):
            gname = cmap.get(cp, notdef) if not (cp < 0x20 and cp not in cmap) else notdef
            pen = FlattenPen(gs, upm, fl)
            gs[gname].draw(pen)
            adv = gs[gname].width / upm * a.scale
            if placeholder(cp) and cp not in cmap:
                adv = gs[notdef].width / upm * a.scale
            verts, idx = build_mesh(pen.contours, a.fringe, a.b, a.scale)
            if len(verts) > 65535:
                sys.exit("glyph U+%04X has too many vertices; raise --flatness" % cp)
            glyphs.append((cp, adv, verts, idx))
            if (n + 1) % 50 == 0:
                print("  %d / %d glyphs" % (n + 1, len(cps)), file=sys.stderr)
        tv = sum(len(g[2]) for g in glyphs)
        ti = sum(len(g[3]) for g in glyphs)
        if not a.single_batch or (tv < 65000 and ti < 65000):
            break
        fl *= 1.25
        if fl > 0.05:
            sys.exit("cannot fit in one batch even when coarse; use --chars to include fewer glyphs")
        print("single-batch: %d verts / %d indices too many, retrying with flatness %.4f" % (tv, ti, fl))
    print("mesh totals: %d vertices, %d indices (original FH3 Anthem_A: 20672 / 36996)" % (tv, ti))

    kern = read_kerning(font, cp_of_glyph, upm)
    kern = sorted((l, r, v * a.scale) for (l, r), v in kern.items() if l in cps and r in cps)
    if tmpl_nk == 0 and kern:
        print("note: template has no kerning, dropping %d kerning pairs (use --keep-kerning to keep)" % len(kern)) \
            if not a.keep_kerning else None
        kern = kern if a.keep_kerning else []

    # header (0x90..H)
    hdr = bytearray(tmpl_hdr if tmpl_hdr else (DEFAULT_HDR_FH3 if H == 0xCC else DEFAULT_HDR))
    space = next((g[1] for g in glyphs if g[0] == 0x20), 0.25)
    struct.pack_into('<f', hdr, 0x00, space)
    if a.ascent is not None or a.descent is not None:
        if H != 0xC0:
            print("warning: --ascent/--descent are only mapped for the FH2 header; ignored for FH3")
        else:
            asc = a.ascent if a.ascent is not None else struct.unpack_from('<i', hdr, 0x0C)[0]
            dsc = a.descent if a.descent is not None else struct.unpack_from('<i', hdr, 0x10)[0]
            struct.pack_into('<f', hdr, 0x08, asc / 1000.0)
            struct.pack_into('<i', hdr, 0x0C, asc)
            struct.pack_into('<i', hdr, 0x10, dsc)
            struct.pack_into('<i', hdr, 0x20, asc)
            struct.pack_into('<i', hdr, 0x24, -dsc)

    name = (a.name or os.path.splitext(os.path.basename(a.output))[0]).encode('ascii', 'ignore')[:127]
    out = bytearray()
    out += name.ljust(0x80, b'\0')
    out += struct.pack('<IIII', len(glyphs), 0, 0, len(kern))
    out += hdr
    assert len(out) == H, (len(out), H)
    for cp, adv, v, i in glyphs:
        out += struct.pack('<IfIIIII', cp, adv, len(v), len(i), 0, 0, 0)
    for l, r, v in kern:
        out += struct.pack('<IIf', l, r, v)
    out += struct.pack('<I', len(glyphs))
    for cp, adv, v, i in glyphs:
        out += struct.pack('<III', cp, len(v), len(i))
        for x, y, aa, bb in v:
            out += struct.pack('<4e', x, y, aa, bb)
        out += struct.pack('<%dH' % len(i), *i)
    open(a.output, 'wb').write(out)
    print("wrote %s: %d glyphs, %d kerning pairs, %d bytes" % (a.output, len(glyphs), len(kern), len(out)))


def main():
    ap = argparse.ArgumentParser(description="TTF/OTF -> Forza Horizon 2 .vfont")
    ap.add_argument('input')
    ap.add_argument('output')
    ap.add_argument('--template', help="original .vfont: copy header fields and code point set")
    ap.add_argument('--game', choices=['fh2', 'fh3'], default='fh2',
                    help="header layout when no --template is given (FH3 header is 0xCC bytes)")
    ap.add_argument('--single-batch', action='store_true',
                    help="keep total vertices and indices under 65000 (the game's loader packs glyphs into 64K batches; stock fonts fit in one)")
    ap.add_argument('--keep-kerning', action='store_true', help="write kerning even if the template has none")
    ap.add_argument('--name', help="font name stored in the header (default: output file name)")
    ap.add_argument('--chars', help="explicit characters to include, e.g. 'ABC abc 123'")
    ap.add_argument('--all', action='store_true', help="include every BMP code point of the font")
    ap.add_argument('--scale', type=float, default=1.0, help="uniform scale (em units), default 1.0")
    ap.add_argument('--fringe', type=float, default=0.0283, help="half width of the AA fringe in em (original: 0.0283)")
    ap.add_argument('--b', type=float, default=0.1992, help="|b| value of fringe vertices (original: 0.04..0.8, guessed)")
    ap.add_argument('--flatness', type=float, default=0.0012, help="curve flattening tolerance in em")
    ap.add_argument('--ascent', type=int, help="header ascent in 1/1000 em (original: 983)")
    ap.add_argument('--descent', type=int, help="header descent in 1/1000 em, positive (original: 207)")
    convert(ap.parse_args())


if __name__ == '__main__':
    main()
