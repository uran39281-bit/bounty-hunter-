#!/usr/bin/env python3
"""Check native leaf semantics with synthetic instructions, including delay-slot RA."""
import argparse
from pathlib import Path
import subprocess
import tempfile
from generate_leaf_entries import translate_leaf


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('repo',type=Path)
    args=parser.parse_args();repo=args.repo.resolve()
    cases=[(0x101000,0x2402ffef),(0x101010,0x241f0055),(0x101020,0x24000007)]
    generated=[translate_leaf(a,0x03e00008,d) for a,d in cases]
    for first,delay in [(0,0x24020001),(0x03e00008,0x24220001),(0x03e00008,0)]:
        try:translate_leaf(0x101000,first,delay)
        except ValueError:pass
        else:raise AssertionError('Unsupported shape accepted')
    source='#include "ps2_runtime.h"\n#include "ps2_runtime_macros.h"\n#include <iostream>\n'+''.join(s for name,s in generated)+'''
int main(){
 R5900Context ctx{};
 ctx.r[31]=_mm_set_epi64x(0,0x123456u);
 ctx.r[2]=_mm_set_epi64x(0x1122334455667788ull,0);
 observed_leaf_00101000(nullptr,&ctx,nullptr);
 if (ctx.pc!=0x123456u || _mm_extract_epi64(ctx.r[2],0)!=-17 ||
     static_cast<uint64_t>(_mm_extract_epi64(ctx.r[2],1))!=0x1122334455667788ull) return 1;
 ctx.r[31]=_mm_set_epi64x(0,0xabcdefu);
 observed_leaf_00101010(nullptr,&ctx,nullptr);
 if (ctx.pc!=0xabcdefu || _mm_cvtsi128_si32(ctx.r[31])!=0x55) return 1;
 observed_leaf_00101020(nullptr,&ctx,nullptr);
 if (_mm_cvtsi128_si32(ctx.r[0])!=0) return 1;
 std::cout<<"PASS: native sign extension, upper-register preservation, JR-before-delay-slot RA, zero register, unsupported-shape rejection\\n";
}
'''
    with tempfile.TemporaryDirectory(prefix='bounty-leaf-test-') as tmp:
        path=Path(tmp);(path/'test.cpp').write_text(source)
        subprocess.run(['g++','-std=c++20','-msse4.1','-mavx2','-I',str(repo/'ps2xRuntime/include'),'-I',str(repo/'ps2xIOP/include'),str(path/'test.cpp'),'-o',str(path/'test')],check=True)
        subprocess.run([str(path/'test')],check=True)


if __name__=='__main__':main()
