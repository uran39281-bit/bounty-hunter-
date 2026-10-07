#include "ps2_runtime.h"
#include "ps2_stubs.h"
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>

void check(bool ok, const char *message) { if (!ok) throw std::runtime_error(message); }
int main() {
    PS2Runtime runtime;
    check(runtime.memory().initialize(), "RAM init failed");
    auto *ram=runtime.memory().getRDRAM();
    auto call=[&](const char *format) {
        std::strcpy(reinterpret_cast<char*>(ram+0x1000),format);
        R5900Context ctx{};
        ctx.r[4]=_mm_set_epi64x(0,0x2000);
        ctx.r[5]=_mm_set_epi64x(0,0x1000);
        ctx.r[6]=_mm_set_epi64x(0,0x4000);
        ps2_stubs::vsprintf(ram,&ctx,&runtime);
        return std::string(reinterpret_cast<char*>(ram+0x2000));
    };
    std::strcpy(reinterpret_cast<char*>(ram+0x3000),"start");
    // Same layout as original native SD argument saves, at 0, 8, 16...
    runtime.memory().write64(0x4000,0x3000);
    runtime.memory().write64(0x4008,2);
    unsetenv("PS2X_EE_VA64");
    check(call("%s_%02d.r2t")=="start_00.r2t", "opt-out baseline changed");
    setenv("PS2X_EE_VA64","1",1);
    for (uint32_t number=1;number<=5;++number) {
        runtime.memory().write64(0x4008,number);
        check(call("%s_%02d.r2t")=="start_0"+std::to_string(number)+".r2t", "texture number lost");
    }
    runtime.memory().write64(0x4000,uint64_t(int64_t(-7)));
    runtime.memory().write64(0x4008,0x1122334455667788ull);
    double value=1.25;uint64_t bits;std::memcpy(&bits,&value,8);
    runtime.memory().write64(0x4010,bits);
    runtime.memory().write64(0x4018,0x3000);
    check(call("%d %llx %.2f %s")=="-7 1122334455667788 1.25 start", "mixed arguments or doubles lost");
    unsetenv("PS2X_EE_VA64");
    runtime.memory().write32(0x4000,11);
    runtime.memory().write32(0x4004,22);
    check(call("%d %d")=="11 22", "four-byte opt-out layout changed");
    std::cout << "PASS: opt-out four-byte layout, five distinct texture names, signed integers, 64-bit values, doubles and strings\n";
}
