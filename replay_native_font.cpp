// Private captured-packet diagnostic. This does not replace the game's drawing.
#include "ps2_runtime.h"
#include "runtime/gs/gs_frontend.h"
#include "runtime/gs/ps2_gs_memory.h"
#include <fstream>
#include <iostream>
#include <vector>
#include <cstring>
static std::vector<uint8_t> read(const char *path) {
    std::ifstream file(path,std::ios::binary);
    return {std::istreambuf_iterator<char>(file),{}};
}
int main(int argc,char **argv) {
    if(argc!=4 && argc!=5)return 2;
    auto ram=read(argv[1]),tga=read(argv[2]);
    if(ram.size()!=PS2_RAM_SIZE || tga.size()!=32850)return 2;
    PS2Runtime runtime;
    if(!runtime.memory().initialize() || !runtime.syncCoreSubsystems())return 1;
    auto &gs=runtime.gs();
    gs.writeRegister(0x4c,140u | (uint64_t(10u)<<16u));
    gs.writeRegister(0x18,27648u | (uint64_t(29184u)<<32u));
    gs.writeRegister(0x40,(uint64_t(639u)<<16u) | (uint64_t(447u)<<48u));
    gs.writeRegister(0x1a,1u);
    std::vector<uint8_t> palette(16u*16u*4u,0);
    for(unsigned n=0;n<16u;++n) {
        palette[n*4u]=tga[18u+n*4u+2u];
        palette[n*4u+1u]=tga[18u+n*4u+1u];
        palette[n*4u+2u]=tga[18u+n*4u];
        palette[n*4u+3u]=tga[18u+n*4u+3u]/2u;
    }
    gs.uploadImageNative((uint64_t(13440u)<<32u)|(uint64_t(1u)<<48u),0,
        16u|(uint64_t(16u)<<32u),0,palette.data(),palette.size());
    gs.uploadImageNative((uint64_t(13472u)<<32u)|(uint64_t(4u)<<48u)|(uint64_t(20u)<<56u),0,
        256u|(uint64_t(256u)<<32u),0,tga.data()+82u,32768u);
    if(argc==5) {
        runtime.memory().processVIF1Data(ram.data()+0x7f4700u,112u);
        runtime.memory().processVIF1Data(ram.data()+0x7f4780u,3536u);
    } else {
        gs.processGIFPacket(ram.data()+0x7f4710u,96u);
        gs.processGIFPacket(ram.data()+0x7f4790u,3520u);
    }
    auto *vram=runtime.memory().getGSVRAM();
    std::ofstream out(argv[3],std::ios::binary);out<<"P6\n640 448\n255\n";
    for(unsigned y=0;y<448u;++y)for(unsigned x=0;x<640u;++x) {
        const auto pixel=GSMem::ReadCT32(vram,4480u,10u,x,y);
        const char rgb[]={char(pixel),char(pixel>>8u),char(pixel>>16u)};
        out.write(rgb,3);
    }
    std::cout<<"Replayed captured font packet; fixture only, not a native integration pass\n";
    return out ? 0:2;
}
