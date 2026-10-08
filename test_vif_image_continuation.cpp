// Regress the native game's header-DIRECT, commands, then pixel-DIRECT layout.
#include "ps2_runtime.h"
#include "runtime/gs/gs_frontend.h"
#include "runtime/gs/ps2_gs_memory.h"
#include <vector>
#include <iostream>
#include <stdexcept>
#include <cstring>
using Bytes=std::vector<uint8_t>;
static void put32(Bytes &b,uint32_t v) {auto n=b.size();b.resize(n+4);std::memcpy(b.data()+n,&v,4);}
static void put64(Bytes &b,uint64_t v) {auto n=b.size();b.resize(n+8);std::memcpy(b.data()+n,&v,8);}
static void require(bool value,const char *message) {if(!value)throw std::runtime_error(message);}
static Bytes direct(const Bytes &payload,bool hl=false,bool mark=false) {
    require(payload.size()%16==0,"Unaligned fixture");Bytes b;
    put32(b,mark ? 0x07001357u:0u);put32(b,0);put32(b,0);
    put32(b,(hl ? 0x51000000u:0x50000000u)|uint32_t(payload.size()/16));
    b.insert(b.end(),payload.begin(),payload.end());return b;
}
static Bytes imageHeader(unsigned count) {
    Bytes b;put64(b,4u|(1ull<<60));put64(b,14u);
    for(auto pair: {std::pair<uint64_t,uint64_t>{(uint64_t(32u)<<32)|(1ull<<48),0x50},
        {0,0x51},{4u|(uint64_t(count)<<32),0x52},{0,0x53}}) {put64(b,pair.first);put64(b,pair.second);}
    put64(b,count|(2ull<<58));put64(b,0);return b;
}
static Bytes pixels(unsigned count) {
    Bytes b;for(unsigned n=0;n<count*4u;++n)put32(b,0x4a130100u+n*0x010203u);return b;
}
static void check(PS2Runtime &r,unsigned count) {
    for(unsigned n=0;n<count*4u;++n)
        require(GSMem::ReadCT32(r.memory().getGSVRAM(),32u,1u,n%4u,n/4u)==0x4a130100u+n*0x010203u,
            "VIFcodes were consumed as image pixels or pixel payload was lost");
}
int main() {
    try {
        GSMem::InitLookupTables();
        for(unsigned variant=0;variant<5u;++variant) {
            PS2Runtime r;require(r.memory().initialize()&&r.syncCoreSubsystems(),"Init failed");
            const unsigned count=3u;auto header=imageHeader(count),body=pixels(count);
            if(variant==4u) {
                header.insert(header.end(),body.begin(),body.end());auto all=direct(header);
                r.memory().processVIF1Data(all.data(),all.size());
            } else {
                if(variant==3u) {header.insert(header.end(),body.begin(),body.begin()+16);body.erase(body.begin(),body.begin()+16);}
                auto setup=direct(header),first=direct(body,variant==2u,true);
                if(variant==0u) {
                    setup.insert(setup.end(),first.begin(),first.end());r.memory().processVIF1Data(setup.data(),setup.size());
                } else if(variant==1u) {
                    auto chunk=direct(Bytes(body.begin(),body.begin()+16));
                    auto tail=direct(Bytes(body.begin()+16,body.end()),false,true);
                    r.memory().processVIF1Data(setup.data(),setup.size());
                    r.memory().processVIF1Data(chunk.data(),chunk.size());
                    r.memory().processVIF1Data(tail.data(),tail.size());
                } else {
                    r.memory().processVIF1Data(setup.data(),setup.size());r.memory().processVIF1Data(first.data(),first.size());
                }
                check(r,count);
                require(r.memory().vif1_regs.mark==0x1357u,"Pending IMAGE swallowed MARK command");
            }
            check(r,count);
            Bytes next;put64(next,1u|(1ull<<60));put64(next,14u);put64(next,77u|(10ull<<16));put64(next,0x4cu);
            auto wrapped=direct(next);r.memory().processVIF1Data(wrapped.data(),wrapped.size());
            require(r.gs().getDebugSnapshot().ctx[0].frame.fbp==77u,"Image continuation swallowed following register packet");
        }
        std::cout<<"PASS: one stream, separate DIRECT calls, multiple image chunks, DIRECTHL, partial initial image, full single packet, MARK and following GS register\n";
        return 0;
    } catch(const std::exception &error) {std::cerr<<"FAIL: "<<error.what()<<'\n';return 1;}
}
