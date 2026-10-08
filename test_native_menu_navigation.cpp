// Invoke unchanged original menu handlers from a private native RAM capture.
// Each button starts from the same capture; this is an isolated host regression.
#include "ps2_runtime.h"
#include <fstream>
#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <cstring>
void registerObservedLeafEntries(PS2Runtime &runtime);
int main(int argc,char **argv) {
    if(argc!=3)return 2;
    std::ifstream file(argv[2],std::ios::binary);
    std::vector<uint8_t> snapshot{std::istreambuf_iterator<char>(file),{}};
    if(snapshot.size()!=PS2_RAM_SIZE)return 2;
    bool ok=true;
    for(auto button:{std::pair<const char *,uint32_t>{"Up",0x18u},
        {"Down",0x19u},{"Left",0x16u},{"Right",0x17u},
        {"Cross",0x1cu},{"Circle",0x1bu},{"Start",0x1eu}}) {
        PS2Runtime runtime;
        runtime.setMissingFunctionPolicy(PS2Runtime::MissingFunctionPolicy::Stop);
        if(!runtime.memory().initialize()||!runtime.syncCoreSubsystems()||!runtime.loadELF(argv[1]))return 2;
        registerObservedLeafEntries(runtime);
        auto *ram=runtime.memory().getRDRAM();
        std::memcpy(ram,snapshot.data(),snapshot.size());
        const uint32_t gp=0x3c79f0u;
        const uint32_t front=runtime.memory().read32(gp-0x3b18u);
        const uint32_t object=runtime.memory().read32(front+4u);
        const uint32_t menu=runtime.memory().read32(object+0x18u);
        if(object>=PS2_RAM_SIZE-0x200u||menu>=PS2_RAM_SIZE-0x200u)return 2;
        const uint32_t originalScreen=runtime.memory().read32(menu+4u);
        // This fixture is the captured No selection in the original warning.
        if(originalScreen!=0x35eu || snapshot[0x639168u]!=0u || snapshot[0x6392e8u]!=1u)return 2;
        auto &ctx=runtime.cpu();ctx={};ctx.pc=0x31f280u;
        ctx.r[4]=_mm_set_epi64x(0,object);ctx.r[5]=_mm_set_epi64x(0,button.second);
        ctx.r[28]=_mm_set_epi64x(0,gp);ctx.r[29]=_mm_set_epi64x(0,0x1f00000u);
        ctx.r[31]=_mm_set_epi64x(0,0x101000u);
        auto handler=runtime.lookupFunction(ctx.pc);if(!handler)return 2;
        std::jthread deadline([&](std::stop_token stop){
            auto end=std::chrono::steady_clock::now()+std::chrono::seconds(2);
            while(!stop.stop_requested()&&std::chrono::steady_clock::now()<end)
                std::this_thread::sleep_for(std::chrono::milliseconds(5));
            if(!stop.stop_requested())runtime.requestStop();
        });
        handler(ram,&ctx,&runtime);deadline.request_stop();deadline.join();
        const int result=_mm_cvtsi128_si32(ctx.r[2]);
        bool pass=ctx.pc==0x101000u&&!runtime.isStopRequested();
        size_t changed=0;for(size_t i=0;i<snapshot.size();++i)changed+=ram[i]!=snapshot[i];
        unsigned shown=0;size_t stateChanges=0;
        for(size_t i=0;i<snapshot.size();++i)
            if(ram[i]!=snapshot[i]&&(i<0x1ef0000u||i>=0x1f00000u)) {
                ++stateChanges;
                if(shown++<16u)std::cout<<"MENU_CHANGE button="<<button.first<<" address=0x"<<std::hex<<i
                    <<" before="<<unsigned(snapshot[i])<<" after="<<unsigned(ram[i])<<std::dec<<'\n';
            }
        if(button.second==0x18u||button.second==0x19u)
            pass&=result==0&&ram[0x639168u]==1u&&ram[0x6392e8u]==0u;
        else if(button.second==0x1cu)
            pass&=result==0&&runtime.memory().read32(0x638d28u)==0x4fu&&ram[object+0x60u]==0u;
        else pass&=result==-2&&stateChanges==0u;
        ok&=pass;
        std::cout<<"NATIVE_MENU_CAPTURE button="<<button.first<<" event=0x"<<std::hex<<button.second
            <<" original_menu=0x"<<originalScreen<<" return_pc=0x"<<ctx.pc<<std::dec
            <<" result="<<result<<" changed_ram_bytes="<<changed<<" state_changes="<<stateChanges<<" pass="<<pass<<'\n';
    }
    std::cout<<(ok?"PASS":"FAIL")<<" original warning: Up/Down toggle No to Yes; Cross requests original screen 0x4f; Left/Right/Circle/Start leave state unchanged. Isolated capture regression, no device validation\n";
    return ok?0:1;
}
