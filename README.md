# Bounty Hunter native recompile experiment

Target: Galaxy S24 / Android ARM64. **Not playable; no Android APK yet.**

The PS2 EE executable has been translated to native C++ and startup executes
on x86-64 Linux with PS2Recomp's compatibility runtime and interpreted IOP.
This repository contains the experiment tooling, runtime patch and diagnostic
reports. Supply the original executable, IRX modules and game assets locally.

## Latest result — 7 October 2026

- The real `CRI_ADXI.IRX` module now registers DTX RPC service `0x7d000000`.
  Native startup passes its previous wait at `0x2579a8`.
- Streaming-audio DMA completed much too quickly and kept the priority-39
  audio worker running ahead of the priority-49 RPC thread. The opt-in
  AutoDMA completion cadence gives that RPC thread time to initialize.
- Added scratchpad normal receive through the runtime's existing DMA engine.
  Its regression verifies actual 16 KB data, wrapping and completion registers.
- The game's three EE workers were rejected because they inherit priority 0
  from the main thread. Opt-in support creates the real threads at that
  priority, as used by PS2SDK's own thread initialization.
- Latest bounded startup has four EE threads and four actual IOP RPC servers.
  It reaches another `sceSifBindRpc` retry for SID `0x80000597`, around
  `0x18afe8`/`0x18b008`. The first game frame is still blocked.
- All three new regressions pass. All four upstream IOP suites pass with
  AutoDMA timing disabled and enabled. Installers and the alternative patch
  reproduce all twelve modified runtime source files exactly.

Earlier descriptor reuse and partial DATA/BUNDLES integration remain required:
657 supplied files total 248,577,426 bytes. CHEWIE, SOUND and VIDEO are still
missing; complete disc assets are unverified.

The headless diagnostic reports zero packed graphics packets, image uploads,
recent draws and presentation frames. No visible frame, sound output,
controls, gameplay, FPS, Android binary or S24 test is established. Diagnostic
exit zero only means the bounded runner returned. AutoDMA timing is a coarse
interrupt-cadence model; it does not implement SPU2 audio output or prove full
hardware accuracy. Other DMA receive channels remain unimplemented.

## Reproduce

Use Linux, Python 3, CMake, Clang 18, and normal raylib X11/OpenGL development
headers. The checked-in reports record the current mixed GCC/Clang desktop
build; Clang is preferable for fresh builds because several generated
functions are unusually large.

1. Place `SLUS_204.20`, `SYSTEM.CNF`, `CDROM.TXT`, `IOPRP254.IMG` and `IRX.zip`
   in `original/`. Keep the separately supplied DATA.zip and BUNDLES.zip local.
