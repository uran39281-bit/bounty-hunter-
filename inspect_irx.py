#!/usr/bin/env python3
"""Extract and inventory the supplied IRX archive; does not execute modules."""
import argparse
import hashlib
import json
import struct
import zipfile
from pathlib import Path, PurePosixPath


def inspect(path):
    data = path.read_bytes()
    if data[:7] != b'\x7fELF\x01\x01\x01' or len(data) < 52:
        raise ValueError(f'Not ELF32 little endian: {path}')
    h = struct.unpack_from('<16sHHIIIIIHHHHHH', data)
    if h[2] != 8:
        raise ValueError(f'Not MIPS: {path}')
    imports, exports = [], []
    # Inspect allocated file-backed sections, not arbitrary non-code metadata.
    for i in range(h[12]):
        off = h[6] + i * h[11]
        if h[11] < 40 or off + 40 > len(data):
            raise ValueError('Invalid section table')
        s = struct.unpack_from('<10I', data, off)
        if s[1] == 8 or not s[2] & 2:
            continue
        if s[4] + s[5] > len(data):
            raise ValueError('Section outside file')
        for pos in range(s[4], s[4] + s[5] - 19, 4):
            magic = struct.unpack_from('<I', data, pos)[0]
            if magic not in (0x41E00000, 0x41C00000):
                continue
            raw = data[pos + 12:pos + 20].split(b'\0', 1)[0]
            if not raw or any(c < 32 or c > 126 for c in raw):
                continue
            row = {'library': raw.decode('ascii'),
                   'version': hex(struct.unpack_from('<H', data, pos + 8)[0]),
                   'file_offset': hex(pos)}
            if magic == 0x41E00000:
                ordinals = []
                cursor = pos + 20
                while cursor + 8 <= s[4] + s[5]:
                    first, delay = struct.unpack_from('<II', data, cursor)
                    if first != 0x03E00008 or delay & 0xFFFF0000 != 0x24000000:
                        break
                    ordinals.append(delay & 0xFFFF)
                    cursor += 8
                row['ordinals'] = ordinals
                imports.append(row)
            else:
                exports.append(row)
    return {'file': path.name, 'size': len(data),
            'sha256': hashlib.sha256(data).hexdigest(),
            'elf_type': hex(h[1]), 'entry': hex(h[4]),
            'imports': imports, 'exports': exports}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.archive) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f'CRC failed: {bad}')
        for entry in archive.infolist():
            p = PurePosixPath(entry.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in entry.filename:
                raise ValueError('Unsafe archive path')
            if entry.is_dir():
                continue
            if len(p.parts) != 2 or p.parts[0] != 'IRX' or p.suffix.upper() != '.IRX':
                raise ValueError(f'Unexpected entry: {p}')
            if entry.file_size > 8 * 1024 * 1024:
                raise ValueError('Oversized module')
            (args.output / p.name).write_bytes(archive.read(entry))
    rows = [inspect(p) for p in sorted(args.output.glob('*.IRX'))]
    result = {'archive_sha256': hashlib.sha256(args.archive.read_bytes()).hexdigest(),
              'modules': rows, 'modules_executed': False}
    inventory = args.output.parent / 'irx-inventory.json'
    inventory.write_text(json.dumps(result, indent=2) + '\n')
    print(f'Validated {len(rows)} modules; wrote {inventory}')


if __name__ == '__main__':
    main()
