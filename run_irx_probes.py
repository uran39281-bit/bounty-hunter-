#!/usr/bin/env python3
"""Repeat isolated IRX loader and entry tests using a compiled probe_irx.

The entry test executes MIPS instructions in PS2Recomp's IOP interpreter.
It does not run the statically translated EE game, use a real boot order,
or prove that hardware/RPC services work.
"""
import argparse
import json
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe', type=Path)
    parser.add_argument('--modules', type=Path,
                        default=Path(__file__).resolve().parent / 'game-irx')
    parser.add_argument('--output', type=Path,
                        default=Path(__file__).resolve().parent / 'irx-probe-results.json')
    args = parser.parse_args()
    rows = []
    for module in sorted(args.modules.glob('*.IRX')):
        row = {'module': module.name}
        for mode in ('load', 'init'):
            try:
                result = subprocess.run([str(args.probe.resolve()), mode,
                                         str(module.resolve())],
                                        capture_output=True, text=True, timeout=10)
                row[mode] = {'returncode': result.returncode,
                             'stdout': result.stdout, 'stderr': result.stderr}
            except subprocess.TimeoutExpired as error:
                row[mode] = {'timeout_seconds': 10,
                             'stdout': (error.stdout or b'').decode(errors='replace')}
        rows.append(row)
        print(module.name, row['load'].get('returncode'),
              row['init'].get('returncode'), flush=True)
    args.output.write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
