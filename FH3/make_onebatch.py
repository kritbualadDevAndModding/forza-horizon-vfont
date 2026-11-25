#!/usr/bin/env python3
"""make_onebatch.py - TTF -> FH3 .vfont that fits in ONE 64K batch (needs ttf2vfont.py in the same folder).

    pip install fonttools
    python make_onebatch.py comic.ttf Anthem_A_original.vfont Anthem_A.vfont

args: <font.ttf> <original .vfont used as template> <output .vfont> [--chars "..."] [--b 0.1992] [--scale 1.0]
The script lowers curve detail automatically until total vertices and indices stay under 65000.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FH3ttf2vfont

ap = argparse.ArgumentParser()
ap.add_argument('ttf'); ap.add_argument('template'); ap.add_argument('output')
ap.add_argument('--chars'); ap.add_argument('--all', action='store_true', help='include every glyph of the font (BMP)'); ap.add_argument('--b', type=float, default=0.1992)
ap.add_argument('--scale', type=float, default=1.0); ap.add_argument('--name', default='Anthem_A')
x = ap.parse_args()
if os.path.abspath(x.template) == os.path.abspath(x.output):
    sys.exit("output must differ from the template")
FH3ttf2vfont.convert(argparse.Namespace(
    input=x.ttf, output=x.output, template=x.template, name=x.name, chars=x.chars, all=x.all,
    scale=x.scale, fringe=0.0283, b=x.b, flatness=0.0012, ascent=None, descent=None,
    game='fh3', keep_kerning=False, single_batch=True))
