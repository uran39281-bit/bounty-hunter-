#!/usr/bin/env python3
"""Add constructor and candidate callback entry hints to an analyzer config.

Candidate callbacks are constants materialized in constructor instructions
that point into primary code and begin with a stack-allocation prologue.
Hints expose additional native entry labels; they do not rewrite instructions.
"""
import argparse
import hashlib
import json
import re
import struct
import tomllib
from pathlib import Path

EXPECTED_SHA256 = '51c56737105d1186f0b14155e39d8af67e63b12c4ac0543e1f0e178ccd6a4304'


def entries(executable):
    data = executable.read_bytes()
    if hashlib.sha256(data).hexdigest() != EXPECTED_SHA256:
        raise ValueError('Expected the inspected SLUS_204.20 build')
    word = lambda address: struct.unpack_from('<I', data, 0x100 + address - 0x100000)[0]
    constructors = list(struct.unpack_from('<114I', data, 0x100 + 0x3b5b50 - 0x100000))
    registers, callbacks = {}, set()
    # Scan the primary code and the confirmed constructor island separately.
    addresses = list(range(0x100000, 0x359880, 4)) + list(range(0x3a6be0, 0x3b5b50, 4))
    for address in addresses:
        if address == 0x3a6be0:
            registers.clear()
        instruction = word(address)
        op, rs, rt, rd = instruction >> 26, (instruction >> 21) & 31, (instruction >> 16) & 31, (instruction >> 11) & 31
        immediate = instruction & 0xffff
        if op == 15:
            registers[rt] = (immediate << 16, address)
        elif op in (9, 25, 13):
            prior = registers.get(rs)
            if prior and address - prior[1] <= 48:
                signed = immediate if immediate < 0x8000 else immediate - 0x10000
                value = ((prior[0] + signed) & 0xffffffff) if op != 13 else prior[0] | immediate
                registers[rt] = (value, prior[1])
                if 0x100000 <= value < 0x359880 and value % 4 == 0:
                    probe = [word(value + offset) for offset in range(0, 32, 4)
                             if value + offset < 0x359880]
                    stack_prologue = any((first >> 26) in (9, 25) and ((first >> 21) & 31) == 29 and ((first >> 16) & 31) == 29 and first & 0x8000 for first in probe[:4])
                    leaf_return = any(first == 0x03e00008 or first >> 26 == 2 for first in probe)
                    if stack_prologue or leaf_return:
                        callbacks.add(value)
            else:
                registers.pop(rt, None)
        elif op in (0, 28):
            if rd:
                registers.pop(rd, None)
        elif op == 3:
            registers.pop(31, None)
        elif op in (32, 33, 34, 35, 36, 37, 38, 39, 48, 52, 55):
            registers.pop(rt, None)
    return constructors, sorted(callbacks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--output-directory', type=Path)
    args = parser.parse_args()
    constructors, callbacks = entries(args.executable)
    text = args.config.read_text()
    settings = tomllib.loads(text)
    existing = settings['general'].get('entry_points', [])
    hints = sorted(set(existing + [f'ctor_{v:08X}@{v:#x}' for v in constructors] +
                       [f'callback_{v:08X}@{v:#x}' for v in callbacks]))
    if 'entry_points' in settings['general']:
        text = re.sub(r'^entry_points\s*=\s*\[[\s\S]*?\]',
                      'entry_points = ' + json.dumps(hints), text, count=1, flags=re.M)
    else:
        text = text.replace('[general]\n', '[general]\nentry_points = ' + json.dumps(hints) + '\n', 1)
    if args.output_directory:
        text = re.sub(r'^output = .*$', 'output = ' + json.dumps(str(args.output_directory)), text, count=1, flags=re.M)
    assert tomllib.loads(text)['general']['entry_points'] == hints
    args.config.write_text(text)
    evidence = {'constructors': constructors, 'candidate_callbacks': callbacks,
                'total_entry_hints': len(hints), 'original_executable_sha256': EXPECTED_SHA256,
                'candidate_callback_boundaries_are_inferred': True}
    (args.config.parent / 'startup-entry-hints.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(f'{len(constructors)} constructors, {len(callbacks)} candidate callbacks; {len(hints)} total hints')


if __name__ == '__main__':
    main()
