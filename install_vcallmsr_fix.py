#!/usr/bin/env python3
"""Correct VCALLMSR's CMSAR0 operand in privately generated game sources.

Semantics verified against PCSX2 COP2.cpp and PS2Recomp PR 268 (a0f89eb3).
Original ELF instructions are preserved; only their incorrect C++ operand changes.
"""
import argparse
import hashlib
import json
from pathlib import Path

OLD='uint16_t instr_index = ctx->vi[27] & 0x1FF;'
NEW='uint16_t instr_index = static_cast<uint16_t>(ctx->vu0_cmsar0 & 0x1FFu);'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args();changes=[]
    for path in sorted(args.directory.glob('*.cpp')):
        text=path.read_text()
        if OLD not in text and NEW not in text: continue
        if 'vcallmsr' not in text.lower() or 'ctx->vu0_cmsar0 = ' not in text:
            raise ValueError('Unexpected VCALLMSR wrapper: '+path.name)
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        if OLD in text:
            if text.count(OLD)!=1: raise ValueError('Unexpected repeated VCALLMSR operand')
            path.write_text(text.replace(OLD,NEW,1))
        changes.append({'file':path.name,'before_sha256':before,
            'after_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    if len(changes)!=1: raise ValueError('Expected exactly one affected generated wrapper')
    report={'operand_corrected':'CMSAR0 control register instead of vi[27]',
        'original_elf_modified':False,'changes':changes,'phone_stall_fix_verified':False,
        'references':['https://github.com/PCSX2/pcsx2/blob/master/pcsx2/COP2.cpp',
                      'https://github.com/ran-j/PS2Recomp/pull/268']}
    if args.report: args.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__': main()
