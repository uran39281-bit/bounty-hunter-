#!/usr/bin/env python3
"""Latch a real host frame after the game's complete native GS display copy."""
import argparse
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo',type=Path)
    args=parser.parse_args()
    path=args.repo/'ps2xRuntime/src/lib/gs/gs_frontend.cpp'
    text=path.read_text()
    if 'BOUNTY_DISPLAY_COPY_CAPTURE' not in text:
        anchor='        m_backend->Submit(batch);'
        assert text.count(anchor)==1
        addition='''
        // BOUNTY_DISPLAY_COPY_CAPTURE: observe all 20 native display-copy strips.
        // No guest state, VBlank, draw packet or rendered pixel is supplied here.
        if (std::getenv("PS2X_CAPTURE_ON_PRESENT"))
        {
            static thread_local uint32_t nextX=0, completed=0;
            const auto &c=batch.state.context;
            const auto &a=batch.vertices[0];
            const auto &b=batch.vertices[batch.vertexCount-1u];
            const float x0=a.x-float(c.xyoffset.ofx)/16.0f;
            const float x1=b.x-float(c.xyoffset.ofx)/16.0f;
            const float y0=a.y-float(c.xyoffset.ofy)/16.0f;
            const float y1=b.y-float(c.xyoffset.ofy)/16.0f;
            const bool strip=batch.vertexCount==2u && batch.state.prim.type==6u &&
                batch.state.prim.tme && batch.state.prim.fst &&
                c.frame.fbp==0u && c.frame.fbw==10u && c.frame.psm==0u &&
                c.tex0.tbp0==4480u && c.tex0.tbw==10u && c.tex0.psm==0u &&
                x1-x0==32.0f && y0==0.0f && y1==448.0f &&
                float(a.u)==x0*16.0f && float(b.u)==x1*16.0f && a.v==0u && b.v==7168u;
            if (strip && x0==0.0f) nextX=0u;
            if (strip && x0==float(nextX))
            {
                nextX+=32u;
                if (nextX==640u)
                {
                    latchHostPresentationFrame();
                    nextX=0u;
                    if (++completed<=3u || completed%32u==0u)
                        std::cerr << "BOOT_DISPLAY_COPY completed=" << completed << '\\n';
                }
            }
            else nextX=0u;
        }'''
        path.write_text(text.replace(anchor,anchor+addition))
    print('Installed opt-in host latch after complete native GS display-copy strips')

if __name__=='__main__':main()
