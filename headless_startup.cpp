// Bounded startup diagnostic using real runtime/scheduler interfaces.
// No window, audio device, or simulated success responses; capture real GS draws.
#include "ps2_runtime.h"
#include "runtime/ee_scheduler.h"
#include "runtime/gs/gs_frontend.h"
#include "Kernel/Stubs/Audio.h"
#include "Kernel/Stubs/MPEG.h"
#include "Kernel/Stubs/Pad.h"
#include "menu_input_script.h"
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
    if (seconds < 1 || seconds > 600) return 2;
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
    const bool scriptInput=std::getenv("PS2X_SCRIPT_MENU_INPUT")!=nullptr;
    if (scriptInput) ps2_stubs::setPadOverrideState(0xffffu,128,128,128,128);
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
        uint16_t lastButtons=0xffffu;
        while (!stop.stop_requested() && std::chrono::steady_clock::now() < deadline) {
            std::this_thread::sleep_for(std::chrono::milliseconds(17));
            if (scriptInput) {
                const auto reads=ps2_stubs::getPadDebugSnapshot().ports[0][0].readCount;
                const uint16_t buttons=menuScriptButtons(reads);
                if (buttons!=lastButtons) {
                    ps2_stubs::setPadOverrideState(buttons,128,128,128,128);
                    std::cerr << "SCRIPTED_PAD_INPUT reads=" << reads << " buttons=0x"
                              << std::hex << buttons << std::dec << '\n';
                    lastButtons=buttons;
                }
            }
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
    const auto pads = ps2_stubs::getPadDebugSnapshot();
    if (scriptInput) ps2_stubs::clearPadOverrideState();
    for (unsigned port=0; port<ps2_stubs::kPadDebugPortCount; ++port) {
        const auto &pad = pads.ports[port][0];
        std::cout << "PAD_ACTIVITY port=" << port << " open=" << pad.open
                  << " reads=" << pad.readCount << " ok=" << pad.lastReadOk
                  << " override=" << pad.lastUsedOverride << " backend=" << pad.lastUsedBackend
                  << " buttons=0x" << std::hex << pad.lastButtons << std::dec << '\n';
    }
    if (std::getenv("PS2X_FRONTEND_TRACE")) {
        const uint32_t gp=static_cast<uint32_t>(_mm_cvtsi128_si32(runtime.cpu().r[28]));
        if (gp>=0x6650u && gp<PS2_RAM_SIZE) {
            const uint32_t front=runtime.memory().read32(gp-0x3b18u);
            const uint32_t object=runtime.memory().read32(front+4u);
            const uint32_t menu=runtime.memory().read32(object+0x18u);
            std::cout << "FRONTEND_STATE state=" << unsigned(runtime.memory().read8(gp-0x6650u))
                      << " mode=" << unsigned(runtime.memory().read8(gp-0x3b00u))
                      << " menu_id=0x" << std::hex << runtime.memory().read32(menu+4u)
                      << " logical_buttons=0x" << runtime.memory().read32(0x3f0634u)
                      << std::dec << '\n';
        }
    }
    std::cout << "EE_REGISTERS s0=" << static_cast<uint32_t>(_mm_cvtsi128_si32(runtime.cpu().r[16]))
              << " a0=" << static_cast<uint32_t>(_mm_cvtsi128_si32(runtime.cpu().r[4]))
              << " gp=" << static_cast<uint32_t>(_mm_cvtsi128_si32(runtime.cpu().r[28])) << '\n';
    const auto graphics = runtime.gs().getDebugSnapshot();
    if (const char *prefix=std::getenv("PS2X_DUMP_VU_STATE")) {
        std::ofstream code(std::string(prefix)+".vu1code",std::ios::binary);
        code.write(reinterpret_cast<const char *>(runtime.memory().getVU1Code()),PS2_VU1_CODE_SIZE);
        std::ofstream data(std::string(prefix)+".vu1data",std::ios::binary);
        data.write(reinterpret_cast<const char *>(runtime.memory().getVU1Data()),PS2_VU1_DATA_SIZE);
        std::cout<<"VU_STATE_DUMP code="<<bool(code)<<" data="<<bool(data)<<'\n';
    }
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
        if (!std::getenv("PS2X_CAPTURE_ON_PRESENT"))
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
            const auto presented = runtime.gs().getDebugSnapshot();
            std::cout << "BOOT_GS_PRESENT display=" << presented.hostPresentationDisplayFbp
                      << " source=" << presented.hostPresentationSourceFbp
                      << " preferred=" << presented.hostPresentationUsedPreferred << '\n';
        }
    }
    if (recentDraws > 0 && std::getenv("PS2X_CAPTURE_FRAME") && std::getenv("PS2X_BOOT_GRAPHICS_TRACE")) {
        // Original game memory for private byte comparisons; never public source.
        if (std::getenv("PS2X_DUMP_GRAPHICS_MEMORY")) {
            const std::string capturePath=std::getenv("PS2X_CAPTURE_FRAME");
            std::ofstream ram(capturePath+".ram",std::ios::binary);
            ram.write(reinterpret_cast<const char*>(runtime.memory().getRDRAM()),PS2_RAM_SIZE);
            std::ofstream vram(capturePath+".vram",std::ios::binary);
            vram.write(reinterpret_cast<const char*>(runtime.memory().getGSVRAM()),PS2_GS_VRAM_SIZE);
        }
        // Diagnostic offscreen surfaces from actual native draws, not CRT presentation.
        for (unsigned c=0; c<2; ++c) {
            const auto &frame=graphics.ctx[c].frame;
            if (frame.psm != 0 || frame.fbw == 0) continue;
            std::ofstream file(std::string(std::getenv("PS2X_CAPTURE_FRAME"))+".ctx"+std::to_string(c)+".ppm", std::ios::binary);
            file << "P6\n640 448\n255\n";
            for (uint32_t y=0; y<448; ++y) for (uint32_t x=0; x<640; ++x) {
                const uint32_t color=runtime.gs().ReadVram(frame.psm,frame.fbp*32u,frame.fbw,x,y);
                const uint8_t rgb[]={uint8_t(color),uint8_t(color>>8),uint8_t(color>>16)};
                file.write(reinterpret_cast<const char*>(rgb),3);
            }
            std::cout << "BOOT_OFFSCREEN_CAPTURE context=" << c << " fbp=" << frame.fbp << " fbw=" << frame.fbw << '\n';
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
