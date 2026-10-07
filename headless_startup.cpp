// Bounded startup diagnostic using real runtime/scheduler interfaces.
// No window, audio device, rendered frames, or simulated success responses.
#include "ps2_runtime.h"
#include "runtime/ee_scheduler.h"
#include "Kernel/Stubs/Audio.h"
#include "Kernel/Stubs/MPEG.h"
#include <chrono>
#include <iostream>
#include <thread>

namespace ps2_stubs { void resetSifState(); }

int main(int argc, char **argv) {
    if (argc != 2) {
        std::cerr << "Usage: headless_startup path/to/SLUS_204.20\n";
        return 2;
    }
    PS2Runtime runtime;
    runtime.setMissingFunctionPolicy(PS2Runtime::MissingFunctionPolicy::Stop);
    if (!runtime.memory().initialize() || !runtime.syncCoreSubsystems() ||
        !runtime.loadELF(argv[1])) return 1;
    ps2_stubs::resetSifState();
    ps2_stubs::resetAudioStubState();
    ps2_stubs::resetMpegStubState();
    auto *ram = runtime.memory().getRDRAM();
    runtime.initializeEeKernelState(ram);
    runtime.cpu().r[4] = _mm_setzero_si128();
    runtime.cpu().r[5] = _mm_setzero_si128();
    runtime.cpu().r[29] = _mm_set_epi64x(0, PS2_RAM_SIZE - 0x10u);
    runtime.eeScheduler().reset(ram, runtime.cpu());
    std::cout << "HEADLESS_START entry=0x" << std::hex << runtime.cpu().pc
              << std::dec << " deadline_seconds=5 graphics_tested=false audio_tested=false\n"
              << std::flush;
    std::jthread timer([&](std::stop_token stop) {
        auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(5);
        while (!stop.stop_requested() && std::chrono::steady_clock::now() < deadline) {
            std::this_thread::sleep_for(std::chrono::milliseconds(17));
            // The actual scheduler already provides its VBlank events.
        }
        if (!stop.stop_requested()) {
            const auto before = runtime.eeScheduler().snapshot();
            for (const auto &thread : before.threads)
                std::cerr << "BEFORE_DEADLINE id=" << thread.id << " pc=0x" << std::hex << thread.pc
                          << " ra=0x" << thread.ra << std::dec << " status=" << int(thread.status)
                          << " wait=" << int(thread.waitReason) << '\n';
            std::cerr << "HEADLESS_DEADLINE requesting stop\n";
            runtime.requestStop();
        }
    });
    try {
        runtime.eeScheduler().run();
    } catch (const std::exception &error) {
        std::cerr << "HEADLESS_EXCEPTION " << error.what() << '\n';
        timer.request_stop();
        runtime.requestStop();
        return 1;
    }
    timer.request_stop();
    timer.join();
    const auto iop = runtime.iopDebugSnapshot();
    for (const auto &row : iop.diagnostics)
        std::cout << "IOP_DIAGNOSTIC " << row << '\n';
    std::cout << "IOP_STOP loaded_modules=" << iop.emulatorLoadedModules
              << " threads=" << iop.emulatorThreads << " rpc_servers=" << iop.emulatorRpcServers
              << " instructions=" << iop.emulatorInstructions << '\n';
    const auto snapshot = runtime.eeScheduler().snapshot();
    std::cout << "HEADLESS_STOP ee_cycles=" << snapshot.eeCycle
              << " threads=" << snapshot.threads.size() << '\n';
    for (const auto &thread : snapshot.threads) {
        std::cout << "THREAD id=" << thread.id << " pc=0x" << std::hex << thread.pc
                  << " ra=0x" << thread.ra << " sp=0x" << thread.sp << std::dec
                  << " status=" << int(thread.status) << " wait=" << int(thread.waitReason) << '\n';
    }
    // Exit zero means the diagnostic returned; it does not mean the game works.
    return 0;
}
