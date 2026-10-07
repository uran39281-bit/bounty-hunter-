#!/usr/bin/env python3
"""Locate the stopped copy's caller and compare its arguments with original ELF bytes."""
import argparse
import json
import re
import struct
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('result', type=Path)
    parser.add_argument('--ram', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    result = json.loads(args.result.read_text())
    output = result['stdout'] + result['stderr']
    match = re.search(r'INVALID_MEMCPY_PRECOPY pc=0x([0-9a-f]+) ra=0x([0-9a-f]+) sp=0x([0-9a-f]+) dst=0x([0-9a-f]+) src=0x([0-9a-f]+) size=0x([0-9a-f]+)', output)
    if not match:
        raise ValueError('No pre-copy event in the captured diagnostic')
    event = {k:int(v,16) for k,v in zip(['pc','ra','sp','dst','src','size'],match.groups())}
    ram = args.ram.read_bytes()
    if len(ram) != 32 * 1024 * 1024:
        raise ValueError('Expected a full 32 MiB guest RAM capture')
    registers = {k:'0x'+v for k,v in re.findall(r'REG (\d+)=0x([0-9a-f]+)',output)}
    candidates = []
    for p in (root/'corrected-output').glob('*.cpp'):
        m = re.search(r'// Address: 0x([0-9a-f]+) - 0x([0-9a-f]+)',p.read_text()[:1000])
        if m and int(m[1],16) <= event['ra'] < int(m[2],16):
            candidates.append({'source':p.name,'start':'0x'+m[1],'end':'0x'+m[2]})
    original = (root/'original/SLUS_204.20').read_bytes()
    phoff = struct.unpack_from('<I',original,28)[0]
    phentsize, phnum = struct.unpack_from('<HH',original,42)
    segments = [struct.unpack_from('<8I',original,phoff+i*phentsize) for i in range(phnum)]
    def original_bytes(addr, size):
        for typ, off, va, _, filesz, _, _, _ in segments:
            if typ == 1 and va <= addr and addr + size <= va + filesz:
                return original[off+addr-va:off+addr-va+size]
        return None
    windows = []
    for name in ['ra','sp','dst','src']:
        addr = event[name]
        if addr + 64 <= len(ram):
            current = ram[addr:addr+64]
            before = original_bytes(addr,64)
            windows.append({'argument':name,'address':hex(addr),
                            'ram_words':[hex(x) for x in struct.unpack('<16I',current)],
                            'original_words':[hex(x) for x in struct.unpack('<16I',before)] if before else None})
    report = {'event':{k:hex(v) for k,v in event.items()},'registers':registers,
              'caller_candidates':candidates,'memory_windows':windows,
              'cause_isolated':False,'capture_before_upstream_clamp':True}
    args.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['registers','memory_windows']},indent=2))

if __name__ == '__main__':
    main()
