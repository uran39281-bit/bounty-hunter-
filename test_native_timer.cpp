// Diagnostic of the unchanged native timer and integer-to-float routines.
#include "ps2_runtime.h"
#include "runtime/ee_scheduler.h"
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <stdexcept>

int main(int argc,char **argv) {
    if(argc!=2)return 2;
    PS2Runtime runtime;
    runtime.setMissingFunctionPolicy(PS2Runtime::MissingFunctionPolicy::Stop);
    if(!runtime.memory().initialize() || !runtime.syncCoreSubsystems() || !runtime.loadELF(argv[1]))return 1;
    auto &ctx=runtime.cpu();
    ctx.r[28]=_mm_set_epi64x(0,0x3c79f0u);
    ctx.r[29]=_mm_set_epi64x(0,PS2_RAM_SIZE-0x100u);
    auto invoke=[&](uint32_t pc,uint64_t a0) {
        ctx.pc=pc;ctx.r[4]=_mm_set_epi64x(0,a0);ctx.r[31]=_mm_set_epi64x(0,0x101000u);
        runtime.lookupFunction(pc)(runtime.memory().getRDRAM(),&ctx,&runtime);
        if(runtime.isStopRequested() || ctx.pc!=0x101000u)throw std::runtime_error("native call did not return");
    };
    bool ok=true;
    for(uint64_t value: {0ull,1ull,123ull,5000ull,30000ull}) {
        invoke(0x100220u,value);
        float expected=static_cast<float>(value);
        bool pass=ctx.f[0]==expected;ok&=pass;
        std::cout << "NATIVE_FLOAT value=" << value << " result=" << ctx.f[0] << " expected=" << expected << " pass=" << pass << '\n';
    }
    for(uint32_t count: {294000000u,1470000000u,2526839651u}) {
        runtime.memory().write8(0x3c79f0u-0x55c0u,1u);
        ctx.cop0_count=count;
        invoke(0x3318a0u,0u);
        uint32_t actual=static_cast<uint32_t>(_mm_cvtsi128_si32(ctx.r[2]));
        uint32_t expected=count/294u/1000u;
        bool pass=actual==expected;ok&=pass;
        std::cout << "NATIVE_CLOCK count=" << count << " result=" << actual << " expected=" << expected << " pass=" << pass << '\n';
    }
    std::cout << (ok?"PASS":"FAIL") << " native timer conversions\n";
    return ok?0:1;
}
