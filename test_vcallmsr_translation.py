#!/usr/bin/env python3
"""Execute the actual private wrapper against a recording VU0-start boundary."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('header','before','after','work-directory','report'):
        parser.add_argument('--'+name,required=True,type=Path)
    args=parser.parse_args()
    work=args.work_directory.resolve();work.mkdir(parents=True,exist_ok=False)
    text=args.header.read_text();start=text.index('struct alignas(16) R5900Context')
    context=text[start:text.index('\n};',start)+3]
    header='''#pragma once
#include <cstdint>
#include <cstring>
#include <immintrin.h>
#include <iostream>
#include <iomanip>
'''+context+'''
class PS2Runtime {
public:
    uint32_t start=0, calls=0;
    bool delay=false;
    void vu0StartMicroProgram(uint8_t*, R5900Context* ctx,uint32_t target) {
        start=target;calls++;delay=ctx->in_delay_slot;
    }
};
'''
    (work/'ps2_runtime.h').write_text(header)
    (work/'ps2_runtime_macros.h').write_text('''#pragma once
#include "ps2_runtime.h"
#define GPR_U64(ctx,n) static_cast<uint64_t>(_mm_cvtsi128_si64((ctx)->r[n]))
#define GPR_U32(ctx,n) static_cast<uint32_t>(_mm_cvtsi128_si32((ctx)->r[n]))
#define SET_GPR_U64(ctx,n,value) ((ctx)->r[n]=_mm_set_epi64x(0,static_cast<int64_t>(value)))
''')
    for name in ('ps2_recompiled_functions.h','ps2_recompiled_stubs.h','ps2_syscalls.h','ps2_stubs.h'):
        (work/name).write_text('#pragma once\n')
    function=re.search(r'void (\w+)\(uint8_t\*',args.after.read_text())[1]
    driver='''#include "ps2_runtime.h"
#include <stdexcept>
void FUNCTION(uint8_t*,R5900Context*,PS2Runtime*);
int main() {
    uint8_t ram[16]{};
    unsigned tests=0;
    for(uint32_t index=0;index<512;index++) {
        for(uint32_t input : {index, index+512u, index|0xabcd0000u}) {
            R5900Context ctx;PS2Runtime runtime;
            for(unsigned i=0;i<16;i++) ctx.vi[i]=static_cast<uint16_t>(0x1200u+i);
            ctx.vu0_cmsar0=0xffffffffu;
            ctx.r[4]=_mm_set_epi64x(0,input);ctx.r[31]=_mm_set_epi64x(0,0x123450);
            FUNCTION(ram,&ctx,&runtime);
            if(runtime.calls!=1 || runtime.start!=8u*index || !runtime.delay ||
               ctx.pc!=0x123450u || ctx.in_delay_slot)
                throw std::runtime_error("VCALLMSR address/delay-slot/return regression");
            for(unsigned i=0;i<16;i++) if(ctx.vi[i]!=0x1200u+i)
                throw std::runtime_error("VI register modified");
            tests++;
        }
    }
    std::cout<<"PASS "<<tests<<" VCALLMSR wrapper cases\\n";
}
'''.replace('FUNCTION',function)
    (work/'driver.cpp').write_text(driver)
    results={}
    for label,source in (('before',args.before),('after',args.after)):
        cpp=work/(label+'.cpp');shutil.copy2(source,cpp)
        binary=work/label
        command=['g++','-std=c++20','-O1','-msse4.1','-fsanitize=undefined',
            '-fno-sanitize-recover=all','-I',str(work),str(cpp),str(work/'driver.cpp'),'-o',str(binary)]
        subprocess.run(command,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        run=subprocess.run([str(binary)],capture_output=True,text=True)
        results[label]={'returncode':run.returncode,'stdout':run.stdout.strip(),'stderr':run.stderr.strip()}
    assert results['before']['returncode']!=0,'Baseline unexpectedly passed'
    assert results['after']['returncode']==0,'Corrected wrapper failed'
    report={'all_passed':True,'baseline_reproduces_vi_array_bounds_failure':True,
        'corrected_actual_wrapper_cases':1536,'real_r5900_context_layout':True,
        'mocked_boundary':'Only VU0 microprogram start is recorded; no microprogram execution is tested',
        'phone_stall_fix_verified':False,'runs':results}
    args.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__': main()
