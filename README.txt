TITLE TRANSITION WORK — 8 October 2026
The original five-second timer advances screen 0x10f to 0x110. Cross then
requests screen 0x35e. Registered verified original entries for memory-card
slots, menu eligibility and animation; native slot/eligibility tests pass.
A 300-second seven-entry run renders the following screen without a missing
function stop. Its graphics and text fragments are distorted; menu rendering
and navigation are not yet correct. Font metrics and glyph calls exist.
All twenty runtime changes reproduce through installers and patch.
Android build remains blocked by absent SDK/NDK/Gradle tools; no APK or S24 test.
See title-result.json, ANDROID.md and README.md for current evidence.
The following records describe historical checkpoints.

MENU INPUT WORK — 7 October 2026
Added Android menu touch controls, physical-controller merge, native event
traces and private native-entry staging. Host Pad press/release tests pass.
Two 300-second native runs still show the logo without menu text; scripted
buttons reach the Pad API but usable menu navigation is not established.
Twenty runtime files reproduce exactly through installers and patch.
The APK build is blocked by missing Gradle, SDK/NDK and SDK CMake. No APK or
S24 validation. See frontend-result.json, ANDROID.md and README.md.
The following notes describe historical checkpoints.

LOGO FORMAT FIX — 7 October 2026
The native run now formats start_01 through start_05 correctly. Its completed
640x446 display copy contains a readable Star Wars Bounty Hunter title logo.
The lower-left region is blank and menu/copyright text is not visible; the
complete opening sequence and rendering correctness remain unverified.
Added opt-in eight-byte va_list slots and full native display-copy capture.
The mixed-type/opt-out regression and eighteen-file installer/patch reproduction
pass. See distortion-result.json and README.md for current reproduction.
No Android APK, sound/controller validation or S24 test.
The following notes describe historical checkpoints.

BOOT-SCREEN CAPTURE — 7 October 2026
First actual game pixels captured: 640x446 Bounty Hunter logo/background and
copyright text. Two 60-second runs reproduce a tiled, clipped and distorted
image. The correct full title/boot sequence remains unverified. No Android APK,
audio/control validation or S24 test. Enabled paused GS history for real draw
capture; added opt-in shared COP0 Count and read-only graphics diagnostics.
COP0 regression and sixteen-file installer/patch reproduction pass.
See boot-screen-result.json, boot-screen-layout-60s.json and README.md.
The following records are historical and their zero-draw counters were not
reliable absence-of-rendering evidence because GS history was paused.

CHEWIE asset update — 7 October 2026
Validated and staged all four CHEWIE files (543,943 bytes). Combined assets:
661 files, 249,121,369 bytes. SOUND and VIDEO remain missing. A 20-second smoke test
opens CS1014A.SYM, CS1014A.CSP and FECOMMON.ZAP with no exception; no visible
frame or Android APK. The prior 60-second result remains historical evidence.

LATEST CHECKPOINT — 7 October 2026
CDVD SearchFile RPC 0x80000597 now registers through supplied CDVDFSV code.
Implemented actual FSV read buffer/layer-zero search and separated callback
stacks from the main thread stack. Four observed code entries now translate
exactly or expose existing native instructions. The 60-second run loads menu
bundles and reaches render routines, but records no draws or visible frame.
No Android APK or S24 test. See README.md and cdvd-investigation-result.json.
The notes below retain historical checkpoints and resolved blockers.

LATEST CHECKPOINT — 7 October 2026
DTX RPC registration now passes using actual CRI_ADXI execution. Added opt-in
SPU2 AutoDMA completion cadence, actual scratchpad DMA receive, and priority-0
EE worker creation. Latest startup: four EE threads, four RPC services; next
wait is sceSifBindRpc SID 0x80000597. No game frame, audio output or Android APK.
All new regressions and upstream IOP suites pass. See README.md for current
reproduction, flags, limitations and evidence. The following notes retain
historical experiments and may describe blockers now resolved.

STAR WARS: BOUNTY HUNTER - NATIVE CODE EXPERIMENT
Date: 7 October 2026
Requested target: Galaxy S24 / Android ARM64
Status: native EE startup executed on x86-64 Linux; NOT a playable Android port.