2. Clone [PS2Recomp](https://github.com/ran-j/PS2Recomp) and check out
   `2c5fbb9389e11dd95693385969490c9e8e6f57b4`.
3. Build its analyzer/recompiler, extract modules, and regenerate translation:

```sh
cmake -S /path/to/PS2Recomp -B /path/to/PS2Recomp/build-tools -DPS2X_BUILD_RUNTIME=OFF -DPS2X_BUILD_TEST=OFF -DPS2X_BUILD_STUDIO=OFF
cmake --build /path/to/PS2Recomp/build-tools -j3
python3 inspect_irx.py original/IRX.zip game-irx
python3 inspect_iop_image.py original/IOPRP254.IMG --extract-to iop-system-modules --output iop-inventory.json
python3 reproduce_corrected.py /path/to/PS2Recomp
python3 stage_runtime.py /path/to/PS2Recomp --generated corrected-output --compact-registration
python3 install_memcpy_probe.py /path/to/PS2Recomp
python3 install_vfs_probe.py /path/to/PS2Recomp
python3 install_boot_sifcmd_probe.py /path/to/PS2Recomp
python3 install_iop_snapshot_probe.py /path/to/PS2Recomp
python3 install_iop_execution_probe.py /path/to/PS2Recomp
python3 install_iop_import_trace.py /path/to/PS2Recomp
python3 install_spu2_adma_timing.py /path/to/PS2Recomp
python3 install_scratchpad_receive.py /path/to/PS2Recomp
python3 install_ee_thread_probe.py /path/to/PS2Recomp
python3 install_ee_zero_priority.py /path/to/PS2Recomp
python3 verify_runtime_probes.py /path/to/PS2Recomp
python3 stage_assets.py --data /path/to/DATA.zip --bundles /path/to/BUNDLES.zip --disc /path/to/disc
```

4. Configure a fresh desktop runtime build. These x86 SIMD flags are not
   Android build flags:

```sh
cmake -S /path/to/PS2Recomp -B /path/to/runtime-build -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_FLAGS_DEBUG="-O0 -msse4.1 -mavx2" -DPS2X_BUILD_RECOMP=OFF -DPS2X_BUILD_ANALYZER=OFF -DPS2X_BUILD_TEST=OFF -DPS2X_BUILD_STUDIO=OFF -DPS2X_ENABLE_DEBUG_UI=OFF -DPS2X_ENABLE_FFMPEG=OFF -DPS2X_ENABLE_AGRESSIVE_LOGS=OFF -DPS2X_ENABLE_IOP_RPC_TRACE=OFF
cmake --build /path/to/runtime-build --target ps2EntryRunner -j3
python3 link_headless.py /path/to/PS2Recomp /path/to/runtime-build
python3 run_startup.py --runner ./headless-startup --disc /path/to/disc --report latest.json --reuse-file-descriptors --stop-invalid-copy --trace-files --boot-sifcmd --inspect-iop --trace-iop-imports --adma-timing --scratchpad-receive --trace-ee-threads --allow-zero-priority
```

Omit `--reuse-file-descriptors` to reproduce the original invalid-copy failure.
Omit `--adma-timing` to reproduce the DTX wait after descriptor reuse; with
cadence alone, startup stops at the former `sceDmaRecvN` stub. SIFCMD execution
is a partial boot probe. Trace flags only add diagnostics. Each compatibility
change defaults off. RPC servers register through actual supplied IRX code.
The original executable remains unchanged. `runtime-experiment.patch` is an alternative
to the installers; apply one route, not both.

For an interrupted GCC build, `compile_large_unit.py BUILD --compiler
/path/to/clang++ --repair-incomplete` repairs missing or empty unity objects.
It does not produce an Android binary. Finish the CMake build before linking.

## Evidence and next work

See `dtx-investigation-result.json`, `dtx-final-baseline.json`,
`dtx-final-cadence-only.json`, `dtx-ee-thread-startup-result.json`, and
`dtx-priority-startup-result.json`. The `dtx-*-tests.log` files retain checks;
`probe-installation-check.json` records reproducibility and source hashes.
Earlier asset and invalid-copy evidence remains available.

Next: trace the RPC bind for `0x80000597` and boot the required real IOP
system service, then retry startup with graphics counters enabled. Faithful
IOP boot, audio hardware, asset completeness and visible rendering still need
work before an Android SDK/NDK build and actual S24 testing.

Primary implementation references used in this investigation:

- [PS2SDK LIBSD block DMA](https://github.com/ps2dev/ps2sdk/blob/master/iop/sound/libsd/src/block.c)
- [PCSX2 SPU2 DMA](https://github.com/PCSX2/pcsx2/blob/master/pcsx2/SPU2/Dma.cpp)
- [PS2SDK priority-zero thread creation](https://github.com/ps2dev/ps2sdk/blob/master/ee/kernel/src/thread.c)
- [Play! EE thread creation](https://github.com/jpd002/Play-/blob/master/Source/ee/PS2OS.cpp)
- [PS2SDK SIFCMD startup](https://github.com/ps2dev/ps2sdk/blob/master/iop/system/sifcmd/src/sifcmd.c)

Upstream PS2Recomp's license is included in `PS2Recomp-LICENSE.txt`.
