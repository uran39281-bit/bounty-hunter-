#pragma once
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <string>

namespace bounty_native {
// Called on the game thread. Separate from Java's rolling log files.
inline bool recordRunEvent(const std::filesystem::path &root,
                           const std::string &kind, uint32_t pc, uint32_t ra,
                           uint64_t branch, const std::string &detail = {}) noexcept {
    try {
        if (root.empty()) return false;
        const auto path = root / ".bounty-native-stop.txt";
        const auto mode = kind == "RUNNING" ? std::ios::trunc : std::ios::app;
        std::ofstream out(path, std::ios::binary | mode);
        if (!out) return false;
        out << kind << " pc=0x" << std::hex << pc << " ra=0x" << ra
            << " branchSource=0x" << uint32_t(branch >> 32)
            << " branchTarget=0x" << uint32_t(branch) << '\n'
            << detail.substr(0, 8192) << '\n';
        out.flush();
        return out.good();
    } catch (...) { return false; }
}
}
