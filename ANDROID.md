# Bounty Hunter Android experiment

No APK has been built or tested. The current native diagnostic reaches a
readable title logo; menu text and navigation remain unresolved. Touch controls
are wired in source and tested on the host through the runtime Pad API.

## Prepare a dedicated checkout

Use the pinned PS2Recomp commit in README.md, regenerate/stage the original
game translation, and install all runtime patches in that document. Apply the
installers or `runtime-experiment.patch`, never both. Generate and verify the
seven observed native entries with the existing native-leaf workflow.

The original game executable, generated game C++, disc assets and native-leaf
output remain private. They are in the private project checkpoint or supplied
asset archives; they are not included in the public source repository.

```sh
python3 prepare_android_runtime.py /path/to/PS2Recomp --build
```

This stages the verified observed entries at the end of the runner's source
list and checks JDK/Gradle, Android SDK platform 34, NDK 28.2.13676358 and SDK
CMake 3.22.1. Set `ANDROID_HOME` or `ANDROID_SDK_ROOT` to the SDK directory.
It exits with failure and records the missing prerequisites when unavailable.
With all prerequisites present it invokes the upstream debug APK build.

The app uses the pinned upstream package `com.ps2x.runner`. The configured ELF
is `/storage/emulated/0/Android/data/com.ps2x.runner/files/SLUS_204.20`.
Preserve the staged disc layout alongside it, including `SYSTEM.CNF`,
`CDROM.TXT`, `IOPRP254.IMG`, `IRX/` and `DATA/`. Keep original assets outside
the APK. Staging an incomplete disc does not establish full game support.

## Controls and presentation

The Android host UI samples touch points and the physical gamepad on its UI
thread. It merges active-low button masks, then sends that state through the
existing mutex-backed runtime Pad API. Start, Cross, Circle and the four
directions are visible touch buttons. Physical stick values are retained.
Shutdown clears the input override. This is a menu input implementation;
additional gameplay controls have not been implemented or validated.

The Android entry uses the same opt-in boot compatibility settings exercised
by the diagnostic, stops on untranslated code, and registers the exact
observed native entries. Its host frame upload retains the completed native
GS display-copy latch instead of resampling partway through native drawing.
Those changes still require an actual NDK build and device validation.

## Host verification

```sh
python3 verify_runtime_probes.py /path/to/PS2Recomp --report frontend-installation-check.json
python3 link_headless.py /path/to/PS2Recomp /path/to/runtime-build --source test_menu_controls.cpp --output test-menu-controls
./test-menu-controls
```

The control regression checks landscape/portrait hit locations, blank surface,
out-of-button touches, physical/touch combination, scripted pulse boundaries,
and real `scePadRead` press/release delivery. A separate host compiler syntax
check enables `__ANDROID__` for the Android control source against the pinned
raylib headers; it is not an ARM64/NDK compile or Android link.

`--trace-frontend` records bounded original front-end/pad/event calls.
`--script-menu-input` explicitly enables test-only repeating button pulses
after 128 real port-zero reads. Default runs send no scripted input. No game
flags, native instructions, synthetic draw packets or success responses are
injected to advance the menu. The diagnostic permits up to 600 seconds because
the current unoptimized desktop runtime advances slowly.

A longer native trace confirms the original five-second transition from menu
`0x10f` to `0x110`. Cross then requests menu `0x35e`. Exact registrations for
missing menu callbacks and an animation update are now staged privately.
This is progress through the original menu state machine; the following screen renders with distorted graphics and text fragments.
Correct rendering and usable on-device navigation are still unverified. See `title-result.json`.

Next validation: resolve native menu event/text behavior, build the real
ARM64 debug APK, install on S24, and test launch, text, button press/release and
background/resume. No device or APK validation has occurred here.