LATEST RESULT
BUNDLES.zip is integrated at DATA/BUNDLES: 84 files, 218,929,584 bytes.
Together with the earlier DATA.zip, 657 files totaling 248,577,426 bytes are
staged. All archive entries passed CRC checks and SHA-256 inventories are
included. CHEWIE, SOUND and VIDEO remain missing; full disc completeness is
not verified. Asset bytes remain in the separately supplied archives.

The invalid memcpy has been isolated to the runtime's monotonically increasing
file descriptors. Closed handles were not reused. The game's buffered-file
layer indexes a fixed static buffer table using a handle derived from the
returned descriptor. The baseline trace progresses from fd 3 through fd 10,
then reaches memcpy with source 0xdd84c010 and size 0x8f0e8e40 at return PC
0x1dea64. A pre-copy trap preserves the original failure before the upstream
clamp can corrupt RAM. precopy-analysis.json records the caller/registers.

With lowest-free descriptor reuse enabled, repeated file loads use fd 3, all
four font families and TEXTDATA load, and the invalid-copy trap is not hit.
Startup reaches the existing DTX bind retry at PC 0x2579a8, service
0x7d000000. Five physical IRX modules load; the EE root remains runnable
with a valid stack rather than becoming dormant at PC zero.

An optional probe executes the supplied IOPRP254 SIFCMD module after reset.
It returns start=0 and removes LIBSD's uninitialized-SIF warning. The read-only
IOP snapshot confirms SIF initialized and six physical modules loaded, but
DTX's SID is absent from the three registered RPC services. This is a partial
boot experiment, not a faithful IOP reboot or a solution to the audio wait.

The VFS regression passes 20 serial loads, rejection of closed handles,
independent live files and hole reuse. All four upstream IOP suites pass with
snapshot diagnostics disabled by default. All eight modified runtime sources
are reproduced exactly by the included installers against the pinned commit.
Current evidence is in headless-vfs-baseline-result.json,
headless-vfs-reuse-result.json and headless-iop-snapshot-result.json.

The runtime is now patched through the included opt-in experiment installers;
earlier README statements about an unmodified runtime described old runs.
No service binding is forced and no synthetic VBlank events are added.
No menu, rendered frame, audio output, controls, gameplay, Android APK or S24
execution is verified. Cycle/instruction counts are diagnostics, not FPS.
A diagnostic exit code zero does not mean successful game startup.

INPUTS AND IOP CHECKS
original/ contains all supplied inputs without modification: SLUS_204.20,
SYSTEM.CNF, CDROM.TXT, IOPRP254.IMG and IRX.zip. Their SHA-256 hashes appear
in experiment.json. The executable is ELF32 little-endian MIPS/R5900,
2,893,840 bytes, entry 0x100008, without usable symbols or debug sections.
SYSTEM.CNF names SLUS_204.20, version 1.02, NTSC.

IRX.zip passed CRC validation and contains 17 MIPS ELF modules. The actual
upstream IOP loader accepted and reported complete relocations for all 17.
All four upstream IOP test executables passed. Isolated entry probes executed
each module in a fresh IOP interpreter. Four isolated modules had unhandled
imports and USBD returned start result 1; these probes do not establish full
boot dependencies, hardware behavior or game compatibility. game-irx/ and
irx-inventory.json preserve the extracted bytes and inventory.

IOPRP254.IMG contains 15 system modules extracted into iop-system-modules/.
Its ROMDIR ranges and ELF structures were checked. The image has not been
integrated into a faithful reboot sequence: upstream reset handlers reset
the IOP transport. CDROM.TXT is a 58-byte marker, not a disc file listing.

TRANSLATION CHANGES AND EVIDENCE
PS2Recomp is pinned to commit 2c5fbb9389e11dd95693385969490c9e8e6f57b4.
The first automatic scan interpreted data as instructions and reported 7,362
unsupported-instruction events. A historical analysis copy limited the main
code region to 0x100000..0x359880. Actual native execution later exposed
missing constructor code at 0x3a6be0; the single-code-region assumption was
incomplete despite zero unsupported instructions in that earlier translation.

The corrected analysis ELF additionally marks constructor code at
0x3a6be0..0x3b5b50, guided by 114 pointers at 0x3b5b50..0x3b5d18. Loaded
segment payload bytes and program headers remain unchanged. The original
executable is never patched or replaced for execution. Constructor-only
analysis changes its entry solely for discovery; that analysis copy is not booted.

