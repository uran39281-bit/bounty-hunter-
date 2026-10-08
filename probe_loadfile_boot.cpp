#include "iop_compat_test_support.h"
#include <fstream>
#include <iterator>
#include <filesystem>

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    using namespace ps2x::iop;
    iop_test::Host host(0x2000000u);
    IopSubsystem iop(host);
    auto load = [&](const char* name) {
        std::ifstream f(std::filesystem::path(argv[1]) / name, std::ios::binary);
        host.file.assign(std::istreambuf_iterator<char>(f), {});
        const auto r = iop.loadModule(std::string("host:") + name);
        std::cout << name << " id=" << r.moduleId << " start=" << r.startResult << '\n';
        iop_test::require(r.moduleId > 0, "load failed");
    };
    iop_test::require(!iop.canBindRpc(0x80000006u), "LOADFILE unexpectedly ready before load");
    load("SIFCMD.irx");
    load("CDVDFSV.irx");
    iop.runEeCycles(1000000u);
    iop_test::require(!iop.canBindRpc(0x80000006u), "APK 4 boot order unexpectedly supplies LOADFILE");
    load("LOADFILE.irx");
    iop.runEeCycles(1000000u);
    std::cout << "canBind=" << iop.canBindRpc(0x80000006u) << '\n';
    iop_test::require(iop.canBindRpc(0x80000006u), "original LOADFILE did not register service");
    auto req = iop_test::request(0x80000006u, 0xffu, 4u);
    req.receive.address=0x10000u;
    const auto r=iop.handleRpc(req);
    std::cout << "version_handled=" << r.handled << " version=" << std::hex << host.word(0x10000u) << '\n';
    for (const auto& line:host.logs) std::cout << line << '\n';
    iop_test::require(r.handled, "version RPC not handled");
    iop_test::require(host.word(0x10000u) == 0x30343532u, "original LOADFILE version reply differs from 2540");
    iop.reset();
    iop_test::require(!iop.canBindRpc(0x80000006u), "reset retained stale service");
    load("SIFCMD.irx");load("CDVDFSV.irx");load("LOADFILE.irx");
    iop.runEeCycles(1000000u);
    iop_test::require(iop.canBindRpc(0x80000006u), "service unavailable after second boot");
    host.fill(0x10000u,4u);
    iop_test::require(iop.handleRpc(req).handled, "second version RPC failed");
    iop_test::require(host.word(0x10000u)==0x30343532u, "second version response changed");
    std::cout << "PASS missing-service reproduction, original IRX startup, version RPC, reset and reload\n";
}
