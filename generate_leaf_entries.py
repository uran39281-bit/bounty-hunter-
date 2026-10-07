#!/usr/bin/env python3
"""Generate exact native observed entries from the supplied ELF and generated code.

Read instructions from the unchanged supplied ELF. Decode supported tiny
return leaves, or expose an entry label in an existing verified generated body.
Unsupported shapes without a generated body fail. Generated game code stays local.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import re
import subprocess


def translate_leaf(address, first, delay):
    if address & 3 or first != 0x03e00008 or delay >> 26 != 9 or (delay >> 21) & 31:
        raise ValueError(f'Unsupported observed leaf at {address:#x}')
    target=(delay >> 16)&31
    value=struct.unpack('<h',struct.pack('<H',delay&0xffff))[0]
    name=f'observed_leaf_{address:08x}'
    write=f'    SET_GPR_S32(ctx, {target}, {value});\n' if target else ''
    source=f'''static void {name}(uint8_t *, R5900Context *ctx, PS2Runtime *) {{
    const uint32_t destination = static_cast<uint32_t>(_mm_cvtsi128_si32(ctx->r[31]));
{write}    ctx->pc = destination;
}}
'''
    return name,source


def expose_generated_entry(address, directory, word):
    marker=f'// {address:#x}:'
    result=subprocess.run(['rg','-l','-F',marker,'--glob','*.cpp',str(directory)],capture_output=True,text=True)
    paths=[Path(p) for p in result.stdout.splitlines()]
    if len(paths)!=1:raise ValueError('Expected one generated instruction body for observed entry')
    text=paths[0].read_text()
    # Verify its instruction comments against every original ELF instruction.
    for addr, opcode in re.findall(r'// 0x([0-9a-f]+): 0x([0-9a-f]+)',text):
        if word(int(addr,16))!=int(opcode,16):raise ValueError('Generated instruction differs from original ELF')
    match=re.search(r'void (sub_[A-Za-z0-9_]+)\(',text)
    if not match:raise ValueError('Expected a native generated function')
    name=f'observed_entry_{address:08x}'
    text=text.replace('void '+match.group(1)+'(', 'static void '+name+'(',1)
    label=f'observed_entry_label_{address:08x}'
    cases=re.findall(r'case (0x[0-9a-fA-F]+|[0-9]+)u:',text)
    if any(int(case,0)==address for case in cases):return name,text,paths[0]
    switch='    switch (ctx->pc) {'
    if text.count('    '+marker)!=1:raise ValueError('Unexpected generated instruction anchor')
    if text.count(switch)==1:
        text=text.replace(switch,switch+f'\n        case {address}u: goto {label};',1)
    elif text.count(switch)==0:
        first_pc=re.search(r'    ctx->pc = 0x[0-9a-f]+u;',text)
        if not first_pc:raise ValueError('Unexpected generated entry anchor')
        text=text[:first_pc.start()]+f'    if (ctx->pc == {address}u) goto {label};\n'+text[first_pc.start():]
    else:raise ValueError('Unexpected generated dispatch switches')
    text=text.replace('    '+marker,label+':\n    '+marker,1)
    return name,text,paths[0]


def generate(executable, addresses, output, generated_directory=None):
    data=executable.read_bytes();sha=hashlib.sha256(data).hexdigest()
    if sha!='51c56737105d1186f0b14155e39d8af67e63b12c4ac0543e1f0e178ccd6a4304':
        raise ValueError('Use the unchanged inspected SLUS_204.20')
    if data[:6]!=b'\x7fELF\x01\x01':raise ValueError('Expected 32-bit little-endian ELF')
    phoff=struct.unpack_from('<I',data,28)[0];phentsize,phnum=struct.unpack_from('<HH',data,42)
    segments=[struct.unpack_from('<8I',data,phoff+i*phentsize) for i in range(phnum)]
    def word(address):
        for kind,offset,vaddr,paddr,filesz,memsz,flags,align in segments:
            if kind==1 and vaddr<=address and address-vaddr+4<=filesz:
                return struct.unpack_from('<I',data,offset+address-vaddr)[0]
        raise ValueError('Leaf entry outside file-backed load segment')
    definitions=[];registrations=[];rows=[]
    for address in sorted(set(addresses)):
        try:
            name,source=translate_leaf(address,word(address),word(address+4))
            rows.append({'address':hex(address),'bytes':8,'shape':'JR RA; ADDIU from zero'})
        except ValueError:
            if generated_directory is None:raise
            name,source,path=expose_generated_entry(address,generated_directory,word)
            rows.append({'address':hex(address),'shape':'Existing native instruction body with exposed entry label',
                         'source_name':path.name,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        definitions.append(source)
        registrations.append(f'    if (!runtime.registerFunction({address}u, {name})) throw std::runtime_error("Leaf registration failed");\n')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text('#include "ps2_runtime.h"\n#include "ps2_runtime_macros.h"\n#include <stdexcept>\n'+''.join(definitions)+
        'void registerObservedLeafEntries(PS2Runtime &runtime) {\n'+''.join(registrations)+'}\n')
    report={'original_executable_sha256':sha,'entries':rows,
            'instructions_changed':False,'generated_native_source':str(output),'game_source_publicly_uploaded':False}
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable',type=Path)
    parser.add_argument('--entry',type=lambda s:int(s,0),action='append',required=True)
    parser.add_argument('--output',type=Path,default=Path('leaf-output/observed_leaf_entries.cpp'))
    parser.add_argument('--report',type=Path,default=Path('observed-leaf-entries.json'))
    parser.add_argument('--generated-directory',type=Path,help='Expose observed entry labels in existing native translations')
    args=parser.parse_args();report=generate(args.executable,args.entry,args.output,args.generated_directory)
    args.report.write_text(json.dumps(report,indent=2)+'\n');print(f'Generated {len(report["entries"])} exact native observed entry translation(s)')


if __name__=='__main__':main()
