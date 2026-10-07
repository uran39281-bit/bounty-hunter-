#!/usr/bin/env python3
"""Replace a huge generated initializer with the same ordered mappings in data.

Reject unexpected source structure and validate every guest address/index.
The original generated source is retained separately for comparison.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def compact(source, output, append=None):
    text = source.read_text()
    marker = 'namespace {\nstruct GeneratedFunctionTableInitializer {\n    GeneratedFunctionTableInitializer() {\n'
    suffix = '    }\n};\nstatic const GeneratedFunctionTableInitializer g_generatedFunctionTableInitializer;\n}\n'
    if text.count(marker) != 1 or not text.endswith(suffix):
        raise ValueError('Unexpected initializer structure')
    prefix, rest = text.split(marker)
    body = rest[:-len(suffix)]
    pattern = re.compile(r'        g_ps2RecompiledFunctionTable\[(\d+)\] = (\w+); // (0x[0-9a-f]+)\n')
    rows = pattern.findall(body)
    if not rows or pattern.sub('', body):
        raise ValueError('Initializer contains unrecognized statements')
    base = int(re.search(r'TableBase = (0x[0-9a-f]+)u;', prefix)[1], 16)
    slots = int(re.search(r'TableSlotCount = (\d+)u;', prefix)[1])
    for slot, function, address in rows:
        if not 0 <= int(slot) < slots or int(address, 16) != base + int(slot) * 4:
            raise ValueError('Address/index mismatch')
    append_count = 0
    if append is not None:
        extra = append.read_text()
        extra_base = int(re.search(r'TableBase = (0x[0-9a-f]+)u;', extra)[1], 16)
        extra_end = int(re.search(r'TableEnd = (0x[0-9a-f]+)u;', extra)[1], 16)
        extra_rows = pattern.findall(extra)
        if not extra_rows or len(extra_rows) != extra.count('g_ps2RecompiledFunctionTable[') - 1:
            raise ValueError('Unrecognized appended mappings')
        existing_addresses = {address for slot, function, address in rows}
        for slot, function, address in extra_rows:
            if int(address, 16) != extra_base + int(slot) * 4 or address in existing_addresses:
                raise ValueError('Invalid or overlapping appended address')
            rows.append((str((int(address, 16) - base) // 4), function, address))
        append_count = len(extra_rows)
        old_end = int(re.search(r'TableEnd = (0x[0-9a-f]+)u;', prefix)[1], 16)
        end = max(old_end, extra_end)
        slots = (end - base) // 4
        prefix = re.sub(r'TableEnd = 0x[0-9a-f]+u;', f'TableEnd = {end:#x}u;', prefix)
        prefix = re.sub(r'TableSlotCount = \d+u;', f'TableSlotCount = {slots}u;', prefix)
        prefix = re.sub(r'g_ps2RecompiledFunctionTable\[\d+u\]', f'g_ps2RecompiledFunctionTable[{slots}u]', prefix)
        # Both generated headers use the same include guard. Import the new
        # declarations directly rather than silently suppressing one header.
        declarations = [line for line in (append.parent / 'ps2_recompiled_functions.h').read_text().splitlines()
                        if line.startswith('void ') and line.endswith(';')]
        if not declarations:
            raise ValueError('Missing appended function declarations')
        prefix += '\n' + '\n'.join(declarations) + '\n\n'
    array = ''.join(f'    {{{slot}u, {function}}},\n' for slot, function, address in rows)
    # Data relocations hold exactly the same function pointers. Iterate in the
    # original order so duplicate indices, if present, retain last-write wins.
    result = prefix + '''namespace {
struct GeneratedRegistration { uint32_t slot; PS2Runtime::RecompiledFunction function; };
static const GeneratedRegistration kGeneratedRegistrations[] = {
''' + array + '''};
struct GeneratedFunctionTableInitializer {
    GeneratedFunctionTableInitializer() {
        for (const auto &entry : kGeneratedRegistrations)
            g_ps2RecompiledFunctionTable[entry.slot] = entry.function;
    }
};
static const GeneratedFunctionTableInitializer g_generatedFunctionTableInitializer;
}
'''
    recovered = re.findall(r'^    \{(\d+)u, (\w+)\},$', result, re.M)
    if recovered != [(slot, function) for slot, function, address in rows]:
        raise ValueError('Ordered mapping changed')
    output.write_text(result)
    return {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
            'mapping_count': len(rows), 'ordered_mapping_preserved': True,
            'appended_mapping_count': append_count,
            'table_base': hex(base), 'table_slot_count': slots}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--append', type=Path)
    args = parser.parse_args()
    result = compact(args.source, args.output, args.append)
    (args.output.parent / 'registration-compaction.json').write_text(
        json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
