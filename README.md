# Bounty Hunter native recompile experiment

Target: Galaxy S24 / Android ARM64. **Not playable; no Android APK yet.**

The PS2 EE executable has been translated to native C++ and startup executes
on x86-64 Linux with PS2Recomp's compatibility runtime and interpreted IOP.
This repository contains the experiment tooling, runtime patch and diagnostic
reports. Supply the original executable, IRX modules and game assets locally.

## Latest result — 7 October 2026

- Integrated 84 BUNDLES files. Together with partial DATA, 657 files
  (248,577,426 bytes) passed CRC/hash inventory checks.
- Isolated the memory-copy failure to monotonically increasing file
  descriptors: the game indexes a fixed buffer table using returned handles.
- With lowest-free handle reuse enabled, font/text file loading passes the
  previous failure and startup reaches the DTX RPC wait at `0x2579a8`.
- Executing the supplied SIFCMD boot module initializes SIF and removes its
  warning, but does not register the required DTX service `0x7d000000`.
- The descriptor regression and all four upstream IOP suites pass. Patch
  installers reproduce all eight changed runtime source files exactly.

No rendered frame, audio, controls, gameplay, FPS, Android binary or S24 test
is established. Diagnostic exit zero only means the bounded runner returned.
CHEWIE, SOUND and VIDEO are still missing. Complete disc assets are unverified.

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
python3 stage_assets.py --data /path/to/DATA.zip --bundles /path/to/BUNDLES.zip --disc /path/to/disc
```

4. Configure a fresh desktop runtime build. These x86 SIMD flags are not
   Android build flags:

```sh
cmake -S /path/to/PS2Recomp -B /path/to/runtime-build -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_FLAGS_DEBUG="-O0 -msse4.1 -mavx2" -DPS2X_BUILD_RECOMP=OFF -DPS2X_BUILD_ANALYZER=OFF -DPS2X_BUILD_TEST=OFF -DPS2X_BUILD_STUDIO=OFF -DPS2X_ENABLE_DEBUG_UI=OFF -DPS2X_ENABLE_FFMPEG=OFF -DPS2X_ENABLE_AGRESSIVE_LOGS=OFF -DPS2X_ENABLE_IOP_RPC_TRACE=OFF
cmake --build /path/to/runtime-build --target ps2EntryRunner -j3
python3 link_headless.py /path/to/PS2Recomp /path/to/runtime-build
python3 run_startup.py --runner ./headless-startup --disc /path/to/disc --report latest.json --reuse-file-descriptors --stop-invalid-copy --trace-files --boot-sifcmd --inspect-iop
```

Omit `--reuse-file-descriptors` to reproduce the original failure. The SIFCMD
and snapshot flags are optional. SIFCMD execution is a partial boot probe.
No RPC binding or successful audio initialization is forced. The original
executable remains unchanged. `runtime-experiment.patch` is an alternative
to the installers; apply one route, not both.

For an interrupted GCC build, `compile_large_unit.py BUILD --compiler
/path/to/clang++ --repair-incomplete` repairs missing or empty unity objects.
It does not produce an Android binary. Finish the CMake build before linking.

## Evidence and next work

See `asset-integration-result.json`, the baseline/reuse startup reports,
`headless-iop-snapshot-result.json`, `precopy-analysis.json` and the test logs.
Raw memory captures and game-derived binaries/generated C++ stay local.
The immediate blocker is the missing DTX RPC registration. Faithful IOP boot,
audio hardware behavior, asset completeness and visible rendering need work
before an Android SDK/NDK build and actual S24 testing.

The partial boot investigation consulted
[PS2SDK SIFCMD startup](https://github.com/ps2dev/ps2sdk/blob/master/iop/system/sifcmd/src/sifcmd.c).
Upstream PS2Recomp's license is included in `PS2Recomp-LICENSE.txt`.

## Complete work checkpoint

The remaining experiment scripts, configuration snapshots, inventories,
constructor hints and previous startup reports are checked in alongside the
current tooling. `README.txt` records the fuller private-checkpoint history;
its references to bundled game files describe that local checkpoint.
Use the reproduction instructions above for a fresh checkout.

`restore_baseline.py` and `build_incremental_startup.py` need locally generated
source snapshots and build caches. The stored TOML files retain their original
experiment paths; `reproduce_corrected.py` regenerates configuration for the
current machine. Older failed runs are retained as historical evidence and
do not supersede the latest results above.

Large analyzer/recompiler logs are preserved byte-for-byte inside
[`history/historical-analysis-logs.tar.xz`](history/historical-analysis-logs.tar.xz).
Smaller build, test and startup logs are ordinary files.
[`upload-manifest.json`](upload-manifest.json) records this supplemental upload.
Original game executables, IRX modules, game assets, regenerated game C++,
compiled objects, native binaries and raw RAM dumps remain local.
