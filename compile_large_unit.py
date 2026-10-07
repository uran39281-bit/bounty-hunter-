#!/usr/bin/env python3
"""Compile the largest game unity unit without native debug information.

Use only after a cancelled build has retained the other game objects. The
runtime probe records guest registers independently of native debug symbols.
"""
import argparse
import json
import shlex
import subprocess
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build', type=Path)
    parser.add_argument('--compiler', type=Path, help='Optional Clang++ executable for this unit')
    parser.add_argument('--repair-incomplete', action='store_true',
                        help='Also compile missing or zero-byte unity objects after interruption')
    args = parser.parse_args()
    commands = json.loads((args.build / 'compile_commands.json').read_text())
    candidates = []
    for entry in commands:
        if '/Unity/' not in entry['file']:
            continue
        tokens = shlex.split(entry['command'])
        output = Path(entry['directory']) / tokens[tokens.index('-o')+1]
        large = 'sub_00105900_0x105900.cpp' in Path(entry['file']).read_text()
        incomplete = not output.is_file() or output.stat().st_size == 0
        if (args.repair_incomplete and incomplete) or (not args.repair_incomplete and large):
            candidates.append(entry)
    if not args.repair_incomplete and len(candidates) != 1:
        raise ValueError('Expected one unity unit containing the largest function')
    for entry in candidates:
        tokens = shlex.split(entry['command'])
        if args.compiler:
            command = [str(args.compiler.resolve()), '-g0']
            skip = False
            for token in tokens[1:]:
                if skip:
                    skip = False
                    continue
                if token == '-include':
                    skip = True  # GCC's PCH cannot be consumed by Clang.
                    continue
                if token not in ['-g', '-fpch-preprocess', '-Winvalid-pch']:
                    command.append(token)
        else:
            command = [token for token in tokens if token != '-g']
            command[1:1] = ['-g0', '-fno-var-tracking', '-fno-var-tracking-assignments']
        subprocess.run(command, cwd=entry['directory'], check=True)
        print('Compiled', Path(entry['file']).name, flush=True)
    print('Requested units complete; resume the CMake build and link diagnostic next')

if __name__ == '__main__':
    main()
