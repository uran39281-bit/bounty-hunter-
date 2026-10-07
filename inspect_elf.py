#!/usr/bin/env python3
"""Inspect an uploaded PS2 ELF without executing it. Standard library only."""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path


def inspect(path: Path, config: Path):
    data = path.read_bytes()
    if data[:7] != b'\x7fELF\x01\x01\x01':
        raise ValueError('Expected a little-endian ELF32 executable')
    h = struct.unpack_from('<HHIIIIIHHHHHH', data, 16)
    kind, machine, version, entry, phoff, shoff, flags, ehsize, phsize, phnum, shsize, shnum, shstrndx = h
    if machine != 8 or phsize != 32 or shsize != 40:
        raise ValueError('Unexpected ELF machine or table entry size')
    segments = []
    for i in range(phnum):
        ptype, offset, vaddr, paddr, filesz, memsz, pflags, align = struct.unpack_from('<IIIIIIII', data, phoff + i * phsize)
        if offset + filesz > len(data):
            raise ValueError('Program segment exceeds file size')
        segments.append(dict(type=ptype, file_offset=offset, virtual_address=hex(vaddr), file_size=filesz, memory_size=memsz, flags=pflags, alignment=align))
    headers = [struct.unpack_from('<IIIIIIIIII', data, shoff + i * shsize) for i in range(shnum)]
    names_header = headers[shstrndx]
    names = data[names_header[4]:names_header[4] + names_header[5]]
    sections = []
    symbol_count = 0
    for section in headers:
        nameoffset, stype, sflags, address, offset, size, link, info, align, entsize = section
        name = names[nameoffset:].split(b'\0', 1)[0].decode('ascii', 'replace')
        if stype == 2 and entsize:
            symbol_count += size // entsize
        sections.append(dict(name=name, type=stype, flags=sflags, address=hex(address), file_offset=offset, size=size))
    literals = [m.group().decode('ascii') for m in re.finditer(rb'[\x20-\x7e]{7,}', data)]
    deps = sorted(set(s for s in literals if re.search(r'(?i)(\.irx\b|DATA[/\\]|cdrom0:|\.zap\b|CDROM\.TXT)', s)))
    boot = config.read_text().strip()
    return dict(file=path.name, size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), elf_class=32, byte_order='little', machine=machine, flags=hex(flags), entry_point=hex(entry), symbol_count=symbol_count, has_debug_sections=any(s['name'].startswith('.debug') for s in sections), segments=segments, sections=sections, boot_config=boot, dependency_literals=deps, caveats=['The executable was inspected, not executed.', 'An executable does not include all game assets or IOP modules.', 'Empty symbol tables mean compiler-reported not-stripped status does not imply usable symbols.', 'Dependency strings are evidence of referenced paths, not proof every referenced file is needed at startup.'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('executable', type=Path)
    parser.add_argument('config', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = json.dumps(inspect(args.executable, args.config), indent=2)
    if args.output:
        args.output.write_text(result + '\n')
    else:
        print(result)


if __name__ == '__main__':
    main()
