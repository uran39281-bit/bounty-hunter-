// Isolated PS2Recomp IOP loader/entry probe, not an EE game boot.
// Build against the pinned PS2Recomp source, including its upstream test host.
#include "emulator/core/iop_memory.h"
#include "emulator/services/iop_module_loader.h"
#include "emulator/iop_emulator.h"
#include "iop_compat_test_support.h"
#include <fstream>
#include <iterator>

int main(int argc, char **argv) {
    if (argc != 3) {
        std::cerr << "Usage: probe_irx load|init file.IRX\n";
        return 2;
    }
    std::ifstream file(argv[2], std::ios::binary);
    if (!file) return 2;
    std::vector<uint8_t> image((std::istreambuf_iterator<char>(file)), {});
    using namespace ps2x::iop::detail;
    IopMemory memory;
    const auto loaded = IopModuleLoader::load(image, memory, 0x10000u);
    std::cout << "load_ok=" << bool(loaded)
              << " error=" << int(loaded.error)
              << " base=" << loaded.base << " size=" << loaded.size
              << " entry=" << loaded.entry
              << " relocations_complete=" << loaded.relocationsComplete << '\n';
    if (!loaded) return 1;
    if (std::string_view(argv[1]) == "init") {
        // Fresh subsystem, no other IRX modules or game assets. File reads
        // return only this module. Results cannot establish a valid boot order.
        iop_test::Host host;
        host.file = image;
        IopEmulator emulator(host);
        const auto result = emulator.loadModule("host:probe.irx", nullptr, 0);
        std::cout << "module_id=" << result.moduleId
                  << " start_result=" << result.startResult
                  << " instructions=" << emulator.instructions()
                  << " threads=" << emulator.threadCount()
                  << " rpc_servers=" << emulator.rpcServerCount() << '\n';
        for (const auto &message : host.logs) std::cout << message << '\n';
    } else if (std::string_view(argv[1]) != "load") {
        return 2;
    }
    return 0;
}
