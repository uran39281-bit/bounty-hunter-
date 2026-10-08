#!/usr/bin/env python3
"""Install queued Android menu touch input in a prepared native checkout."""
from pathlib import Path
import argparse
import shutil

def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Unexpected source anchor: ' + old[:100])
    return text.replace(old, new, 1)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo',type=Path)
    repo=parser.parse_args().repo.resolve()
    root=Path(__file__).resolve().parent
    main_dir=repo/'android/app/src/main'
    java=main_dir/'java/com/ps2x/runner'
    shutil.copy2(root/'android-phone/BountyNativeActivity.java',java/'BountyNativeActivity.java')
    shutil.copy2(root/'android-phone/PhoneDiagnostics.java',java/'PhoneDiagnostics.java')
    manifest=main_dir/'AndroidManifest.xml'
    text=manifest.read_text()
    if 'com.ps2x.runner.BountyNativeActivity' not in text:
        manifest.write_text(replace_once(text,'android:name="android.app.NativeActivity"',
                                        'android:name="com.ps2x.runner.BountyNativeActivity"'))
    setup=java/'GameSetupActivity.java'
    setup.write_text(setup.read_text().replace('new Intent(this, NativeActivity.class)',
                                              'new Intent(this, BountyNativeActivity.class)'))
    shutil.copy2(root/'android_touch_queue.h',repo/'ps2xRuntime/include/android_touch_queue.h')
    native=repo/'ps2xRuntime/src/lib/ps2_android_runtime.cpp'
    text=native.read_text()
    if 'BOUNTY_QUEUED_ANDROID_INPUT' not in text:
        start=text.index('    for (int i=0;i<GetTouchPointCount();++i) {')
        end=text.index('    const uint16_t physical=',start)
        text=text[:start]+text[end:]
        start=text.index('void drawControls() {')
        end=text.index('void releasePad()',start)
        text=text[:start]+'// Java draws and receives the same controls in one coordinate space.\nvoid drawControls() {}\n'+text[end:]
        text=text.replace('#include <cstdlib>', '#include <cstdlib>\n#include <jni.h>\n#include "android_touch_queue.h"')
        text += '''
// BOUNTY_QUEUED_ANDROID_INPUT: Android and the guest may run at different speeds.
#if defined(__ANDROID__)
namespace bounty_android {
static bounty_touch::Queue touchQueue;
uint16_t consumeTouchButtons() { return touchQueue.read(); }
}
extern "C" JNIEXPORT jlong JNICALL
Java_com_ps2x_runner_BountyNativeActivity_nativeTouch(JNIEnv *, jclass, jint buttons) {
    return bounty_android::touchQueue.push(static_cast<uint16_t>(buttons));
}
extern "C" JNIEXPORT jlong JNICALL
Java_com_ps2x_runner_BountyNativeActivity_nativeInputStatus(JNIEnv *, jclass) {
    return static_cast<jlong>(bounty_android::touchQueue.status());
}
extern "C" JNIEXPORT void JNICALL
Java_com_ps2x_runner_BountyNativeActivity_nativeCancelTouch(JNIEnv *, jclass) {
    bounty_android::touchQueue.cancel();
}
#endif
'''
        native.write_text(text)
    pad=repo/'ps2xRuntime/src/lib/Kernel/Stubs/Pad.cpp'
    text=pad.read_text()
    if 'BOUNTY_QUEUED_ANDROID_INPUT' not in text:
        text=replace_once(text,'namespace ps2_stubs\n', '''// BOUNTY_QUEUED_ANDROID_INPUT
#if defined(__ANDROID__)
namespace bounty_android { uint16_t consumeTouchButtons(); }
#endif

namespace ps2_stubs
''')
        text=replace_once(text,'            fillPadStatus(outData, state, portState);', '''#if defined(__ANDROID__)
            // Only consume after a successful primary guest pad read. A tap
            // cannot disappear merely because rendering samples after release.
            if (port == 0 && slot == 0)
                state.buttons &= static_cast<uint16_t>(~bounty_android::consumeTouchButtons());
#endif
            fillPadStatus(outData, state, portState);''')
        pad.write_text(text)
    gradle=repo/'android/app/build.gradle'
    text=gradle.read_text()
    for code in (1,2,3): text=text.replace('versionCode '+str(code),'versionCode 4')
    for name in ('0.1.0','0.1.1','0.1.2'): text=text.replace("versionName '"+name+"'","versionName '0.1.3'")
    gradle.write_text(text)
    print('Installed queued touch controls, phone log export and APK version 4')

if __name__=='__main__': main()
