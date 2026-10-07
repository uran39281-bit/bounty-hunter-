// Verify real EE thread creation at priority zero without fabricating thread IDs.
#include "ps2_runtime.h"
#include "runtime/ee_scheduler.h"
#include <cstdlib>
#include <iostream>
#include <stdexcept>

void require(bool ok, const char *message) { if (!ok) throw std::runtime_error(message); }
int main() {
    PS2Runtime runtime;
    require(runtime.memory().initialize(), "RAM init failed");
    R5900Context ctx{};
    ctx.pc=0x100008u;ctx.r[29]=_mm_set_epi64x(0,0x01fffff0u);
    auto &ee=runtime.eeScheduler();
    ee.reset(runtime.memory().getRDRAM(),ctx);
    EeThreadCreateParams param{};
    param.entry=0x101000u;param.stack=0x400000u;param.stackSize=4096;param.priority=0;
    unsetenv("PS2X_EE_ZERO_PRIORITY");
    require(ee.createThread(param) < 0, "baseline priority-zero behavior changed");
    setenv("PS2X_EE_ZERO_PRIORITY","1",1);
    const int id=ee.createThread(param);
    require(id>1, "priority-zero thread creation failed");
    const auto *thread=ee.thread(id);
    require(thread && thread->initialPriority==0 && thread->currentPriority==0,
            "thread priority changed");
    require(thread->entry==param.entry && thread->status==EeThreadStatus::Dormant,
            "real thread state not created");
    param.priority=-1;require(ee.createThread(param)<0, "negative priority accepted");
    param.priority=128;require(ee.createThread(param)<0, "out-of-range priority accepted");
    unsetenv("PS2X_EE_ZERO_PRIORITY");
    param.priority=127;require(ee.createThread(param)>id, "ordinary priority rejected");
    std::cout << "PASS: opt-out baseline, real priority-zero thread and descriptor, priorities -1/128 rejected, priority 127 accepted\n";
}
