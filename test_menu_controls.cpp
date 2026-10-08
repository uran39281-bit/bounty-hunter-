#include "android_touch_controls.h"
#include "ps2_runtime.h"
#include "menu_input_script.h"
#include "Kernel/Stubs/Pad.h"
#include <iostream>
#include <vector>
#include <stdexcept>

void check(bool condition,const char *message) { if (!condition) throw std::runtime_error(message); }
void reg(R5900Context &ctx,int n,uint32_t value) { ctx.r[n]=_mm_set_epi64x(0,value); }
int main() {
    check(menuScriptButtons(127)==0xffffu && menuScriptButtons(128)==0xfff7u &&
          menuScriptButtons(136)==0xffffu && menuScriptButtons(160)==0xbfffu &&
          menuScriptButtons(168)==0xffffu && menuScriptButtons(192)==0xffbfu &&
          menuScriptButtons(224)==0xdfffu,"script press/release boundaries");
    check(menuScriptButtons(336)==0xffefu && menuScriptButtons(344)==0xffffu &&
          menuScriptButtons(352)==0xff7fu && menuScriptButtons(368)==0xffdfu &&
          menuScriptButtons(384)==0xdfffu && menuScriptButtons(400)==0xfff7u &&
          menuScriptButtons(416)==0xbfffu && menuScriptButtons(432)==0xffbfu,
          "complete native navigation script");
    // Exercise portrait and landscape layouts, both edges, release, and multi-touch.
    for (const auto dimensions : {std::array<float,2>{1920,1080},{1080,2340},{2340,1080}}) {
        for (const auto &b:bounty_touch::buttons)
            check(bounty_touch::maskAt(b.x*dimensions[0],b.y*dimensions[1],dimensions[0],dimensions[1])==b.mask,"button hit");
        check(bounty_touch::maskAt(0,0,dimensions[0],dimensions[1])==0,"outside all buttons");
    }
    check(bounty_touch::maskAt(0,0,0,1080)==0,"uninitialized surface");
    const uint16_t startCross=0x4008u, up=0x0010u;
    const uint16_t both=bounty_touch::merge(static_cast<uint16_t>(~up),startCross);
    check(both==static_cast<uint16_t>(~(up|startCross)),"physical and touch merge");
    std::vector<uint8_t> ram(PS2_RAM_SIZE);R5900Context ctx{};
    ps2_stubs::scePadInit(ram.data(),&ctx,nullptr);
    reg(ctx,4,0);reg(ctx,5,0);reg(ctx,6,0x1200);
    ps2_stubs::scePadPortOpen(ram.data(),&ctx,nullptr);
    for (uint16_t buttons:{both,uint16_t(0xffff)}) {
        ps2_stubs::setPadOverrideState(buttons,128,128,128,128);
        reg(ctx,4,0);reg(ctx,5,0);reg(ctx,6,0x1000);
        ps2_stubs::scePadRead(ram.data(),&ctx,nullptr);
        check(_mm_cvtsi128_si32(ctx.r[2])==1,"pad read success");
        check((ram[0x1002]|(ram[0x1003]<<8))==buttons,"real Pad API delivers press and release");
        check(ram[0x1004]==128 && ram[0x1007]==128,"centered axes");
    }
    ps2_stubs::clearPadOverrideState();
    check(!ps2_stubs::getPadDebugSnapshot().overrideEnabled,"override cleared");
    std::cout<<"PASS menu touch layout, physical/touch merge, actual pad press/release\n";
}
