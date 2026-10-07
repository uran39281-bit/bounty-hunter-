// Verify streaming cadence without changing normal DMA timing or sample data.
#include "emulator/core/iop_memory.h"
#include <cstdlib>
#include <iostream>
#include <stdexcept>

using ps2x::iop::detail::IopMemory;
void require(bool ok, const char *message) {
    if (!ok) throw std::runtime_error(message);
}
void check(IopMemory &memory, bool second, unsigned admas, unsigned direction,
           uint64_t delay) {
    const uint32_t chcr = second ? 0x1f801508u : 0x1f8010c8u;
    const uint32_t core = second ? 0x400u : 0u;
    memory.write16(0x1f9001b0u + core, admas);
    memory.write32(chcr - 4u, 0x00200010u); // 512 words = 2048 bytes
    memory.write32(chcr, 0x01000200u | direction);
    const auto start = memory.takeDmaStart();
    require(start.has_value(), "Missing DMA completion event");
    require(start->irq == (second ? 0x28 : 0x24), "Wrong core interrupt");
    require(start->delayCycles == delay, "Wrong DMA completion cadence");
    require(!memory.takeDmaStart(), "Duplicate event for one DMA start");
}
int main() {
    unsetenv("PS2X_SPU2_ADMA_TIMING");
    IopMemory memory;
    check(memory, false, 1, 1, 1024); // historical baseline
    setenv("PS2X_SPU2_ADMA_TIMING", "1", 1);
    check(memory, false, 1, 1, 393216);
    check(memory, true, 2, 1, 393216);
    check(memory, false, 0, 1, 1024); // plain write
    check(memory, true, 1, 1, 1024); // wrong core enable bit
    check(memory, false, 4, 0, 1024); // read mode
    memory.reset();
    check(memory, false, 0, 1, 1024);
    std::cout << "PASS SPU2 AutoDMA cadence: both cores, baseline, plain DMA, read mode, reset\n";
}
