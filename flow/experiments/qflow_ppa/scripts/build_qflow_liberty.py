#!/usr/bin/env python3
"""Remove DFF2 from the TR10 Liberty for qflow.

The Liberty DFF2 has single D/Q/QB pins while the LEF DFF2 is the dual
D0/Q0/D1/Q1 macro; qflow's vlog2Cel cannot place the single-pin view.
"""
import re, sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src).read()
m = re.search(r'(?m)^[ \t]*cell \(DFF2\) \{', s)
if not m:
    raise SystemExit('DFF2 not found')
i = m.end(); depth = 1
while depth and i < len(s):
    if s[i] == '{': depth += 1
    elif s[i] == '}': depth -= 1
    i += 1
s = s[:m.start()] + s[i:]
assert 'cell (DFF2)' not in s
open(dst, 'w').write(s)
print(dst)
