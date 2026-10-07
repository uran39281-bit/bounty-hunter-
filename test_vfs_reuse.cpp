// Regression: serial file loads must not exhaust a small guest descriptor table.
#include "runtime/ps2_vfs.h"
#include "runtime/ps2_rom_device.h"
#include "runtime/ps2_memory.h"
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <stdexcept>

void require(bool value, const char *message) {
    if (!value) throw std::runtime_error(message);
}

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    const std::filesystem::path root = argv[1];
    std::filesystem::create_directories(root);
    std::ofstream(root / "fixture.txt") << "AB";
    PS2RomDevice rom;
    PS2VfsMounts mounts{root, root, root};
    unsetenv("PS2X_VFS_REUSE_DESCRIPTORS");
    PS2Vfs baseline;
    int last = -1;
    for (int i=0; i<20; ++i) {
        last = baseline.open("host0:fixture.txt", PS2_FIO_O_RDONLY, mounts, rom);
        require(last >= 3, "baseline open failed");
        require(baseline.close(last) == 0, "baseline close failed");
    }
    require(last > 8, "baseline did not reproduce descriptor table overflow risk");
    setenv("PS2X_VFS_REUSE_DESCRIPTORS", "1", 1);
    PS2Vfs fixed;
    for (int i=0; i<20; ++i) {
        const int fd = fixed.open("host0:fixture.txt", PS2_FIO_O_RDONLY, mounts, rom);
        require(fd == 3, "serial open did not reuse its closed descriptor");
        require(fixed.close(fd) == 0, "serial close failed");
        char b = 0;
        require(fixed.read(fd, &b, 1) == -1, "closed descriptor remained readable");
    }
    const int first = fixed.open("host0:fixture.txt", PS2_FIO_O_RDONLY, mounts, rom);
    const int second = fixed.open("host0:fixture.txt", PS2_FIO_O_RDONLY, mounts, rom);
    require(first != second, "live descriptors aliased");
    require(fixed.close(first) == 0, "live first close failed");
    const int third = fixed.open("host0:fixture.txt", PS2_FIO_O_RDONLY, mounts, rom);
    require(third == first, "hole was not reused");
    char a=0, b=0;
    require(fixed.read(second, &a, 1) == 1 && a == 'A', "second live file lost its data");
    require(fixed.read(third, &b, 1) == 1 && b == 'A', "reopened file lost its data");
    require(fixed.close(second) == 0 && fixed.close(third) == 0, "final closes failed");
    std::cout << "PASS: 20 serial loads, closed-handle rejection, independent live files, hole reuse\n";
}
