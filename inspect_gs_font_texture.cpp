// Inspect original checkpoint texture contents without changing guest state.
#include "runtime/gs/ps2_gs_memory.h"
#include <fstream>
#include <vector>
#include <iostream>
#include <cstring>
static std::vector<uint8_t> read(const char *path) {
    std::ifstream input(path,std::ios::binary);
    return {std::istreambuf_iterator<char>(input),{}};
}
int main(int argc,char **argv) {
    if(argc!=4)return 2;
    auto vram=read(argv[1]),ram=read(argv[2]);
    if(vram.size()!=4194304 || ram.size()!=33554432)return 2;
    GSMem::InitLookupTables();
    const auto word=[&](unsigned a){uint32_t w;std::memcpy(&w,ram.data()+a,4);return w;};
    const auto manager=word(0x3c406cu),table=word(manager+20u),font=word(table+4u);
    const auto descriptor=word(font+36u),pixels=word(descriptor),base=word(font+56u);
    uint32_t differences=0;
    std::ofstream out(argv[3],std::ios::binary);out<<"P5\n256 256\n255\n";
    for(unsigned y=0;y<256u;++y)for(unsigned x=0;x<256u;++x) {
        const unsigned n=y*256u+x;
        const auto expected=(ram[pixels+(n>>1u)]>>((n&1u)*4u))&15u;
        const auto actual=GSMem::ReadP4(vram.data(),base,4u,x,y);
        differences+=actual!=expected;
        out.put(char(actual*17u));
    }
    std::cout<<"Font texture base="<<base<<" pixel_index_differences="<<differences<<" of 65536\n";
    return out ? 0:2;
}
