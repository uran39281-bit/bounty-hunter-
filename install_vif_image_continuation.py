#!/usr/bin/env python3
"""Keep VIF commands outside pending GIF IMAGE payloads."""
import argparse
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo',type=Path)
    args=parser.parse_args()
    path=args.repo/'ps2xRuntime/src/lib/ps2_vif1_interpreter.cpp'
    text=path.read_text()
    if 'BOUNTY_VIF_IMAGE_DIRECT_BOUNDARY' in text:
        print('VIF IMAGE/DIRECT boundary fix already installed');return
    start=text.index('        if (m_vif1PendingPath2ImageQwc != 0u)',text.index('void PS2Memory::processVIF1Data(const uint8_t'))
    end=text.index('        uint32_t cmd;',start)
    text=text[:start]+text[end:]
    start=text.index('            if (qwCount > 0)',text.index('else if (opcode == VIF_DIRECT || opcode == VIF_DIRECTHL)'))
    end=text.index('            pos += qwCount * 16;',start)
    code=r'''            // BOUNTY_VIF_IMAGE_DIRECT_BOUNDARY: a pending GIF IMAGE consumes
            // only DIRECT payload bytes. NOP/DIRECT VIFcodes remain commands.
            if (qwCount > 0)
            {
                const bool directHl = (opcode == VIF_DIRECTHL);
                uint32_t consumedQw = 0u;
                if (m_vif1PendingPath2ImageQwc != 0u)
                {
                    consumedQw = std::min<uint32_t>(m_vif1PendingPath2ImageQwc,qwCount);
                    std::vector<uint8_t> imagePacket(16u+size_t(consumedQw)*16u,0u);
                    const uint64_t imageTag = uint64_t(consumedQw) |
                        ((consumedQw==m_vif1PendingPath2ImageQwc) ? (1ull<<15) : 0ull) |
                        (uint64_t(kGifFmtImage)<<58);
                    std::memcpy(imagePacket.data(),&imageTag,sizeof(imageTag));
                    std::memcpy(imagePacket.data()+16u,data+pos,size_t(consumedQw)*16u);
                    submitGifPacket(GifPathId::Path2,imagePacket.data(),uint32_t(imagePacket.size()),true,directHl);
                    m_vif1PendingPath2ImageQwc -= consumedQw;
                    if (m_vif1PendingPath2ImageQwc==0u) m_vif1PendingPath2DirectHl=false;
                }
                if (consumedQw < qwCount)
                {
                    const uint8_t *remaining = data+pos+consumedQw*16u;
                    const uint32_t remainingBytes = (qwCount-consumedQw)*16u;
                    submitGifPacket(GifPathId::Path2,remaining,remainingBytes,true,directHl);
                    m_vif1PendingPath2ImageQwc = pendingGifImageQwc(remaining,remainingBytes);
                    m_vif1PendingPath2DirectHl = m_vif1PendingPath2ImageQwc!=0u && directHl;
                }
            }

'''
    path.write_text(text[:start]+code+text[end:])
    print('Installed VIF IMAGE continuation within explicit DIRECT payloads')

if __name__=='__main__':main()
