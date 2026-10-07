// Host UI thread samples touch and physical input; mutex-backed Pad API delivers it.
#if defined(__ANDROID__)
#include "ps2_host_backend.h"
#include "runtime/ps2_pad.h"
#include "Kernel/Stubs/Pad.h"
#include <cstdlib>

namespace bounty_android {
void configureRuntime() {
    // Same opt-in boot compatibility settings exercised by the native diagnostic.
    for (const char *flag : {"PS2X_VFS_REUSE_DESCRIPTORS","PS2X_STOP_INVALID_MEMCPY",
         "PS2X_LOAD_BOOT_SIFCMD","PS2X_SPU2_ADMA_TIMING","PS2X_SPR_RECVN",
         "PS2X_EE_ZERO_PRIORITY","PS2X_LOAD_BOOT_CDVDFSV","PS2X_CDVD_COMPAT",
         "PS2X_CALLBACK_HEAP_STACKS","PS2X_COP0_COUNT","PS2X_EE_VA64",
         "PS2X_CAPTURE_ON_PRESENT"}) setenv(flag,"1",1);
}
void updatePad() {
    uint8_t data[32]{};
    PSPadBackend backend;
    backend.readState(0,0,data,sizeof(data));
    uint16_t pressed=0;
    const float width=GetScreenWidth(),height=GetScreenHeight();
    for (int i=0;i<GetTouchPointCount();++i) {
        const Vector2 point=GetTouchPosition(i);
        pressed|=bounty_touch::maskAt(point.x,point.y,width,height);
    }
    const uint16_t physical=static_cast<uint16_t>(data[2] | (data[3]<<8));
    ps2_stubs::setPadOverrideState(bounty_touch::merge(physical,pressed),data[6],data[7],data[4],data[5]);
}
void drawControls() {
    const float width=GetScreenWidth(),height=GetScreenHeight();
    const float r=bounty_touch::radius(width,height);
    const unsigned font=static_cast<unsigned>(std::max(12.0f,height*0.028f));
    const auto pad=ps2_stubs::getPadDebugSnapshot();
    for (const auto &b : bounty_touch::buttons) {
        const int x=static_cast<int>(b.x*width),y=static_cast<int>(b.y*height);
        const bool down=(pad.overrideButtons & b.mask)==0;
        DrawCircle(x,y,r,down?Color{90,150,210,170}:Color{25,35,50,135});
        DrawCircleLines(x,y,r,Color{200,210,220,190});
        DrawText(b.label,x-MeasureText(b.label,font)/2,y-font/2,font,Color{240,245,250,220});
    }
}
void releasePad() { ps2_stubs::clearPadOverrideState(); }
}
#endif
