// Verify the registered original menu memory-card entry, with isolated inputs.
#include "ps2_runtime.h"
#include <iostream>
void registerObservedLeafEntries(PS2Runtime &runtime);
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    PS2Runtime runtime;
    runtime.setMissingFunctionPolicy(PS2Runtime::MissingFunctionPolicy::Stop);
    if(!runtime.memory().initialize() || !runtime.syncCoreSubsystems() || !runtime.loadELF(argv[1]))return 1;
    registerObservedLeafEntries(runtime);
    auto &ctx=runtime.cpu();
    const uint32_t object=0x1e00000u,slots=0x1e01000u,returnPc=0x101000u;
    runtime.memory().write32(object+0x18u,slots);
    bool ok=true;
    for(unsigned port=0;port<3;++port) {
        ctx={};ctx.pc=0x2df460u;
        ctx.r[4]=_mm_set_epi64x(0,object);
        ctx.r[5]=_mm_set_epi64x(0,port);
        ctx.r[31]=_mm_set_epi64x(0,returnPc);
        auto function=runtime.lookupFunction(ctx.pc);
        if(!function)return 1;
        function(runtime.memory().getRDRAM(),&ctx,&runtime);
        const uint32_t actual=static_cast<uint32_t>(_mm_cvtsi128_si32(ctx.r[2]));
        const uint32_t expected=port<2?slots+port*0x500u:0u;
        bool pass=actual==expected && ctx.pc==returnPc && !runtime.isStopRequested();
        ok &= pass;
        std::cout << "NATIVE_MENU_ENTRY port=" << port << " result=0x" << std::hex << actual << " expected=0x" << expected << std::dec << " pass=" << pass << '\n';
    }
    for(unsigned flags=0;flags<4;++flags) {
        runtime.memory().write8(object+0x4du,flags&1u);
        runtime.memory().write8(object+0x4eu,(flags>>1u)&1u);
        runtime.memory().write8(object+8u,0xa5u);
        ctx={};ctx.pc=0x3265d0u;
        ctx.r[4]=_mm_set_epi64x(0,object);
        ctx.r[5]=_mm_set_epi64x(0,1u);
        ctx.r[31]=_mm_set_epi64x(0,returnPc);
        auto function=runtime.lookupFunction(ctx.pc);
        if(!function)return 1;
        function(runtime.memory().getRDRAM(),&ctx,&runtime);
        const unsigned result=static_cast<unsigned>(_mm_cvtsi128_si32(ctx.r[2]));
        const unsigned enabled=runtime.memory().read8(object+8u);
        const bool pass=result==(flags?1u:0u) && enabled==(flags?1u:0xa5u) && ctx.pc==returnPc && !runtime.isStopRequested();
        ok &= pass;
        std::cout << "NATIVE_MENU_CALLBACK flags=" << flags << " result=" << result << " enabled=" << enabled << " pass=" << pass << '\n';
    }
    std::cout << (ok?"PASS":"FAIL") << " original menu entries\n";
    return ok?0:1;
}
