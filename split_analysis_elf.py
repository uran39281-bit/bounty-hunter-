#!/usr/bin/env python3
"""Add inferred code/data/BSS section metadata to a COPY of this specific ELF.

The boundary is an experimental hypothesis, not an authoritative function map.
Program headers and loaded bytes are preserved exactly. Never replaces input.
"""
import argparse
import struct
from pathlib import Path


def split(source: Path, destination: Path, code_end: int, constructors_only=False, include_constructors=False):
    if source.resolve() == destination.resolve():
        raise ValueError('Output must differ from input')
    original = source.read_bytes()
    data = bytearray(original)
    h = list(struct.unpack_from('<HHIIIIIHHHHHH', data, 16))
    if data[:7] != b'\x7fELF\x01\x01\x01' or h[1] != 8:
        raise ValueError('Expected little-endian MIPS ELF32')
    phoff, shoff, phsize, phnum, shsize, shnum = h[4], h[5], h[8], h[9], h[10], h[11]
    old_sections = [list(struct.unpack_from('<IIIIIIIIII', data, shoff+i*shsize)) for i in range(shnum)]
    candidates = [s for s in old_sections if s[1] == 1 and s[2] & 4 and s[5] > 0]
    if len(candidates) != 1:
        raise ValueError('Expected exactly one merged executable section')
    text = candidates[0]
    code_start, file_start, merged_size = text[3], text[4], text[5]
    data_end = code_start + merged_size
    if not code_start < code_end < data_end or code_end % 16:
        raise ValueError('Invalid boundary')
    load = next(struct.unpack_from('<IIIIIIII', data, phoff+i*phsize) for i in range(phnum) if struct.unpack_from('<IIIIIIII', data, phoff+i*phsize)[2] == code_start)
    names = b'\0.shstrtab\0.text\0.rodata\0.bss\0.scratchpad\0.comment\0.reginfo\0.rodata.before_ctors\0.text.ctors\0.rodata.after_ctors\0'
    name_offset = lambda name: names.index(name.encode() + b'\0')
    new = [[0]*10]
    # String table offset is assigned after appending its bytes.
    new.append([name_offset('.shstrtab'),3,0,0,0,len(names),0,0,1,0])
    if constructors_only or include_constructors:
        # Native startup's constructor walk was observed using this exact
        # pointer-table range. This island was excluded by the first split.
        ctor_start, ctor_end = 0x3a6be0, 0x3b5b50
        pointers = struct.unpack_from('<114I', original, file_start + ctor_end - code_start)
        assert min(pointers) == ctor_start and max(pointers) == 0x3b5b00
        assert all(ctor_start <= p < ctor_end and p % 16 == 0 for p in pointers)
        # Constructor-only translation needs an entry inside that section.
        # This metadata copy is never booted; actual startup still uses the
        # original executable's entry 0x100008.
        if constructors_only:
            h[3] = ctor_start
            before = [('.rodata.before_ctors',3,code_start,ctor_start)]
        else:
            before = [('.text',6,code_start,code_end),
                      ('.rodata.before_ctors',3,code_end,ctor_start)]
        for name, flags, begin, end in before + [
                ('.text.ctors',6,ctor_start,ctor_end),
                ('.rodata.after_ctors',3,ctor_end,data_end)]:
            new.append([name_offset(name),1,flags,begin,file_start+begin-code_start,end-begin,0,0,16,0])
    else:
        new.append([name_offset('.text'),1,6,code_start,file_start,code_end-code_start,0,0,128,0])
        new.append([name_offset('.rodata'),1,3,code_end,file_start+code_end-code_start,data_end-code_end,0,0,16,0])
    new.append([name_offset('.bss'),8,3,data_end,file_start+merged_size,load[5]-load[4],0,0,16,0])
    for old in old_sections:
        if old[3] == 0x70000000 and old[5]:
            old[0] = name_offset('.scratchpad')
            new.append(old)
        elif old[1] in (0x70000006,) or (old[1] == 1 and not old[2] and old[5]):
            old[0] = name_offset('.reginfo' if old[1] == 0x70000006 else '.comment')
            new.append(old)
    new[1][4] = len(data)
    data.extend(names)
    data.extend(b'\0' * (-len(data) % 4))
    h[5], h[11], h[12] = len(data), len(new), 1
    for s in new:
        data.extend(struct.pack('<IIIIIIIIII', *s))
    struct.pack_into('<HHIIIIIHHHHHH', data, 16, *h)
    for i in range(phnum):
        p = struct.unpack_from('<IIIIIIII', original, phoff+i*phsize)
        assert data[p[1]:p[1]+p[4]] == original[p[1]:p[1]+p[4]]
    assert data[phoff:phoff+phnum*phsize] == original[phoff:phoff+phnum*phsize]
    destination.write_bytes(data)
    print(f'Analysis-only ELF written; constructors_only={constructors_only}; inferred main code end={code_end:#x}; all loaded payloads preserved')


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('source',type=Path)
    p.add_argument('destination',type=Path)
    p.add_argument('--code-end',type=lambda s:int(s,0),default=0x359880)
    p.add_argument('--constructors-only',action='store_true')
    p.add_argument('--include-constructors',action='store_true')
    a=p.parse_args()
    split(a.source,a.destination,a.code_end,a.constructors_only,a.include_constructors)
