// Bounded startup diagnostic using real runtime/scheduler interfaces.
// No window, audio device, or simulated success responses; capture real GS draws.
#include "ps2_runtime.h"
#include "runtime/ee_scheduler.h"
#include "runtime/gs/gs_frontend.h"
#include "Kernel/Stubs/Audio.h"
#include "Kernel/Stubs/MPEG.h"
#include <chrono>
#include <iostream>
#include <thread>
#include <fstream>
#include <cstdlib>

namespace ps2_stubs { void resetSifState(); }
#ifdef BOUNTY_OBSERVED_LEAF_ENTRIES
void registerObservedLeafEntries(PS2Runtime &runtime);
#endif

int main(int argc, char **argv) {
    if (argc != 2 && argc != 3) {
        std::cerr << "Usage: headless_startup path/to/SLUS_204.20 [seconds]\n";
        return 2;
    }
    const int seconds = argc == 3 ? std::stoi(argv[2]) : 5;
    if (seconds < 1 || seconds > 60) return 2;
    PS2Runtime runtime;
    runtime.setMissingFunctionPolicy(PS2Runtime::MissingFunctionPolicy::Stop);
    if (!runtime.memory().initialize() || !runtime.syncCoreSubsystems() ||
        !runtime.loadELF(argv[1])) return 1;
    #ifdef BOUNTY_OBSERVED_LEAF_ENTRIES
    registerObservedLeafEntries(runtime);
    #endif
    // GS history defaults to paused; observe real draws before capture.
    runtime.gs().setDebugHistoryPaused(false);
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
              << std::dec << " deadline_seconds=" << seconds << " graphics_tested=false audio_tested=false\n"
              << std::flush;
    std::jthread timer([&](std::stop_token stop) {
        auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(seconds);
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
    int result = 0;
    try {
        runtime.eeScheduler().run();
    } catch (const std::exception &error) {
        std::cerr << "HEADLESS_EXCEPTION " << error.what() << '\n';
        timer.request_stop();
        runtime.requestStop();
        result = 1;
    }
    timer.request_stop();
    timer.join();
    std::cout << "EE_REGISTERS s0=" << static_cast<uint32_t>(_mm_cvtsi128_si32(runtime.cpu().r[16]))
              << " a0=" << static_cast<uint32_t>(_mm_cvtsi128_si32(runtime.cpu().r[4]))
              << " gp=" << static_cast<uint32_t>(_mm_cvtsi128_si32(runtime.cpu().r[28])) << '\n';
    const auto graphics = runtime.gs().getDebugSnapshot();
    size_t recentDraws = 0;
    for (const auto &event : runtime.gs().getDebugHistory())
        if (event.kind == GSDebugEventKind::Draw) ++recentDraws;
    std::cout << "GRAPHICS_ACTIVITY packed_packets=" << runtime.gs().nativePackedGIFPacketCount()
              << " image_uploads=" << runtime.gs().nativeImageUploadCount()
              << " recent_draws=" << recentDraws
              << " presentation_frame=" << graphics.hasHostPresentationFrame
              << " width=" << graphics.hostPresentationWidth
              << " height=" << graphics.hostPresentationHeight << '\n';
    std::cout << "MEMORY_GRAPHICS_ACTIVITY dma_starts=" << runtime.memory().dmaStartCount()
              << " gif_copies=" << runtime.memory().gifCopyCount()
              << " gs_writes=" << runtime.memory().gsWriteCount()
              << " vif_writes=" << runtime.memory().vifWriteCount() << '\n';
    if (std::getenv("PS2X_BOOT_GRAPHICS_TRACE")) {
        const auto history = runtime.gs().getDebugHistory();
        size_t tags=0, transfers=0, drawSamples=0;
        for (const auto &event : history) {
            if (event.kind == GSDebugEventKind::GifTag) {
                if (++tags <= 16) std::cout << "BOOT_GS_TAG seq=" << event.seq
                    << " nloop=" << event.gifNloop << " flg=" << unsigned(event.gifFlg)
                    << " nreg=" << unsigned(event.gifNreg) << " bytes=" << event.gifSizeBytes << '\n';
            }
            if (event.kind == GSDebugEventKind::Draw && ++drawSamples <= 12)
                std::cout << "BOOT_GS_DRAW seq=" << event.seq << " fbp=" << event.frame.fbp
                    << " fbw=" << event.frame.fbw << " psm=" << unsigned(event.frame.psm)
                    << " texture_base=" << event.tex0.tbp0 << " texture_bw=" << unsigned(event.tex0.tbw)
                    << " texture_psm=" << unsigned(event.tex0.psm)
                    << " texture_tw=" << unsigned(event.tex0.tw) << " texture_th=" << unsigned(event.tex0.th)
                    << " x=" << event.xMin << ',' << event.xMax << " y=" << event.yMin << ',' << event.yMax << '\n';
            if (event.kind == GSDebugEventKind::Transfer) ++transfers;
        }
        std::cout << "BOOT_GS_HISTORY entries=" << history.size() << " tags=" << tags
                  << " transfers=" << transfers << " paused=" << runtime.gs().isDebugHistoryPaused()
                  << " prim=" << unsigned(graphics.prim.type)
                  << " copied_pixels=" << graphics.transferCopiedPixels << '\n';

        const uint32_t gp = static_cast<uint32_t>(_mm_cvtsi128_si32(runtime.cpu().r[28]));
        std::cout << "BOOT_GRAPHICS_STATE cop0_count=" << runtime.cpu().cop0_count
                  << " vsync_tick=" << runtime.memory().gs().vsyncTick.load()
                  << " current=" << runtime.memory().read32(gp-0x38fcu)
                  << " requested=" << runtime.memory().read32(gp-0x38f8u)
                  << " buffer=0x" << std::hex << runtime.memory().read32(0x454918u)
                  << " end=0x" << runtime.memory().read32(0x45491cu)
                  << " pmode=0x" << runtime.memory().gs().pmode
                  << " dispfb1=0x" << runtime.memory().gs().dispfb1
                  << " display1=0x" << runtime.memory().gs().display1
                  << " dispfb2=0x" << runtime.memory().gs().dispfb2
                  << " display2=0x" << runtime.memory().gs().display2
                  << " vif_chcr=0x" << runtime.memory().readIORegister(0x10009000u)
                  << " d_ctrl=0x" << runtime.memory().readIORegister(0x1000e000u)
                  << std::dec << '\n';
    }
    if (recentDraws > 0 && std::getenv("PS2X_CAPTURE_FRAME")) {
        runtime.gs().latchHostPresentationFrame();
        std::vector<uint8_t> pixels;
        uint32_t width=0, height=0;
        if (runtime.gs().copyLatchedHostPresentationFrame(pixels, width, height) &&
            pixels.size() == static_cast<size_t>(width)*height*4u) {
            std::ofstream file(std::getenv("PS2X_CAPTURE_FRAME"), std::ios::binary);
            file << "P6\n" << width << ' ' << height << "\n255\n";
            for (size_t offset=0; offset<pixels.size(); offset+=4u)
                file.write(reinterpret_cast<const char*>(pixels.data()+offset), 3);
            std::cout << "CAPTURED_GS_FRAME width=" << width << " height=" << height << '\n';
        }
    }
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
    return result;
}
