#!/usr/bin/env python3
"""Validate and optionally extract a ROMDIR-based IOP image without execution."""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path


def inspect(source, destination=None):
    blob=source.read_bytes()
    entries=[]
    position=offset=0
    while position+16<=len(blob):
        namebytes,extsize,size=struct.unpack_from('<10sHI',blob,position)
        name=namebytes.split(b'\0',1)[0].decode('ascii')
        if not name:
            break
        if not re.fullmatch(r'[A-Z0-9_]+',name):
            raise ValueError('Invalid ROMDIR entry name')
        if offset+size>len(blob):
            raise ValueError('ROMDIR entry exceeds image size')
        payload=blob[offset:offset+size]
        entry=dict(name=name,offset=offset,size_bytes=size,extended_info_size=extsize,sha256=hashlib.sha256(payload).hexdigest())
        if payload.startswith(b'\x7fELF'):
            if len(payload)<52 or payload[4:7]!=b'\x01\x01\x01':
                raise ValueError('Invalid embedded ELF header')
            kind,machine,version,elf_entry,phoff,shoff,flags,ehsize,phsize,phnum,shsize,shnum,shstrings=struct.unpack_from('<HHIIIIIHHHHHH',payload,16)
            if machine!=8:
                raise ValueError('Embedded ELF is not MIPS')
            if (phnum and phoff+phnum*phsize>size) or (shnum and shoff+shnum*shsize>size):
                raise ValueError('Embedded ELF table exceeds module size')
            entry['elf']=dict(bits=32,byte_order='little',type=hex(kind),machine=machine,entry=hex(elf_entry),flags=hex(flags),program_headers=phnum,sections=shnum)
            if destination:
                destination.mkdir(parents=True,exist_ok=True)
                (destination/(name+'.irx')).write_bytes(payload)
        entries.append(entry)
        offset=(offset+size+15)&~15
        position+=16
    else:
        raise ValueError('ROMDIR terminator missing')
    if len(entries)<3 or [e['name'] for e in entries[:3]]!=['RESET','ROMDIR','EXTINFO']:
        raise ValueError('Unexpected ROMDIR layout')
    if entries[1]['size_bytes']!=position+16:
        raise ValueError('ROMDIR table size does not match entries')
    return dict(file=source.name,size_bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest(),entry_count=len(entries),elf_module_count=sum('elf' in e for e in entries),modules=entries,validation='ROMDIR ranges and embedded ELF headers/tables validated; no module was executed')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('image',type=Path)
    parser.add_argument('--extract-to',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result=json.dumps(inspect(args.image,args.extract_to),indent=2)+'\n'
    if args.output:args.output.write_text(result)
    else:print(result,end='')
