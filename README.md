# Bounty Hunter native recompile experiment

Target: Galaxy S24 / Android ARM64. **Not playable; no Android APK yet.**

The PS2 EE executable has been translated to native C++ and startup executes
on x86-64 Linux with PS2Recomp's compatibility runtime and interpreted IOP.
This repository contains the experiment tooling, runtime patch and diagnostic
reports. Supply the original executable, IRX modules and game assets locally.

## Latest result — 7 October 2026

- **First real game frame captured:** a 640×446 Bounty Hunter logo/background
  with copyright text, visibly tiled and distorted. Two 60-second runs reproduce
  the result. This is not a verified correct title screen or Android build.
- Fixed the runner's capture gate: GS history defaults to paused and must be
  enabled before counting actual draws. The latest capture has 456 recent Draw
  events; zero specialized fast-path counters did not imply zero GS work.
- Added opt-in scheduler-cycle COP0 Count accounting with shared thread/IRQ
  state, guest-write preservation and 32-bit wrap. The regression passes.
  See `boot-screen-result.json` and `boot-screen-layout-60s.json`. Game pixels
  are retained in the private project checkpoint and separate preview image.

Previous completed startup fixes and asset integration:

- The supplied `CDVDFSV.IRX` now boots after SIFCMD and registers the real
  disc-search RPC service `0x80000597`. DTX remains registered. Native startup
  starts with nine actual RPC services and seven real loaded modules; the
  60-second run later loads memory-card modules too.
- Added opt-in support for its two missing CDVD imports: a real shared read
  buffer and layer-zero file lookup through the existing host-backed ISO.
  Files that are absent still fail; other disc layers remain unsupported.
- RPC callback stacks overlapped the main thread's top-of-RAM stack. Separately
  allocated callback stacks preserve its saved return address and let startup
  continue beyond the previous PC-zero failure.
- Four observed code entries now have exact native translations or entry labels
  exposed in existing translated instruction bodies. Every instruction is
  checked against the unchanged supplied ELF; no game instructions are patched.
- Startup reaches main-menu assets: `FECOMMON.ZAP`, `FESTART.ZAP`, `STARTUP.BIN`,
  `MM_ANI_2.VFX` and `MM_ANI_4.VFX`. These loaded assets precede the new distorted logo capture.
- CDVD file/sector, callback-stack and native-leaf regressions pass. All four
  upstream IOP suites pass with the new imports disabled and enabled.
  Installers and the alternative patch reproduce sixteen runtime files exactly.

The supplied DATA/BUNDLES/CHEWIE contains 661 files totaling 249,121,369 bytes.
CHEWIE.zip passes CRC validation and adds all four supplied files (543,943 bytes).
A 20-second post-staging smoke test opens `CS1014A.SYM`, `CS1014A.CSP` and
`FECOMMON.ZAP` without an exception; it captures no frame. See
`chewie-integration-result.json` and `chewie-startup-result.json`. The prior CDVD 60-second
result predates this asset addition; new boot-screen runs include CHEWIE.
`DATA/VIDEO/01TRAILR.SFD` is requested and missing; the game proceeds to the
front end with the current fixes. SOUND and VIDEO remain incomplete.
Missing assets may cause later failures, and full-disc completeness is unverified.

Correct title-screen rendering, sound output, controls, gameplay, FPS, Android
binaries and S24 testing remain unverified. Diagnostic exit zero only means the bounded runner
returned. AutoDMA timing remains a coarse interrupt-cadence model; it does not
implement SPU2 audio output or prove full hardware accuracy. CDVDFSV boot is
still a partial IOP boot, and other DMA receive channels remain unimplemented.

## Reproduce

Use Linux, Python 3, CMake, Clang 18, and normal raylib X11/OpenGL development
headers. The checked-in reports record the current mixed GCC/Clang desktop
build; Clang is preferable for fresh builds because several generated
functions are unusually large.