prepare_corrected_config.py supplies 617 candidate callback entry hints from
conservative instruction-pattern inspection. These are discovery hints, not
an authoritative Ghidra function map. The final translation discovered 7,930
functions, recompiled 7,755 and assigned 175 stubs, producing 7,943 generated
functions. It reported zero unsupported instructions/errors and 3,104 warnings.
Zero errors do not validate instruction semantics, indirect branches, SDK
matches, timing or runtime correctness.

compact_registration.py replaces the enormous generated initializer with an
ordered mapping array and loop, checking preservation of all 233,013 mappings.
The historical translation run did not patch upstream runtime source. Current
optional runtime changes are documented in LATEST RESULT and runtime-experiment.patch. Earlier missing constructor/callback
targets were addressed through code discovery and regeneration. Other headless
results/logs are historical attempts, including a superseded harness that added
synthetic VBlank events; consult the partial-DATA and no-DATA comparison
results described above for current behavior.

The earlier ARM64 startup object compiled with Zig 0.16.0 and sse2neon commit
92f6de174717aef09033ad21568d5bb9e5470404. This is an aarch64-linux-gnu
compile-only object, not an Android binary or proof of an ARM64 runtime.
The included small x86-64 objects are also compile-only checks.

REMAINING WORK
- Resolve the DTX audio RPC service initialization/registration barrier.
- Implement and validate the required IOP boot, audio hardware and scheduling
  behavior; loading SIFCMD alone does not reproduce the complete boot image.
- Obtain CHEWIE, SOUND and VIDEO and check actual disc paths/completeness.
  Two literal HUD text paths were not found, but they may be packaged or unused;
  direct-asset-reference-check.json is not a full required-file manifest.
- Validate real graphics, audio, controls and gameplay, then build with the
  Android SDK/NDK and test on the Galaxy S24. No Android binary is included.

CHECKPOINT CONTENTS
corrected-output/ contains current generated C++ and headers.
SLUS_204.20.corrected.elf is the analysis copy with both code regions.
experiment.json, inventories, build logs and final execution records provide
evidence and limitations. Original inputs and extracted modules are included.
Large desktop executables and build intermediates are excluded.

The historical split-output/ snapshot is deduplicated in this archive. Restore
and SHA-256-verify its 7,781 files with:
  python3 restore_baseline.py
baseline-delta/ holds the 63 files whose original baseline bytes differ;
baseline-source-manifest.json verifies the complete restored snapshot.
Constructor-only generated sources/logs are a historical intermediate.
Recorded configs contain experiment workspace paths; use regeneration helpers.

REPRODUCE CORRECTED TRANSLATION
Use Linux with git, Python, CMake 3.21+ and a C++20 compiler:
  git clone https://github.com/ran-j/PS2Recomp.git /path/to/PS2Recomp
  git -C /path/to/PS2Recomp checkout 2c5fbb9389e11dd95693385969490c9e8e6f57b4
  cmake -S /path/to/PS2Recomp -B /path/to/PS2Recomp/build-tools -DPS2X_BUILD_RUNTIME=OFF -DPS2X_BUILD_TEST=OFF -DPS2X_BUILD_STUDIO=OFF
  cmake --build /path/to/PS2Recomp/build-tools -j3
From this checkpoint directory:
  python3 reproduce_corrected.py /path/to/PS2Recomp
This verifies the original hash and pinned tool commit, recreates the analysis
ELF, re-analyzes, adds constructor/callback hints and translates. Dependencies
may be fetched by CMake. reproduce.py reproduces the older main-code-only run.

BUILD THE DESKTOP DIAGNOSTIC
Use a dedicated pinned checkout; staging copies generated files into it and
replaces its registration source. On x86-64 Linux with normal raylib X11/OpenGL
development dependencies:
  python3 stage_runtime.py /path/to/PS2Recomp --generated corrected-output --compact-registration
  cmake -S /path/to/PS2Recomp -B /path/to/runtime-build -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_FLAGS_DEBUG="-O0 -msse4.1 -mavx2" -DPS2X_BUILD_RECOMP=OFF -DPS2X_BUILD_ANALYZER=OFF -DPS2X_BUILD_TEST=OFF -DPS2X_BUILD_STUDIO=OFF -DPS2X_ENABLE_DEBUG_UI=OFF -DPS2X_ENABLE_FFMPEG=OFF -DPS2X_ENABLE_AGRESSIVE_LOGS=OFF -DPS2X_ENABLE_IOP_RPC_TRACE=OFF
  cmake --build /path/to/runtime-build --target ps2EntryRunner -j3
  python3 link_headless.py /path/to/PS2Recomp /path/to/runtime-build
  ./headless-startup /path/to/disc/SLUS_204.20
