#!/usr/bin/env python3
"""Run strict TR10 LVS; mismatch is fatal even if KLayout exits successfully."""

import argparse
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gds', required=True, type=Path)
    parser.add_argument('--top', required=True)
    parser.add_argument('--circuit', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    deck = Path(__file__).resolve().parents[2] / 'klayout/tech/lvs/lvs.lylvs'
    command = ['klayout', '-b', '-r', str(deck)]
    for key, value in [('input', args.gds.resolve()), ('top_cell', args.top),
                       ('circuit', args.circuit.resolve()),
                       ('report', args.report.resolve()),
                       ('extracted', args.report.resolve().with_suffix('.extracted'))]:
        command.extend(['-rd', f'{key}={value}'])
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(result.stdout, end='')
    verdicts = [line.strip() for line in result.stdout.splitlines()
                if line.startswith('TR10_LVS ')]
    if result.returncode != 0 or verdicts != ['TR10_LVS PASS'] or not args.report.is_file():
        print('PDN_LVS_CHECK FAIL', file=sys.stderr)
        return 1
    print('PDN_LVS_CHECK PASS (device connectivity and all top-port aliases)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
