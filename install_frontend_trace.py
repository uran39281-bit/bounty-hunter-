#!/usr/bin/env python3
"""Install opt-in, bounded observations of the original front end and pad calls."""
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    path = parser.parse_args().repo / 'ps2xRuntime/src/lib/ps2_runtime.cpp'
    text = path.read_text()
    if 'BOUNTY_FRONTEND_TRACE' in text:
        start=text.index('    // BOUNTY_FRONTEND_TRACE')
        end=text.index('    // BOUNTY_BOOT_GRAPHICS_TRACE',start)
        text=text[:start]+text[end:]
    anchor = '    ctx->pc = targetPc;\n    // BOUNTY_BOOT_GRAPHICS_TRACE'
    addition = r'''    ctx->pc = targetPc;
    // BOUNTY_FRONTEND_TRACE: observe original calls; no guest-state changes.
    if (std::getenv("PS2X_FRONTEND_TRACE") &&
        (sourcePc == 0x2a5ab0u || sourcePc == 0x2a5ae0u || sourcePc == 0x2a5b50u ||
         sourcePc == 0x3113c0u || sourcePc == 0x311400u ||
         (sourcePc >= 0x31bf00u && sourcePc < 0x31c540u) ||
         sourcePc == 0x312c50u || targetPc == 0x33fd00u ||
         (sourcePc >= 0x31bbb0u && sourcePc < 0x31bf00u) ||
         targetPc == 0x323840u || targetPc == 0x1d9420u ||
         targetPc == 0x1da1e0u || targetPc == 0x1b9b70u ||
         (sourcePc >= 0x301aa0u && sourcePc < 0x301f00u) ||
         targetPc == 0x31f280u || targetPc == 0x31ec00u ||
         targetPc == 0x1baf70u || targetPc == 0x199290u ||
         targetPc == 0x199310u || targetPc == 0x198f40u))
    {
        static thread_local std::unordered_map<uint32_t, uint32_t> hits;
        const uint32_t hit = ++hits[sourcePc];
        if (hit <= 3u || hit == 64u || hit == 128u || hit == 256u || hit == 512u)
        {
            const uint32_t gp = static_cast<uint32_t>(_mm_cvtsi128_si32(ctx->r[28]));
            auto word = [&](uint32_t a) { return (a & 3u)==0u && a <= PS2_RAM_SIZE - 4u ? m_memory.read32(a) : 0u; };
            const uint32_t front = word(gp-0x3b18u);
            const uint32_t object=word(front+4u);
            const uint32_t a1=static_cast<uint32_t>(_mm_cvtsi128_si32(ctx->r[5]));
            std::cerr << "FRONTEND_CALL target=0x" << std::hex << targetPc
                      << " source=0x" << sourcePc << " a0=0x"
                      << static_cast<uint32_t>(_mm_cvtsi128_si32(ctx->r[4]))
                      << " a1=0x" << a1 << " event=0x" << word(a1+4u)
                      << " front=0x" << front << " object=0x" << object
                      << " menu_id=0x" << word(word(object+0x18u)+4u)
                      << " logical_buttons=0x" << word(0x3f0634u)
                      << " elapsed_bits=0x" << word(gp-0x3ae8u)
                      << " pending_screen=0x" << word(object+0x58u)
                      << " timer_start=0x" << word(object+0x108u)
                      << " count=0x" << ctx->cop0_count
                      << std::dec << " state=" << unsigned(m_memory.read8(gp-0x6650u))
                      << " mode=" << unsigned(m_memory.read8(gp-0x3b00u))
                      << " timer_active=" << unsigned(m_memory.read8(object+0x121u))
                      << " delta=" << ctx->f[12] << " hit=" << hit << '\n';
        }
    }
    // BOUNTY_BOOT_GRAPHICS_TRACE'''
    if text.count(anchor) != 1: raise ValueError('Unexpected branch trace anchor')
    path.write_text(text.replace(anchor, addition))
    text=path.read_text()
    return_anchor='    targetFn(rdram, ctx, this);\n'
    return_trace=r'''    targetFn(rdram, ctx, this);
    // BOUNTY_TITLE_RETURN_TRACE: observe timer/conversion/update results only.
    if (std::getenv("PS2X_FRONTEND_TRACE") &&
        ((sourcePc >= 0x31bf00u && sourcePc < 0x31c540u) ||
         sourcePc == 0x3318a8u || sourcePc == 0x312c50u ||
         sourcePc == 0x1d9960u ||
         (sourcePc >= 0x301aa0u && sourcePc < 0x301f00u)))
    {
        static thread_local std::unordered_map<uint32_t,uint32_t> returns;
        const uint32_t hit=++returns[sourcePc];
        if (hit<=3u || hit==64u || hit==128u || hit==256u || hit==512u || hit==1024u)
            std::cerr << "TITLE_RETURN source=0x" << std::hex << sourcePc
                      << " target=0x" << targetPc << " pc=0x" << ctx->pc
                      << " v0=0x" << static_cast<uint64_t>(_mm_cvtsi128_si64(ctx->r[2]))
                      << " count=0x" << ctx->cop0_count << std::dec
                      << " f0=" << ctx->f[0] << " hit=" << hit << '\n';
    }
    // BOUNTY_TITLE_RETURN_TRACE_END
'''
    if 'BOUNTY_TITLE_RETURN_TRACE:' in text:
        start=text.index('    // BOUNTY_TITLE_RETURN_TRACE:')
        end=text.index('    // BOUNTY_TITLE_RETURN_TRACE_END',start)+len('    // BOUNTY_TITLE_RETURN_TRACE_END\n')
        text=text[:start]+text[end:]
    if text.count(return_anchor)!=1: raise ValueError('Unexpected return trace anchor')
    path.write_text(text.replace(return_anchor,return_trace))
    print('Installed bounded front-end trace')

if __name__ == '__main__': main()
