#!/usr/bin/env python3
"""Install menu touch controls into the pinned Android host runner."""
import argparse
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('repo',type=Path)
    repo=p.parse_args().repo;root=Path(__file__).resolve().parent
    runtime=repo/'ps2xRuntime/src/lib/ps2_runtime.cpp';text=runtime.read_text()
    if 'BOUNTY_ANDROID_TOUCH' not in text:
        anchor='void PS2Runtime::run()\n'
        if text.count(anchor)!=1: raise ValueError('Unexpected runtime main anchor')
        text=text.replace(anchor,'// BOUNTY_ANDROID_TOUCH\n#if defined(__ANDROID__)\nnamespace bounty_android { void updatePad(); void drawControls(); void releasePad(); }\n#endif\n\n'+anchor)
        anchor='        UploadFrame(frameTex, this, presentWidth, presentHeight);'
        if text.count(anchor)!=1: raise ValueError('Unexpected input frame anchor')
        text=text.replace(anchor,'#if defined(__ANDROID__)\n        bounty_android::updatePad();\n#endif\n'+anchor)
        anchor='        DrawTexturePro(frameTex, srcRect, dstRect, Vector2{0.0f, 0.0f}, 0.0f, WHITE);'
        if text.count(anchor)!=1: raise ValueError('Unexpected drawing anchor')
        text=text.replace(anchor,anchor+'\n#if defined(__ANDROID__)\n        bounty_android::drawControls();\n#endif')
        anchor='    if (gameThread.joinable())\n'
        if text.count(anchor)!=1: raise ValueError('Unexpected shutdown anchor')
        text=text.replace(anchor,'#if defined(__ANDROID__)\n    bounty_android::releasePad();\n#endif\n'+anchor)
        runtime.write_text(text)
    if 'BOUNTY_NATIVE_PRESENT_UPLOAD' not in text:
        anchor='    const bool needsLatch = !s_hasLatchedInitialFrame || currentTick != s_lastPresentationTick;'
        if text.count(anchor)!=1: raise ValueError('Unexpected host presentation anchor')
        text=text.replace(anchor,'    // BOUNTY_NATIVE_PRESENT_UPLOAD: retain the completed native display copy.\n    const bool nativeCopy = std::getenv("PS2X_CAPTURE_ON_PRESENT") != nullptr;\n    const bool needsLatch = nativeCopy || !s_hasLatchedInitialFrame || currentTick != s_lastPresentationTick;')
        anchor='        rt->gs().latchHostPresentationFrame();'
        if text.count(anchor)!=1: raise ValueError('Unexpected host latch anchor')
        text=text.replace(anchor,'        if (!nativeCopy) rt->gs().latchHostPresentationFrame();')
        runtime.write_text(text)
    main=repo/'ps2xRuntime/src/main.cpp';main_text=main.read_text()
    if 'BOUNTY_ANDROID_BOOT' not in main_text:
        anchor='int main(int argc, char *argv[])'
        if main_text.count(anchor)!=1: raise ValueError('Unexpected Android entry anchor')
        main_text=main_text.replace(anchor,'// BOUNTY_ANDROID_BOOT\n#if defined(__ANDROID__)\nnamespace bounty_android { void configureRuntime(); }\nvoid registerObservedLeafEntries(PS2Runtime &runtime);\n#endif\n\n'+anchor)
        anchor='    redirectStdioToLogcat();'
        if main_text.count(anchor)!=1: raise ValueError('Unexpected logcat anchor')
        main_text=main_text.replace(anchor,anchor+'\n    bounty_android::configureRuntime();')
        anchor='        runtime.run();'
        if main_text.count(anchor)!=1: raise ValueError('Unexpected run anchor')
        main_text=main_text.replace(anchor,'#if defined(__ANDROID__)\n        runtime.setMissingFunctionPolicy(PS2Runtime::MissingFunctionPolicy::Stop);\n        registerObservedLeafEntries(runtime);\n#endif\n'+anchor)
        main.write_text(main_text)
    (repo/'ps2xRuntime/src/lib/ps2_android_runtime.cpp').write_text(
        '// BOUNTY_ANDROID_TOUCH: generated from author-owned control sources.\n'+
        (root/'android_touch_controls.h').read_text().replace('#pragma once\n','')+'\n'+
        (root/'android_touch_controls.cpp').read_text())
    print('Installed Android boot settings, native presentation and menu controls; device validation pending')

if __name__=='__main__': main()