1. Place `SLUS_204.20`, `SYSTEM.CNF`, `CDROM.TXT`, `IOPRP254.IMG` and `IRX.zip`
   in `original/`. Keep the separately supplied DATA.zip, BUNDLES.zip and CHEWIE.zip local.
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
python3 install_boot_cdvdfsv_probe.py /path/to/PS2Recomp
python3 install_cdvd_imports.py /path/to/PS2Recomp
python3 install_ee_exit_probe.py /path/to/PS2Recomp
python3 install_ee_return_probe.py /path/to/PS2Recomp
python3 install_callback_heap_stacks.py /path/to/PS2Recomp
python3 install_cop0_count.py /path/to/PS2Recomp
python3 install_boot_graphics_trace.py /path/to/PS2Recomp
python3 install_graphics_dma_trace.py /path/to/PS2Recomp
python3 verify_runtime_probes.py /path/to/PS2Recomp
python3 stage_assets.py --data /path/to/DATA.zip --bundles /path/to/BUNDLES.zip --extra-assets /path/to/CHEWIE.zip --disc /path/to/disc
```

Repeat `--extra-assets` for additional SOUND or VIDEO ZIP batches. The staging
tool preserves their disc-relative paths and rejects differing existing files.

4. Configure a fresh desktop runtime build. These x86 SIMD flags are not
   Android build flags:

```sh
cmake -S /path/to/PS2Recomp -B /path/to/runtime-build -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_FLAGS_DEBUG="-O0 -msse4.1 -mavx2" -DPS2X_BUILD_RECOMP=OFF -DPS2X_BUILD_ANALYZER=OFF -DPS2X_BUILD_TEST=OFF -DPS2X_BUILD_STUDIO=OFF -DPS2X_ENABLE_DEBUG_UI=OFF -DPS2X_ENABLE_FFMPEG=OFF -DPS2X_ENABLE_AGRESSIVE_LOGS=OFF -DPS2X_ENABLE_IOP_RPC_TRACE=OFF
cmake --build /path/to/runtime-build --target ps2EntryRunner -j3
python3 generate_leaf_entries.py original/SLUS_204.20 --entry 0x265780 --entry 0x29e7f0 --entry 0x301fa0 --entry 0x31b980 --generated-directory corrected-output
python3 link_headless.py /path/to/PS2Recomp /path/to/runtime-build --leaf-entries leaf-output/observed_leaf_entries.cpp
python3 run_startup.py --runner ./headless-startup --disc /path/to/disc --report latest.json --reuse-file-descriptors --stop-invalid-copy --trace-files --boot-sifcmd --inspect-iop --trace-iop-imports --adma-timing --scratchpad-receive --trace-ee-threads --allow-zero-priority --boot-cdvdfsv --cdvd-compat --separate-callback-stacks --advance-cop0-count --trace-boot-graphics --seconds 60 --capture-frame first-game-frame.ppm
```

Omit `--reuse-file-descriptors` to reproduce the original invalid-copy failure.
Omit `--adma-timing` to reproduce the DTX wait after descriptor reuse; with
cadence alone, startup stops at the former `sceDmaRecvN` stub. SIFCMD execution
is a partial boot probe. CDVDFSV runs supplied IRX code and requires the SIFCMD probe. Trace flags only add diagnostics. Each compatibility
change defaults off. RPC servers register through actual supplied IRX code.
The original executable remains unchanged. Frame capture writes only after real draw activity; it does not generate a placeholder image. `runtime-experiment.patch` is an alternative
to the installers; apply one route, not both.

For an interrupted GCC build, `compile_large_unit.py BUILD --compiler
/path/to/clang++ --repair-incomplete` repairs missing or empty unity objects.
It does not produce an Android binary. Finish the CMake build before linking.

## Evidence and next work

See `cdvd-investigation-result.json`, `cdvd-startup-result.json`,
`cdvd-final-startup-result.json`, `cdvd-callback-startup-result.json`,
`cdvd-long-startup-result.json`, `cdvd-third-entry-result.json`, and the latest
`cdvd-front-end-60s.json`. `observed-leaf-entries.json` records exact observed entry
translation and source hashes. Earlier DTX and asset evidence is retained.

`cdvd-regression.log`, `cdvd-callback-regression.log`,
`cdvd-leaf-regression.log`, the IOP suite logs, and
`probe-installation-check.json` retain validation. Generated game C++, raw
memory captures, original modules/assets and large native binaries remain local.

The previous zero-draw reports used paused GS debug history. That counter could
not establish absence of drawing. Likewise, `packed_packets` and `image_uploads`
count specialized fast paths, and `gs_writes` covers a direct IO-write path;
zero values do not establish absence of generic GIF processing or GS setup.
The new runner enables GS history before startup and captures only after it
observes actual Draw events. No placeholder or synthetic game image is used.

`--advance-cop0-count` advances the hardware counter from existing scheduler
cycle charges, shares it across threads and interrupt contexts, and preserves
native guest writes and 32-bit wrap. It defaults off. Charges remain coarse;
this does not implement instruction-accurate timing or COP0 Compare interrupts.
Read-only graphics traces show original game calls, DMA/VIF metadata, decoded
GIF tags and draw-state metadata. They do not alter or replay game packets.
The first preliminary clock report used incorrect graphics-buffer addresses;
the shared-clock and later reports use the corrected original addresses.

Next: correct the tiled/distorted logo and text in the real captured frame,
then validate the opening screen sequence, missing assets, audio and controller
input before an Android SDK/NDK build and S24 testing.

Primary implementation references:

- [PS2SDK CDVD RPC identifiers](https://github.com/ps2dev/ps2sdk/blob/master/ee/rpc/cdvd/src/libcdvd.c)
- [PS2SDK CDVD import numbers](https://github.com/ps2dev/ps2sdk/blob/master/iop/cdvd/cdvdman/include/cdvdman.h)
- [PS2SDK CDVD read buffer](https://github.com/ps2dev/ps2sdk/blob/master/iop/cdvd/cdvdman/src/cdvdman.c)
- [PS2SDK LIBSD block DMA](https://github.com/ps2dev/ps2sdk/blob/master/iop/sound/libsd/src/block.c)
- [PCSX2 SPU2 DMA](https://github.com/PCSX2/pcsx2/blob/master/pcsx2/SPU2/Dma.cpp)
- [PS2SDK priority-zero thread creation](https://github.com/ps2dev/ps2sdk/blob/master/ee/kernel/src/thread.c)
- [PS2SDK SIFCMD startup](https://github.com/ps2dev/ps2sdk/blob/master/iop/system/sifcmd/src/sifcmd.c)

Upstream PS2Recomp's license is included in `PS2Recomp-LICENSE.txt`.

- [PCSX2 EE COP0 Count cycle accounting](https://github.com/PCSX2/pcsx2/blob/master/pcsx2/R5900.cpp)
