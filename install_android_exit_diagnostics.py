#!/usr/bin/env python3
"""Persist native runner stop reasons without changing guest execution."""
import argparse
from pathlib import Path
import shutil

def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Unexpected runtime anchor: ' + old[:100])
    return text.replace(old, new, 1)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('repo', type=Path)
    repo = p.parse_args().repo.resolve()
    root = Path(__file__).resolve().parent
    shutil.copy2(root/'android-phone/NativeRunLog.h', repo/'ps2xRuntime/include/bounty_native_run_log.h')
    path = repo/'ps2xRuntime/src/lib/ps2_runtime.cpp'
    text = path.read_text()
    if '// BOUNTY_SAVED_NATIVE_EXIT' not in text:
        text = once(text, '#include <android/log.h>', '#include <android/log.h>\n// BOUNTY_SAVED_NATIVE_EXIT\n#include "bounty_native_run_log.h"')
        text = once(text, '            std::cerr << oss.str() << std::endl;', '''            std::cerr << oss.str() << std::endl;
#if defined(__ANDROID__)
            bounty_native::recordRunEvent(getIoPaths().elfDirectory,
                "MISSING_TRANSLATED_TARGET", targetPc,
                m_debugRa.load(std::memory_order_relaxed),
                (uint64_t(sourcePc) << 32) | targetPc, oss.str());
#endif''')
        text = once(text, '    std::atomic<bool> traceFinished{false};', '''    bounty_native::recordRunEvent(getIoPaths().elfDirectory, "RUNNING",
        m_debugPc.load(std::memory_order_relaxed), m_debugRa.load(std::memory_order_relaxed), 0);
    std::atomic<bool> traceFinished{false};''')
        text = once(text, '            uint32_t pc = m_debugPc.load(std::memory_order_relaxed);', '''            uint32_t pc = m_debugPc.load(std::memory_order_relaxed);
#if defined(__ANDROID__)
            bounty_native::recordRunEvent(getIoPaths().elfDirectory, "GAME_THREAD_RETURNED", pc,
                m_debugRa.load(std::memory_order_relaxed), bountyLastBranch.load(std::memory_order_relaxed),
                isStopRequested() ? "stopRequested=true" : "stopRequested=false");
#endif''')
        for original, kind, detail in (
            ('            std::cerr << "Error during program execution: " << e.what() << std::endl;', 'EXCEPTION', 'e.what()'),
            ('            std::cerr << "Error during program execution: unknown exception" << std::endl;', 'UNKNOWN_EXCEPTION', '"Unknown C++ exception"')):
            text = once(text, original, original + '''
#if defined(__ANDROID__)
            bounty_native::recordRunEvent(getIoPaths().elfDirectory, "''' + kind + '''",
                m_debugPc.load(std::memory_order_relaxed), m_debugRa.load(std::memory_order_relaxed),
                bountyLastBranch.load(std::memory_order_relaxed), ''' + detail + ''');
#endif''')
        path.write_text(text)
    print('Installed saved native run and stop diagnostics')

if __name__ == '__main__': main()