Keep original SYSTEM.CNF, IOPRP254.IMG, CDROM.TXT and an IRX/ directory of
supplied module bytes beside the original executable. DATA/ belongs there
once obtained. Supplied partial DATA assets are in the separately uploaded
DATA.zip, not duplicated in this source checkpoint. Stage and CRC/hash-check:
  python3 inspect_data.py /path/to/DATA.zip --destination /path/to/disc/DATA --report data-inventory.json
The ZIP contains ALLOCS, ICONS and IFACE at its root. A DATA/ prefix must
be supplied through --destination as above. A graphical launch could not
be evaluated here because a display server could not establish listening
sockets. Android requires its own toolchain and ARM flags; do not use these
desktop SIMD flags for an Android build. No APK is produced by these steps.

REPEAT THE IRX PROBES
  cmake -S /path/to/PS2Recomp/ps2xIOP -B /path/to/iop-build -DPS2X_IOP_BUILD_TESTS=ON
  cmake --build /path/to/iop-build -j4
  ctest --test-dir /path/to/iop-build --output-on-failure
  g++ -std=c++20 -O2 -I /path/to/PS2Recomp/ps2xIOP/include -I /path/to/PS2Recomp/ps2xIOP/src -I /path/to/PS2Recomp/ps2xIOP/tests probe_irx.cpp /path/to/iop-build/libps2_iop.a -o probe-irx
  python3 run_irx_probes.py ./probe-irx
The probe uses an upstream test host; it is a diagnostic, not a port.

UPSTREAM SOURCES
https://github.com/ran-j/PS2Recomp
https://github.com/DLTcollab/sse2neon
https://github.com/ran-j/PS2Recomp/tree/main/android
PS2Recomp-LICENSE.txt is included. Compiler/runtime and other dependencies
remain external; this archive does not replace their source or licenses.

REPRODUCE THE LATEST ASSET/FILE-HANDLE CHECKPOINT
After corrected translation has been regenerated and staged (steps above),
apply installers to a dedicated pinned PS2Recomp checkout before compiling:
  python3 install_memcpy_probe.py /path/to/PS2Recomp
  python3 install_vfs_probe.py /path/to/PS2Recomp
  python3 install_boot_sifcmd_probe.py /path/to/PS2Recomp
  python3 install_iop_snapshot_probe.py /path/to/PS2Recomp
Stage original inputs, supplied modules and both uploaded archives:
  python3 stage_assets.py --data /path/to/DATA.zip --bundles /path/to/BUNDLES.zip --disc /path/to/disc

For fresh desktop builds, Clang 18 is recommended because GCC spends excessive
time on four large generated unity units. Set CMAKE_C_COMPILER=clang and
CMAKE_CXX_COMPILER=clang++ at first configuration and use the other desktop
options above. The current build retained completed GCC objects and compiled
four large units with Clang 18, at O0, without GCC PCH/debug symbols.
compile_large_unit.py supports --compiler /path/to/clang++ and
--repair-incomplete for an interrupted GCC build; finish the CMake build
before linking. These are x86 desktop settings, not Android build settings.

Link and run the latest diagnostic:
  python3 link_headless.py /path/to/PS2Recomp /path/to/runtime-build
  python3 run_startup.py --runner ./headless-startup --disc /path/to/disc --report latest.json --reuse-file-descriptors --stop-invalid-copy --trace-files --boot-sifcmd --inspect-iop
To reproduce the original descriptor failure, omit --reuse-file-descriptors.
The SIFCMD and IOP snapshot flags are optional. A RAM dump can be requested
using --dump-ram; precopy-ram.bin from the first stopped failure is included.
No patched game executable is used. runtime-experiment.patch is an alternative
to the four installers; do not apply both to the same checkout.
