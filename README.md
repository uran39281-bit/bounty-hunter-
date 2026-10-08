# Bounty Hunter native recompile experiment

Target: Galaxy S24 / Android ARM64. **The user confirms game import and boot to
the original main menu on their phone. Advancing from PLAY GAME is blocked; full gameplay
remains unverified.**

The PS2 EE executable has been translated to native C++ and startup executes
on x86-64 Linux with PS2Recomp's compatibility runtime and interpreted IOP.
This repository contains the experiment tooling, runtime patch and diagnostic
reports. Supply the original executable, IRX modules and game assets locally.

## Latest result — 8 October 2026

- APK 4's new phone log identifies the stable guest PC `0x196bd8` inside
  LOADFILE initialization. It retries SIF RPC SID `0x80000006`, stops sampling
  the pad at read 297 for at least 110.986 seconds, and submits no new DMA/GIF
  work while the host continues redrawing. The boot sequence omitted LOADFILE.
  A local test reproduces the absent service with SIFCMD/CDVDFSV alone; executing
  the original LOADFILE IRX registers the service and answers its version RPC.
  APK 5, `Bounty-Hunter-Startup-Fix.apk`, loads that original module at IOP reset
  and prepares it automatically on existing imports. Its phone effect is unverified.
  See `phone-menu-stall-apk4-analysis.json` and `loadfile-boot-regression.json`.
- The APK 4 inventory also confirms SOUND and VIDEO were not imported.
  Failed sound opens are observed; their effect beyond the diagnosed LOADFILE
  loop remains unestablished. Original game code and menu state are unchanged in APK 5.
- APK 3's exported phone log confirms Start and two X presses are consumed.
  Pad reads then slow sharply and stop at 318 for at least 50.843 seconds;
  later Down/Circle transitions stay queued. The capture has no missing-target
  or fatal guest-exception message. The blocked game PC is not exposed by APK 3.
  See `phone-menu-stall-log-analysis.json`; APK 4 later locates the LOADFILE retry.
- APK 4 adds an independent native watcher for branch/render progress and the
  scheduler's published EE thread/wait snapshots, plus asset-open failures and
  imported DATA folder counts. It also corrects one generated VCALLMSR operand;
  the other 7,944 generated sources and original ELF instructions stay unchanged.
  The private native object cache allows future runtime edits to reuse the
  compiled game. The actual corrected wrapper passes 1,536 address/return cases,
  while the baseline reproduces the vi[27] bounds failure. This confirms the
  translation defect; its role in the phone stall remains unverified. See
  `vcallmsr-translation-test.json` and `vcallmsr-translation-fix.json`.
- APK version 2 gets past the save warning and displays the original main menu.
  The latest screenshot shows PLAY GAME selected and `Touch: X | Game: waiting`.
  The touch was detected; the guest has not consumed that queued press. The
  reason is not yet established without the phone runtime log.
- APK version 3 adds **Export logs** to the independent Android controls. It
  records only its own process log and touch/pad counters in a bounded buffer.
  The phone document picker saves a text report without a computer. The native
  runtime is byte-identical to APK 2; this is a diagnostic update, not a game fix.
  Java/DEX compilation, same-certificate signing, native entry and 16 KB alignment
  checks pass. The user successfully exported the APK 3 phone log. See `PHONE-INSTALL.md` and
  `android-phone-diagnostics-verification.json`.
- The first APK reaches the readable original save warning on the user's S24.
  The user reports that Up, Down and Cross do not respond. See
  `phone-device-observation.json`; this confirms import/boot, not full gameplay.
- A candidate input update queues Android press/release events until an actual
  primary guest pad read consumes them. It preserves fast taps and draws/tests
  controls in one Java view, with `Game: received` or `waiting` feedback. Host
  tests pass for quick/repeated taps, held input, multi-touch, cancellation,
  bounded overflow and concurrent threads. The user now reaches the main menu; delivery there remains blocked.
- Built and signed APK version 2 with the same certificate as version 1.
  Static verification passes for the Java NativeActivity subclass, independent
  popup controls, all three touch JNI methods, launcher, ARM64 library and
  16 KB ELF/ZIP alignment. All 7,945 staged generated game sources retain their
  verified hashes. APK 3 retains this native runtime and adds phone diagnostics.
- Fixed a graphics upload boundary bug: a pending GIF IMAGE previously consumed
  the next VIF NOP/DIRECT commands as pixels. Continuations now consume only
  bytes inside explicit DIRECT/DIRECTHL payloads. Pixel bytes remain untouched.
