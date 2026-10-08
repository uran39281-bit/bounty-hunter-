# Bounty Hunter Android experiment

An ARM64 debug APK has been built and signed. Static verification passes for
its signature, launcher, AArch64 native library, exported NativeActivity entry,
and 16 KB ELF/ZIP alignment. The phone importer also prepares original startup
modules; host checks match the existing SIFCMD/CDVDFSV files byte for byte.
The user imported their files on Galaxy S24. APK 1 reached the original save
warning; APK 2 reaches the original main menu. At PLAY GAME, the latest screenshot
shows `Touch: X | Game: waiting`, so the queued press has not been consumed.
The runtime reason is not yet established. Full gameplay is unverified.

APK version 2 replaces frame-sampled menu touch input with a Java control view on its own transparent popup surface
and a bounded queue of touch transitions. The primary guest pad read consumes
each press/release in order, including quick taps completed before rendering.
The same view draws controls and tests their hit areas in the fitted game
viewport. Pausing, losing focus and cancelling a touch clear held input.
After a tap, `Touch: DOWN | Game: received` confirms guest delivery; `waiting`
means the game has not polled that queued touch. Host queue checks pass for
quick taps, repeated taps, held buttons, multi-touch, cancellation, overflow
and concurrent UI/guest threads. The user reaches the main menu with this change, but advancing remains blocked.

See `android-apk-build.json`, `android-apk-verification.json`,
`android-boot-module-test.json` and `PHONE-INSTALL.md`.

APK 3 adds a phone **Export logs** button. `PhoneDiagnostics.java` runs process-
filtered logcat, retaining at most 2 MiB of characters, and records touch serials
and primary pad-read counts. A snapshot is taken before the Android document
picker pauses the activity; the selected text document is written on a worker
thread. No READ_LOGS or broad storage permissions are requested. Android CTS
confirms own-UID logs remain readable without READ_LOGS:
https://android.googlesource.com/platform/cts/+/041c3806a93%5E%21/
The exact native runtime remains unchanged; Java compilation, DEX and static APK
checks pass. Log export on this S24 still needs the next phone test.

`build_android_phone_update.py` compiles the four authored Java files against
SDK 34, runs D8, compiles an APK-3 manifest with aapt and reuses the APK-2 library.
It requires `--base-apk`, `--sdk`, `--keystore`, `--output` and a new
`--work-directory`. Keep the same private signing key for updates. Results are in
`android-phone-diagnostics-build.json` and `android-phone-diagnostics-verification.json`.

## Phone setup

Install the separately supplied `Bounty-Hunter-Diagnostics.apk`, open **Bounty Hunter**
and tap **Import game folder**. Choose the parent game folder containing
`SLUS_204.20`, `IOPRP254.IMG`, `IRX/` and `DATA/`. Unzip the original files first.
The app copies the selected disc tree into its external app files directory,
checks the original executable/image SHA-256 values, and prepares `BOOT/SIFCMD.IRX`
and `BOOT/CDVDFSV.IRX` directly from the original image. The extraction preserves
module bytes. The selected source files remain in their original folder.

The native package is `com.ps2x.runner`; the configured executable is
`/storage/emulated/0/Android/data/com.ps2x.runner/files/SLUS_204.20`.
The importer uses Android's document-tree picker without broad storage
permissions. After a complete import, subsequent app launches open the native
runner directly. No original executable, IRX or disc assets are embedded in the
APK. Startup does not require manually accessing `Android/data` from a file manager.

## Offline ARM64 build

The public `Android build tools` GitHub Actions workflow prepares SDK platform
34, build tools 34.0.0, NDK 28.2.13676358, CMake 3.22.1, Gradle 8.9, the AGP 8.6.1
module cache, raylib 5.5 and sse2neon v1.9.1. Its fixture contains no game code.
It uploads three toolchain parts with one archive SHA-256 manifest.

Download the three ZIP artifacts and verify their GitHub digests. Extract them
with `unpack_android_tools.py`; its `--sdk-destination` option allows a separate
SDK directory on hosts that truncate large executable files in a synced workspace.

```sh
python3 unpack_android_tools.py --destination /path/to/build-tools \
  --sdk-destination /tmp/bounty-android-sdk \
  android-tools-aa.zip android-tools-ab.zip android-tools-ac.zip
```

Prepare a pinned PS2Recomp checkout at
`2c5fbb9389e11dd95693385969490c9e8e6f57b4` using the complete private corrected
translation and exact observed entries. Supply the original/generated sources
from the private checkpoint; they are absent from public GitHub.

```sh
python3 stage_runtime.py /path/to/prepared-repo \
  --generated corrected-output --compact-registration
python3 prepare_android_runtime.py /path/to/prepared-repo
python3 stage_android_offline.py --prepared-repo /path/to/prepared-repo \
  --destination /path/to/new-android-checkout \
  --tools /path/to/build-tools/android-tools
python3 build_android_offline.py --repo /path/to/new-android-checkout \
  --tools /path/to/build-tools/android-tools --output /path/to/apk-output
python3 verify_android_apk.py /path/to/apk-output/Bounty-Hunter-ARM64.apk \
  --sdk /path/to/build-tools/android-tools/sdk --report apk-verification.json
```

The stager applies the twenty-file verified runtime patch to a fresh checkout,
then copies all 7,945 corrected game/observed-entry C++ files and generated
headers. It installs the phone importer, selects ARM64 only, supplies local
FetchContent dependencies and uses `-O2 -g0 -DNDEBUG` without fast-math. Ninja
compiles at most two units concurrently. Gradle runs offline. The original
native instructions and generated source files are not rewritten by this setup.
The private checkpoint retains this APK's debug signing key for future updates;
keep it private. The builder automatically reuses `android-signing/debug.keystore`
when present; `--signing-keystore` accepts an explicit private key path.

## Controls and rendering evidence

The host UI snapshots physical input through the existing mutex-backed Pad
API. The guest merges queued Android touch input when reading its primary pad.
Start, Cross, Circle and four directions are visible touch buttons.
This is a menu input implementation; further gameplay controls remain open.

Android startup enables the same compatibility settings used by the native
Linux diagnostic, stops on untranslated code, and registers the seven exact
observed native entries. Frame upload retains the completed native GS display
copy. The VIF IMAGE/DIRECT fix preserves command boundaries and original pixels.

The desktop native diagnostic renders the original title and readable save
warning. Cross opens it, Down selects No and Up selects Yes. Exact captured
palette/index comparisons pass. An isolated original-handler test confirms
Cross requests the next screen while the warning ignores Left/Right/Circle/Start.
The phone now displays the main menu; its advancement and full gameplay remain unverified.

## Remaining validation

Install on S24; check folder import, native launch, text, button press/release,
background/resume and the post-warning transition. Full sound, video and gameplay
remain unverified. The full native build reports an array-bounds warning in a
translated VU0 path (`vi[27]` with a 16-element register array). Its runtime effect
is not established and needs review before claiming gameplay support.
