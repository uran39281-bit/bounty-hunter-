// Regression: real callback allocations must not overwrite the live main stack.
#include "ps2_runtime.h"
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <cstring>
void require(bool ok,const char*msg){if(!ok)throw std::runtime_error(msg);}
int main(){
 PS2Runtime runtime;require(runtime.memory().initialize(),"RAM init failed");
 runtime.configureGuestHeap(0x800000u,0x1800000u);
 auto*ram=runtime.memory().getRDRAM();
 constexpr uint32_t canaryAddress=PS2_RAM_SIZE-0x40u;constexpr uint64_t canary=0x1234567887654321ull;
 auto write64=[&](uint32_t address,uint64_t value){std::memcpy(ram+address,&value,sizeof(value));};
 auto read64=[&](uint32_t address){uint64_t value;std::memcpy(&value,ram+address,sizeof(value));return value;};
 unsetenv("PS2X_CALLBACK_HEAP_STACKS");write64(canaryAddress,canary);
 const auto baseline=runtime.reserveAsyncCallbackStack(0x4000u,16u);
 require(baseline==PS2_RAM_SIZE-16u,"baseline changed");
 write64(baseline-0x30u,0);
 require(read64(canaryAddress)==0,"baseline overlap not reproduced");
 write64(canaryAddress,canary);setenv("PS2X_CALLBACK_HEAP_STACKS","1",1);
 const auto live=runtime.guestMalloc(64u,16u);require(live!=0,"ordinary allocation failed");
 write64(live,canary);
 const auto first=runtime.reserveAsyncCallbackStack(0x4000u,64u);
 const auto second=runtime.reserveAsyncCallbackStack(0x4000u,64u);
 require(first>=0x800000u&&first<0x1800000u&&second>first,"callbacks outside heap or aliased");
 require(((first+16u-0x4000u)&63u)==0,"allocation alignment wrong");
 write64(first-0x30u,0);write64(second-0x30u,0);
 require(read64(canaryAddress)==canary,"main return address overwritten");
 require(read64(live)==canary,"live heap allocation overwritten");
 require(runtime.reserveAsyncCallbackStack(0u)==0,"zero-sized request allocated");
 require(runtime.reserveAsyncCallbackStack(PS2_RAM_SIZE)==0,"exhausted heap invented stack");
 std::cout<<"PASS: baseline return-address overlap, separate allocated callback stacks, alignment, main/heap canaries intact, zero/exhausted allocation rejection\n";
}