- The regression reproduces the defect on the old runtime and passes with the
  fix: one stream, separate calls, multiple chunks, DIRECTHL, a partial initial
  image, a full single packet, MARK and a following GS register packet.
- Replaying an unchanged captured game upload now matches every palette entry
  and all 65,536 texture indices. Before the fix, 256 palette entries and 7,469
  texture indices differed. No original game instructions or menu flags changed.
- An isolated original copyright draw packet is readable with the original atlas;
  direct GS and VIF submissions produce identical pixels. This isolates the draw
  path; normal asset loading and full-screen correctness require native capture.
- The separate diagnostic archive now optimizes nine host runtime units,
  including VIF and the vector interpreter, at `-O2` without fast-math. Original
  generated game objects and the baseline runtime archive remain unchanged.
- A fixed 360-second native run renders a readable original save warning,
  coherent border/background and YES/NO controls. Cross opens the warning;
  Down selects No. No missing-target stop or reserved VU instructions occur.
  The previous comparable run had 57 reserved VU instruction reports.
  See `menu-rendering-result.json`. Full-game and S24 validation remain open.
- The fixed 480-second run delivers all four directions after the title;
  Up changes the visible No selection to Yes. Both fixed runs reach their
  deadlines without missing-target stops or reserved VU instructions.
- An isolated original-handler regression restores the captured No selection
  for each of seven buttons. Up/Down toggle it to Yes; Cross requests original
  screen `0x4f`; Left/Right/Circle/Start leave this warning's state unchanged.
  The subsequent screen and on-device touch behavior are not validated.
- Built the actual ARM64 Android APK with NDK 28.2.13676358, SDK 34, AGP
  8.6.1 and Gradle 8.9. All 7,945 corrected game/observed-entry C++ files
  compile and link with `-O2 -g0`, without fast-math. The APK is debug signed.
- APK verification passes: signature, ARM64-only ELF, exported NativeActivity
  entry, game-folder launcher and 16 KB ELF/ZIP native-library alignment.
- Added a phone folder picker. It checks the original executable and IOP image,
  copies original disc files, and prepares the two startup modules automatically.
  Host extraction checks reproduce the existing module files byte for byte and
  reject missing/wrong images. The user now confirms device import and launch.
- Earlier native compilation reported a VCALLMSR array-bounds warning. APK 4
  corrects that operand to CMSAR0; the link between this defect and the phone
  stall still needs a device test. Full gameplay remains unverified.
- See `android-apk-build.json`, `android-apk-verification.json` and
  `PHONE-INSTALL.md`. Original game files, generated C++, APK and signing key
  remain private; public GitHub contains the authored tooling and reports.

## Previous title/menu milestone

- The original title timer works: a longer native run advances from screen
  `0x10f` to `0x110` at 5.009 seconds. Cross then requests screen `0x35e`.
  Earlier shorter runs did not establish that the transition was broken.
- The first transition stops at an unregistered original entry `0x2df460`.
  Registering its verified existing native body passes memory-card slot tests
  and moves execution to missing callback `0x3265d0`. Its registration passes
  all four eligibility flag cases. The next run reaches an animation update
  at `0x1c4a80`; its verified original body is now registered too. Seven exact
  native entries are staged, without editing original instructions or forcing
  menu flags. See `observed-leaf-entries.json` and `title-result.json`.
- A 300-second run with all seven entries reaches screen `0x35e`, renders
  its animation and reaches the deadline without a missing-target stop. The
  new image is distorted with duplicated/clipped elements; usable menu
  navigation and correct rendering are not established.
- Font metrics, copyright strings and original glyph calls are present.
  Copyright layout measures 336 × 18. Native glyph routines return expected
  advances at scale 0.6. The visible text failure remains in the rendering
  path; a collapsed-layout explanation was not supported by measurement.
- Added bounded native timer/glyph traces and a separate optimized host
  diagnostic archive. Only host dispatch, memory, scheduler and GS units use
  `-O2` without fast-math; original generated game objects and the baseline
  runtime archive remain untouched. This is diagnostic tooling, not an APK.
- Native timer, entry semantics and leaf checks pass. All twenty runtime files
  reproduce exactly through installers and the alternative patch. The APK
  build was still blocked at this earlier milestone by missing Gradle/SDK/NDK.
  The newer ARM64 build above resolves that tooling blocker; S24 validation remains open.

Earlier logo rendering milestone:

- **Readable title logo captured:** the native run now selects `start_01`
  through `start_05`, giving five distinct background panels instead of the
  repeated logo fragment. The 640×446 capture contains the readable Star Wars
  Bounty Hunter logo. The lower-left region remains blank; a complete opening
  sequence, menu text and correct rendering are still unverified.
- Fixed an observed argument-layout mismatch: original callers save formatting
  arguments eight bytes apart, while the runtime's `vsprintf` cursor advanced
  four bytes. The fix is opt-in (`--ee-va64`); mixed-type and opt-out regressions pass.
- Added capture after all 20 original GS display-copy strips complete
  (`--capture-on-present`), so the preview is a completed native display copy
  rather than an arbitrary point during drawing. No replacement game pixels,
  draw packets, VBlank events or native instructions are supplied.
- See `distortion-result.json`, `distortion-copy-60s.json` and
  `distortion-native-observations.json`. A separate 120-second run reaches at
  least 160 completed display copies with the same logo and no visible menu text
  (`distortion-long-120s.json`). All eighteen modified runtime files
  reproduce exactly from the pinned source through installers or the patch.
  Game pixels and RAM/VRAM comparisons remain in the private checkpoint.

Earlier real boot captures contained tiled/distorted logo fragments and
copyright text. Enabled GS history and the opt-in shared COP0 Count made those
captures possible; their timing and counter limitations still apply.

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
  Installers and the alternative patch now reproduce eighteen runtime files exactly.

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
python3 install_frontend_trace.py /path/to/PS2Recomp
python3 install_graphics_dma_trace.py /path/to/PS2Recomp
python3 install_gs_batch_trace.py /path/to/PS2Recomp
python3 install_gs_vertex_trace.py /path/to/PS2Recomp
python3 install_vif_image_continuation.py /path/to/PS2Recomp
python3 install_ee_valist.py /path/to/PS2Recomp
python3 install_present_capture.py /path/to/PS2Recomp
python3 install_android_touch.py /path/to/PS2Recomp
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
python3 generate_leaf_entries.py original/SLUS_204.20 --entry 0x265780 --entry 0x29e7f0 --entry 0x301fa0 --entry 0x31b980 --entry 0x2df460 --entry 0x3265d0 --entry 0x1c4a80 --generated-directory corrected-output
python3 link_headless.py /path/to/PS2Recomp /path/to/runtime-build --leaf-entries leaf-output/observed_leaf_entries.cpp
python3 run_startup.py --runner ./headless-startup --disc /path/to/disc --report latest.json --reuse-file-descriptors --stop-invalid-copy --trace-files --boot-sifcmd --inspect-iop --trace-iop-imports --adma-timing --scratchpad-receive --trace-ee-threads --allow-zero-priority --boot-cdvdfsv --cdvd-compat --separate-callback-stacks --advance-cop0-count --trace-boot-graphics --ee-va64 --capture-on-present --seconds 60 --capture-frame first-game-frame.ppm
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

`--ee-va64` makes `vsprintf` read eight-byte argument slots, matching the
original executable's `SD` saves at `sp+0x840`, `sp+0x848` and `sp+0x850`
(and a second caller at `sp+0x430`, `sp+0x438`, `sp+0x440`). The default
four-byte cursor read an argument's upper padding as the next argument.
The opt-in cursor also reads 64-bit integers and doubles from one full slot;
the packed four-byte mode remains available. `test_ee_valist.cpp` checks both
layouts, numbered names, signed values, strings, 64-bit values and doubles.
Actual native format traces request `start_01` through `start_05` with the fix.

`--capture-on-present` latches only after all 20 observed native GS display-copy
strips complete, copying the original rendered surface to the display. It
checks their original geometry and source coordinates; it neither draws
additional pixels nor advances VBlank. A direct native-return hook was tested
and did not fire because this generated build returns without the strict
return-dispatch macro. `distortion-present-60s.json` records that failed
capture experiment. The final installer observes the actual GS copy instead.
Deadline captures without this flag can show a partially drawn frame.
The runner accepts bounded runs of 1–600 seconds; the default remains five.
With graphics tracing enabled, `.ctx0.ppm` and `.ctx1.ppm` are actual offscreen
surfaces for diagnosis, not CRT captures. Add `--dump-graphics-memory` explicitly
to retain private RAM/VRAM diagnostics; these and game pixels stay out of GitHub.

Next: determine how the original front end draws text and input prompts,
validate the opening screen sequence, and continue missing assets/audio/input
work before an Android SDK/NDK build and S24 testing.

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
