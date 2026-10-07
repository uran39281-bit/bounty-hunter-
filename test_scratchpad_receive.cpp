// Verify actual scratchpad data, wrapping, DMA register updates and rejected input.
#include "ps2_runtime.h"
#include "Kernel/Stubs/DMA.h"
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <cstring>

void require(bool ok, const char *message) {
    if (!ok) throw std::runtime_error(message);
}
void setreg(R5900Context &ctx, int index, uint32_t value) {
    ctx.r[index] = _mm_set_epi64x(0, value);
}
int main() {
    PS2Runtime runtime;
    require(runtime.memory().initialize(), "RAM init failed");
    auto &memory = runtime.memory();
    auto *ram = memory.getRDRAM();
    auto *spr = memory.getScratchpad();
    for (uint32_t i=0; i<16384; ++i) spr[i] = static_cast<uint8_t>((i*17u + i/256u) & 255u);
    setenv("PS2X_SPR_RECVN", "1", 1);
    R5900Context ctx{};
    setreg(ctx,4,0x1000d000u);setreg(ctx,5,0x00400000u);setreg(ctx,6,0x400u);
    memory.writeIORegister(0x1000d080u, 0x3ff0u);
    ps2_stubs::sceDmaRecvN(ram,&ctx,&runtime);
    require(_mm_cvtsi128_si32(ctx.r[2]) == 0, "receive failed");
    for (uint32_t i=0; i<16384; ++i)
        require(ram[0x400000u+i] == spr[(0x3ff0u+i)&0x3fffu], "scratchpad data or wrapping wrong");
    require(memory.readIORegister(0x1000d010u) == 0x404000u, "MADR not advanced");
    require(memory.readIORegister(0x1000d020u) == 0, "QWC not cleared");
    require(memory.readIORegister(0x1000d080u) == 0x3ff0u, "SADR wrap wrong");
    require((memory.readIORegister(0x1000d000u)&0x100u)==0, "STR not cleared");
    const auto causes = memory.consumeCompletedDmacCauses();
    require(causes.size()==1 && causes[0]==8u, "SPR completion cause missing");
    setreg(ctx,5,PS2_RAM_SIZE-16u);setreg(ctx,6,2u);
    ps2_stubs::sceDmaRecvN(ram,&ctx,&runtime);
    require(_mm_cvtsi128_si32(ctx.r[2]) == -1, "invalid range accepted");
    require(memory.consumeCompletedDmacCauses().empty(), "invalid request completed DMA");
    setreg(ctx,5,0x400000u);setreg(ctx,6,0x10000u);
    ps2_stubs::sceDmaRecvN(ram,&ctx,&runtime);
    require(_mm_cvtsi128_si32(ctx.r[2]) == -1, "oversize QWC accepted");
    std::cout << "PASS: real 16KB SPR copy, wrap, MADR/QWC/SADR/STR, completion IRQ, invalid-range and oversize rejection\n";
}
