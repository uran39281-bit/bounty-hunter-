#!/usr/bin/env python3
"""Bounded, read-only metadata for the real GS draw batches."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    args = parser.parse_args()
    path = args.repo / 'ps2xRuntime/src/lib/gs/gs_frontend.cpp'
    text = path.read_text()
    if 'BOUNTY_GS_TEXTURE_TRACE' in text:
        print('GS batch metadata trace already installed')
        return
    anchor = '        GSPrimitiveBatch batch = buildDrawBatch(needed);'
    if text.count(anchor) != 1:
        raise ValueError('Unexpected GS draw-batch anchor')
    code = '''
        // BOUNTY_GS_TEXTURE_TRACE: observe the original batch without changing it.
        if (std::getenv("PS2X_BOOT_GRAPHICS_TRACE"))
        {
            static thread_local uint32_t all = 0, emitted = 0;
            static thread_local std::unordered_map<uint32_t, uint32_t> textures;
            const auto &c = batch.state.context;
            const auto &a = batch.vertices[0];
            const auto &b = batch.vertices[batch.vertexCount-1u];
            const bool big = std::abs(b.x-a.x) >= 128.0f || std::abs(b.y-a.y) >= 128.0f;
            const uint32_t key = (c.tex0.tbp0 << 6u) | c.tex0.psm;
            const bool newTexture = batch.state.prim.tme && ++textures[key] <= 3u;
            if (++all <= 16u || (newTexture && emitted++ < 96u) ||
                (big && batch.state.prim.tme && c.frame.fbp != 0u && emitted++ < 96u))
                std::cerr << "BOOT_GS_BATCH draw=" << all << " prim=" << unsigned(batch.state.prim.type)
                    << " tme=" << batch.state.prim.tme << " fst=" << batch.state.prim.fst
                    << " frame=" << c.frame.fbp << ',' << c.frame.fbw << ',' << unsigned(c.frame.psm)
                    << " texture=" << c.tex0.tbp0 << ',' << unsigned(c.tex0.tbw) << ',' << unsigned(c.tex0.psm)
                    << " dimensions=" << unsigned(c.tex0.tw) << ',' << unsigned(c.tex0.th)
                    << " clamp=0x" << std::hex << c.clamp << std::dec
                    << " xy=" << a.x << ',' << a.y << ',' << b.x << ',' << b.y
                    << " offset=" << c.xyoffset.ofx << ',' << c.xyoffset.ofy
                    << " uv=" << a.u << ',' << a.v << ',' << b.u << ',' << b.v
                    << " stq=" << a.s << ',' << a.t << ',' << a.q << ',' << b.s << ',' << b.t << ',' << b.q << '\\n';
        }'''
    for header in ['cstdlib', 'iostream', 'cmath', 'unordered_map']:
        if f'#include <{header}>' not in text:
            text = f'#include <{header}>\n' + text
    text = text.replace(anchor, anchor + code)
    transfer = '            command.direction = m_trxdir;'
    transfer_trace = r'''
            // BOUNTY_GS_UPLOAD_TRACE: native upload destination and dimensions only.
            if (std::getenv("PS2X_BOOT_GRAPHICS_TRACE"))
            {
                static thread_local uint32_t hit = 0;
                if (++hit <= 128u)
                    std::cerr << "BOOT_GS_UPLOAD hit=" << hit << " direction=" << m_trxdir
                        << " destination=" << m_bitbltbuf.dbp << ',' << unsigned(m_bitbltbuf.dbw) << ',' << unsigned(m_bitbltbuf.dpsm)
                        << " origin=" << m_trxpos.dsax << ',' << m_trxpos.dsay
                        << " size=" << m_trxreg.rrw << ',' << m_trxreg.rrh << '\n';
            }'''
    flush = '    case GS_REG_TEXFLUSH:\n'
    flush_trace = r'''        if (std::getenv("PS2X_BOOT_GRAPHICS_TRACE"))
        {
            static thread_local uint32_t hit = 0;
            if (++hit <= 256u) std::cerr << "BOOT_GS_FLUSH hit=" << hit << '\n';
        }
'''
    for item in [transfer, flush]:
        if text.count(item) != 1: raise ValueError('Unexpected GS upload trace anchor')
    text = text.replace(transfer, transfer + transfer_trace).replace(flush, flush + flush_trace)
    path.write_text(text)
    print('Installed bounded read-only GS batch metadata trace')


if __name__ == '__main__':
    main()
