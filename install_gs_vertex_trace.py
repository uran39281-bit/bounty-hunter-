#!/usr/bin/env python3
"""Opt-in bounded metadata for every vertex in original GS batches."""
import argparse
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo',type=Path)
    args=parser.parse_args()
    path=args.repo/'ps2xRuntime/src/lib/gs/gs_frontend.cpp'
    source=path.read_text()
    if 'BOUNTY_GS_VERTEX_TRACE' in source:
        print('GS vertex trace already installed');return
    anchor='        updatePreferredDisplaySourceForDraw(batch);'
    if source.count(anchor)!=1:raise ValueError('Unexpected batch trace anchor')
    code=r'''        // BOUNTY_GS_VERTEX_TRACE: inspect original packet output; do not edit it.
        if (std::getenv("PS2X_GS_VERTEX_TRACE"))
        {
            static thread_local std::unordered_map<uint64_t,uint32_t> hits;
            static thread_local uint32_t emitted=0;
            const auto &c=batch.state.context;
            const uint64_t key=(uint64_t(c.tex0.tbp0)<<16u) |
                (uint64_t(c.tex0.psm)<<8u) | unsigned(batch.state.prim.type);
            if (batch.state.prim.tme && ++hits[key]<=32u && emitted++<1024u)
            {
                std::cerr << "GS_VERTEX_BATCH texture=" << c.tex0.tbp0 << ','
                    << unsigned(c.tex0.psm) << " prim=" << unsigned(batch.state.prim.type)
                    << " fst=" << batch.state.prim.fst << " frame=" << c.frame.fbp
                    << " size=" << batch.state.textureWidth << ',' << batch.state.textureHeight
                    << " offset=" << c.xyoffset.ofx << ',' << c.xyoffset.ofy
                    << " test=0x" << std::hex << c.test << " alpha=0x" << c.alpha
                    << " mask=0x" << c.frame.fbmsk << std::dec;
                for (uint32_t n=0;n<batch.vertexCount;++n)
                {
                    const auto &v=batch.vertices[n];
                    std::cerr << " vertex" << n << '=' << v.x << ',' << v.y << ',' << v.z
                        << '/' << v.s << ',' << v.t << ',' << v.q
                        << '/' << v.u << ',' << v.v
                        << '/' << unsigned(v.r) << ',' << unsigned(v.g) << ','
                        << unsigned(v.b) << ',' << unsigned(v.a);
                }
                std::cerr << '\n';
            }
        }
'''
    for header in ['cstdlib','iostream','unordered_map']:
        if f'#include <{header}>' not in source:source=f'#include <{header}>\n'+source
    path.write_text(source.replace(anchor,code+anchor))
    print('Installed bounded original GS vertex metadata trace')

if __name__=='__main__':main()
