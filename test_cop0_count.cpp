// Shared hardware Count follows scheduler cycles and explicit guest writes.
#include "ps2_runtime.h"
#include "runtime/ee_scheduler.h"
#include <cstdlib>
#include <iostream>
#include <stdexcept>

void require(bool ok, const char *message) {
    if (!ok) throw std::runtime_error(message);
}
int workerId = 0;
void guest(uint8_t *, R5900Context *ctx, PS2Runtime *runtime) {
    auto &ee = runtime->eeScheduler();
    const uint32_t previous = ctx->cop0_count;
    require(previous >= 11u, "new interrupt context reset Count");
    ee.accountCycles(123u);
    require(ctx->cop0_count == previous + 123u, "active Count did not advance");
    // This is the field written by the native MTC0 Count translation.
    ctx->cop0_count = 0xfffffffeu;
    ee.accountCycles(3u);
    require(ctx->cop0_count == 1u, "guest write or 32-bit wrap lost");
    require(ee.thread(workerId)->context.cop0_count == 1u,
            "dormant thread retained a private counter");
    runtime->requestStop();
}
int main() {
    PS2Runtime runtime;
    require(runtime.memory().initialize(), "RAM init failed");
    auto &ee = runtime.eeScheduler();
    runtime.cpu() = {};
    runtime.cpu().pc = 0x101000u;
    runtime.cpu().cop0_count = 0xfffffffeu;
    ee.reset(runtime.memory().getRDRAM(), runtime.cpu());
    unsetenv("PS2X_COP0_COUNT");
    ee.accountCycles(3u);
    require(ee.thread(1)->context.cop0_count == 0xfffffffeu,
            "opt-out Count behavior changed");
    setenv("PS2X_COP0_COUNT", "1", 1);
    ee.accountCycles(3u);
    require(ee.thread(1)->context.cop0_count == 1u, "idle Count wrap failed");
    EeThreadCreateParams param{};
    param.entry = 0x102000u; param.stack = 0x400000u;
    param.stackSize = 4096u; param.priority = 50;
    workerId = ee.createThread(param);
    require(workerId > 1, "worker creation failed");
    ee.accountCycles(10u);
    require(ee.thread(1)->context.cop0_count == 11u &&
            ee.thread(workerId)->context.cop0_count == 11u,
            "shared idle cadence failed");
    auto caller = runtime.cpu();
    require(ee.startThread(workerId, 0u, caller, false) == 0,
            "worker start failed");
    require(ee.thread(workerId)->context.cop0_count == 11u,
            "new worker context reset Count");
    GuestInvocation invocation{};
    invocation.kind = GuestInvocationKind::Interrupt;
    invocation.context.pc = 0x101000u;
    ee.queueInvocation(std::move(invocation));
    require(runtime.registerFunction(0x101000u, guest), "guest fixture registration failed");
    ee.run();
    require(ee.thread(1)->context.cop0_count == 1u, "IRQ counter was not shared with parent");
    std::cout << "PASS: opt-out baseline, idle/active cadence, guest Count writes, 32-bit wrap, dormant thread and interrupt-context sharing\n";
}
