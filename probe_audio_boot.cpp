// Isolate real IRX startup using supplied modules; no fake RPC registration.
#include "emulator/iop_emulator.h"
#include "iop_compat_test_support.h"
#include <filesystem>
#include <fstream>
#include <iterator>

int main(int argc, char **argv) {
    if (argc < 2) return 2;
    iop_test::Host host(32u * 1024u * 1024u);
    ps2x::iop::detail::IopEmulator emulator(host);
    for (int i = 1; i < argc; ++i) {
        std::ifstream file(argv[i], std::ios::binary);
        if (!file) return 2;
        host.file.assign(std::istreambuf_iterator<char>(file), {});
        const auto result = emulator.loadModule(argv[i], nullptr, 0);
        std::cout << "MODULE name=" << std::filesystem::path(argv[i]).filename().string()
                  << " id=" << result.moduleId << " start=" << result.startResult << '\n';
        emulator.runEeCycles(3000000u);
        std::vector<std::string> rows;
        emulator.appendDiagnosticRows(rows);
        for (const auto &row : rows) std::cout << row << '\n';
    }
    for (unsigned i = 0; i < 5; ++i) emulator.runEeCycles(10000000u);
    std::vector<std::string> rows;
    emulator.appendDiagnosticRows(rows);
    std::cout << "FINAL instructions=" << emulator.instructions() << '\n';
    for (const auto &row : rows) std::cout << row << '\n';
    for (const auto &message : host.logs) std::cout << message << '\n';
    std::cout << "DTX_REGISTERED " << emulator.hasRpcServer(0x7d000000u) << '\n';
}
