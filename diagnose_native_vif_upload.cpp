// Compare an unchanged private captured VIF upload with its actual VRAM pixels.
#include "ps2_runtime.h"
#include "runtime/gs/ps2_gs_memory.h"
#include <fstream>
#include <vector>
#include <iostream>
#include <cstring>
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    std::ifstream input(argv[1],std::ios::binary);
    std::vector<uint8_t> data{std::istreambuf_iterator<char>(input),{}};
    if(data.size()<0x10500u)return 2;
    PS2Runtime r;if(!r.memory().initialize()||!r.syncCoreSubsystems())return 2;
    GSMem::InitLookupTables();r.memory().processVIF1Data(data.data(),0x10500u);
    uint32_t paletteDifferences=0,pixelDifferences=0;
    for(unsigned n=0;n<256u;++n) {
        uint32_t expected;std::memcpy(&expected,data.data()+0x80u+n*4u,4);
        paletteDifferences+=GSMem::ReadCT32(r.memory().getGSVRAM(),13440u,1u,n%16u,n/16u)!=expected;
    }
    for(unsigned n=0;n<65536u;++n)
        pixelDifferences+=GSMem::ReadP8(r.memory().getGSVRAM(),13472u,4u,n%256u,n/256u)!=data[0x500u+n];
    std::cout<<"CAPTURED_NATIVE_UPLOAD palette_differences="<<paletteDifferences
        <<" pixel_index_differences="<<pixelDifferences<<" of 65536\n";
    return paletteDifferences||pixelDifferences ? 1:0;
}
