#!/usr/bin/env python3
"""Add read-only native progress diagnostics for the Android menu stall."""
import argparse
from pathlib import Path

def replace_once(text,old,new):
    if text.count(old)!=1: raise ValueError('Unexpected trace anchor: '+old[:100])
    return text.replace(old,new,1)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo',type=Path)
    repo=parser.parse_args().repo.resolve()
    runtime=repo/'ps2xRuntime/src/lib/ps2_runtime.cpp'
    text=runtime.read_text()
    if 'BOUNTY_ANDROID_RUNTIME_TRACE' not in text:
        text=replace_once(text,'namespace ps2_stubs\n', '''// BOUNTY_ANDROID_RUNTIME_TRACE: observe host progress without changing guest state.
#if defined(__ANDROID__)
#include <android/log.h>
namespace {
std::atomic<uint64_t> bountyLastBranch{0}, bountyBranchCount{0}, bountyFrames{0};
void bountyTraceLine(const std::string &line) {
    __android_log_write(ANDROID_LOG_INFO,"bounty-runtime",line.c_str());
}
}
#endif

namespace ps2_stubs
''')
        text=replace_once(text,'    ctx->pc = targetPc;\n    // BOUNTY_FRONTEND_TRACE', '''#if defined(__ANDROID__)
    bountyLastBranch.store((uint64_t(sourcePc)<<32)|targetPc,std::memory_order_relaxed);
    bountyBranchCount.fetch_add(1,std::memory_order_relaxed);
#endif
    ctx->pc = targetPc;
    // BOUNTY_FRONTEND_TRACE''')
        text=replace_once(text,'    std::atomic<bool> gameThreadFinished{false};', '''#if defined(__ANDROID__)
    std::atomic<bool> traceFinished{false};
    // Independent of the render/game threads: still reports if either stalls.
    std::thread progressWatcher([&]() {
        while(!traceFinished.load(std::memory_order_acquire)) {
            std::this_thread::sleep_for(std::chrono::milliseconds(1000));
            const auto branch=bountyLastBranch.load(std::memory_order_relaxed);
            const auto snapshot=m_eeScheduler->snapshot();
            std::ostringstream line;
            line<<"GAME_PROGRESS pc=0x"<<std::hex<<m_debugPc.load(std::memory_order_relaxed)
                <<" ra=0x"<<m_debugRa.load(std::memory_order_relaxed)
                <<" branchSource=0x"<<uint32_t(branch>>32)<<" branchTarget=0x"<<uint32_t(branch)
                <<std::dec<<" branches="<<bountyBranchCount.load(std::memory_order_relaxed)
                <<" frames="<<bountyFrames.load(std::memory_order_relaxed)
                <<" snapshot="<<snapshot.sequence<<" eeCycle="<<snapshot.eeCycle
                <<" runningThread="<<snapshot.runningThreadId
                <<" dma="<<m_memory.dmaStartCount()<<" gif="<<m_memory.gifCopyCount();
            bountyTraceLine(line.str());
            for(const auto &thread:snapshot.threads) {
                std::ostringstream row;
                row<<"EE_STATE id="<<thread.id<<" pc=0x"<<std::hex<<thread.pc
                   <<" ra=0x"<<thread.ra<<std::dec<<" status="<<unsigned(thread.status)
                   <<" waitReason="<<unsigned(thread.waitReason)<<" waitId="<<thread.waitId
                   <<" priority="<<thread.currentPriority<<" invocations="<<thread.invocationDepth;
                bountyTraceLine(row.str());
            }
            for(const auto &semaphore:snapshot.semaphores) {
                if(semaphore.waiters) bountyTraceLine("EE_SEMAPHORE id="+std::to_string(semaphore.id)+
                    " count="+std::to_string(semaphore.count)+" waiters="+std::to_string(semaphore.waiters));
            }
        }
    });
#endif
    std::atomic<bool> gameThreadFinished{false};''')
        text=replace_once(text,'        EndDrawing();\n\n        if (WindowShouldClose())', '''        EndDrawing();
#if defined(__ANDROID__)
        bountyFrames.fetch_add(1,std::memory_order_relaxed);
#endif

        if (WindowShouldClose())''')
        text=replace_once(text,'    requestStop();\n#if defined(__ANDROID__)\n    bounty_android::releasePad();', '''    requestStop();
#if defined(__ANDROID__)
    traceFinished.store(true,std::memory_order_release);
    progressWatcher.join();
    bounty_android::releasePad();''')
        runtime.write_text(text)
    android=repo/'ps2xRuntime/src/lib/ps2_android_runtime.cpp'
    text=android.read_text()
    text=text.replace('"PS2X_CAPTURE_ON_PRESENT"}',
        '"PS2X_CAPTURE_ON_PRESENT","PS2X_VFS_TRACE","PS2X_FRONTEND_TRACE",'
        '"PS2X_BOOT_GRAPHICS_TRACE","PS2X_EE_THREAD_TRACE"}')
    android.write_text(text)
    vfs=repo/'ps2xRuntime/src/lib/ps2_vfs.cpp';text=vfs.read_text()
    if 'BOUNTY_VFS_FAILURE_TRACE' not in text:
        text=text.replace('#include <iostream>','#include <iostream>\n#include <cerrno>')
        text=replace_once(text,'        if (!stream)\n            return -1;', '''        // BOUNTY_VFS_FAILURE_TRACE: retain actual file-open failures.
        if (!stream) {
            if(std::getenv("PS2X_VFS_TRACE")) std::cerr<<"VFS_OPEN_FAILED path="<<path<<" errno="<<errno<<'\\n';
            return -1;
        }''')
        vfs.write_text(text)
    print('Installed independent native progress, published EE wait state and file-open diagnostics')

if __name__=='__main__': main()
