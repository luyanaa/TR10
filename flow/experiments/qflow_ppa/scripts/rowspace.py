#!/usr/bin/env python3
"""Post-process a GrayWolf/qflow DEF into a TR10 237.6 um-pitch row DEF.

qflow 1.4's GrayWolf rowSep/numrows knobs do not produce the TR10 row pitch
(child cells 59.4 um high + 178.2 um routing channel).  This script keeps the
GrayWolf x placement and shifts each row, extends DIEAREA/TRACKS, moves the
top-edge pins, and (optionally) strips the qflow power SPECIALNETS so qrouter
can read the signal netlist.
"""
import argparse, re

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--def', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--old-row-pitch', type=float, default=59.4)
    ap.add_argument('--new-row-pitch', type=float, default=237.6)
    ap.add_argument('--row0', type=float, default=2.7)
    ap.add_argument('--strip-specialnets', action='store_true')
    a = ap.parse_args()
    s = open(a.def).read()
    if a.strip_specialnets:
        s = re.sub(r'\nSPECIALNETS \d+ ;.*?\nEND SPECIALNETS\n', '\n', s, flags=re.S)
    old_p = int(round(a.old_row_pitch * 1000))
    new_p = int(round(a.new_row_pitch * 1000))
    row0 = int(round(a.row0 * 1000))
    m = re.search(r'DIEAREA \( (-?\d+) (-?\d+) \) \( (\d+) (\d+) \)', s)
    if not m:
        raise SystemExit('no DIEAREA')
    x0, y0, x1, y1 = map(int, m.groups())
    # shift components only (not pins)
    def shift(m):
        name, cell, x, y, orient = m.group(1), m.group(2), int(m.group(3)), int(m.group(4)), m.group(5)
        row = max(0, (y - row0) // old_p)
        return f'- {name} {cell} + PLACED ( {x} {y + row * (new_p - old_p)} ) {orient} ;'
    s = re.sub(r'(?m)^- (\S+) (\S+) \+ PLACED \( (-?\d+) (-?\d+) \) (\w+) ;', shift, s)
    max_row = 0
    for mm in re.finditer(r'(?m)^- \S+ \S+ \+ PLACED \( (-?\d+) (-?\d+) \)', s):
        max_row = max(max_row, (int(mm.group(2)) - row0) // new_p)
    new_h = y1 + max_row * (new_p - old_p)
    s = s[:m.start()] + f'DIEAREA ( {x0} {y0} ) ( {x1} {new_h} )' + s[m.end():]
    # extend M1 Y tracks
    def tracks(mm):
        return f'TRACKS Y {y0} DO {max(1, (new_h - y0) // 5400 + 1)} STEP 5400 LAYER M1'
    s = re.sub(r'(?m)^TRACKS Y -?\d+ DO \d+ STEP 5400 LAYER M1', tracks, s)
    # move pins that were on the old top edge to the new top edge
    old_top = y1
    def pin_shift(mm):
        x, y, orient = int(mm.group(1)), int(mm.group(2)), mm.group(3)
        if y > old_top - 20000:
            y = new_h + 5400
        return f'+ PLACED ( {x} {y} ) {orient} ;'
    i = s.index('PINS '); j = s.index('END PINS')
    pins = s[i:j]
    pins = re.sub(r'\+ PLACED \( (-?\d+) (-?\d+) \) (\w+) ;', pin_shift, pins)
    # add DIRECTION/USE if missing
    out = []
    current = None
    for line in pins.splitlines():
        mm = re.match(r'- (\S+) \+ NET ', line)
        if mm: current = mm.group(1)
        out.append(line)
        if line.strip().startswith('+ DIRECTION'):
            use = 'POWER' if current == 'VDD' else ('GROUND' if current == 'GND' else 'SIGNAL')
            if '+ USE ' not in pins:
                out.append('  + USE ' + use)
    pins = '\n'.join(out)
    s = s[:i] + pins + s[j:]
    open(a.out, 'w').write(s)
    print(f'{a.def} -> {a.out}: new height {new_h/1000:.1f} um, max row {max_row}')

if __name__ == '__main__':
    main()
