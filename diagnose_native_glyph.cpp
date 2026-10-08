// Isolated investigation using a private RAM checkpoint and unchanged game code.
#include "ps2_runtime.h"
#include <fstream>
#include <iostream>
#include <cstring>
int main(int argc,char **argv) {
    if(argc!=3 && argc!=4)return 2;
    PS2Runtime runtime;
    runtime.setMissingFunctionPolicy(PS2Runtime::MissingFunctionPolicy::Stop);
    if(!runtime.memory().initialize() || !runtime.syncCoreSubsystems() || !runtime.loadELF(argv[1]))return 1;
    auto *ram=runtime.memory().getRDRAM();
    std::ifstream input(argv[2],std::ios::binary);
    input.read(reinterpret_cast<char *>(ram),PS2_RAM_SIZE);
    if(input.gcount()!=PS2_RAM_SIZE)return 2;
    auto &ctx=runtime.cpu();
    ctx={};ctx.pc=0x1d93a0u;
    ctx.r[4]=_mm_set_epi64x(0,0x3cf324u);
    ctx.r[31]=_mm_set_epi64x(0,0x101000u);
    ctx.f[12]=ctx.f[13]=0.6f;
    runtime.lookupFunction(ctx.pc)(ram,&ctx,&runtime);
    for(unsigned ch: {65u,97u,169u}) {
        ctx={};ctx.pc=0x1da1e0u;
        ctx.r[28]=_mm_set_epi64x(0,0x3c79f0u);
        ctx.r[29]=_mm_set_epi64x(0,PS2_RAM_SIZE-0x100u);
        ctx.r[31]=_mm_set_epi64x(0,0x101000u);
        ctx.r[4]=_mm_set_epi64x(0,0x3cf324u);
        ctx.r[5]=_mm_set_epi64x(0,ch);
        ctx.r[6]=_mm_set_epi64x(0,200u);
        ctx.r[7]=_mm_set_epi64x(0,339u);
        ctx.r[8]=_mm_set_epi64x(0,0x1e00000u);
        runtime.lookupFunction(ctx.pc)(ram,&ctx,&runtime);
        std::cout << "GLYPH char=" << ch << " pc=0x" << std::hex << ctx.pc << std::dec << " advance=" << ctx.f[0] << " stop=" << runtime.isStopRequested() << '\n';
    }
    ctx={};ctx.pc=0x1d9420u;
    ctx.r[28]=_mm_set_epi64x(0,0x3c79f0u);
    ctx.r[29]=_mm_set_epi64x(0,PS2_RAM_SIZE-0x100u);
    ctx.r[31]=_mm_set_epi64x(0,0x101000u);
    ctx.r[4]=_mm_set_epi64x(0,0x3cf324u);
    ctx.r[5]=_mm_set_epi64x(0,322u);
    ctx.r[6]=_mm_set_epi64x(0,339u);
    ctx.r[7]=_mm_set_epi64x(0,0x5d01c0u);
    ctx.r[9]=_mm_set_epi64x(0,-1);
    runtime.lookupFunction(ctx.pc)(ram,&ctx,&runtime);
    std::cout << "STRING pc=0x" << std::hex << ctx.pc << std::dec << " width=" << _mm_cvtsi128_si32(ctx.r[2]) << " stop=" << runtime.isStopRequested() << '\n';
    for(uint32_t address: {0x452798u,0x4527a0u,0x4527acu,0x454918u,0x45491cu}) {
        uint32_t value;std::memcpy(&value,ram+address,4);
        std::cout << "PACKET_GLOBAL address=0x" << std::hex << address << " value=0x" << value << std::dec << '\n';
    }
    if(argc==4) {
        std::ofstream dump(argv[3],std::ios::binary);
        dump.write(reinterpret_cast<const char *>(ram),PS2_RAM_SIZE);
        if(!dump)return 2;
    }
}
