#!/usr/bin/env python3
"""Verify persistent Android log data without requiring a phone or game files."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report', type=Path, required=True)
    args=p.parse_args()
    root=Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='bounty-saved-logs-') as temp:
        work=Path(temp)
        classes=work/'classes'; classes.mkdir()
        storage=work/'storage'; storage.mkdir()
        subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',str(classes),
            str(root/'android-phone/RunLog.java'),str(root/'android-phone/RunLogTest.java')],check=True)
        subprocess.run(['java','-cp',str(classes),'com.ps2x.runner.RunLogTest',str(storage)],check=True)
        cpp=work/'test.cpp'
        cpp.write_text(r'''#include "NativeRunLog.h"
#include <cassert>
#include <iterator>
int main(int argc,char**argv) {
    std::filesystem::path root=argv[1];
    auto read=[&](){ std::ifstream f(root/".bounty-native-stop.txt");
        return std::string(std::istreambuf_iterator<char>(f),{}); };
    assert(bounty_native::recordRunEvent(root,"RUNNING",1,2,0));
    assert(bounty_native::recordRunEvent(root,"MISSING_TRANSLATED_TARGET",0x1234,0x5678,
        (uint64_t(0x90)<<32)|0x1234,"guest dispatch history"));
    assert(bounty_native::recordRunEvent(root,"GAME_THREAD_RETURNED",0x1234,0x5678,0));
    auto report=read();
    assert(report.find("MISSING_TRANSLATED_TARGET pc=0x1234 ra=0x5678")!=std::string::npos);
    assert(report.find("branchSource=0x90 branchTarget=0x1234")!=std::string::npos);
    assert(report.find("GAME_THREAD_RETURNED")!=std::string::npos);
    assert(bounty_native::recordRunEvent(root,"RUNNING",1,2,0));
    assert(read().find("MISSING_TRANSLATED_TARGET")==std::string::npos);
    assert(!bounty_native::recordRunEvent(root/"absent","EXCEPTION",1,2,0));
}''')
        binary=work/'test'
        subprocess.run(['g++','-std=c++17','-I',str(root/'android-phone'),str(cpp),'-o',str(binary)],check=True)
        subprocess.run([str(binary),str(storage)],check=True)
    args.report.write_text(json.dumps({'all_passed':True,
        'checks':['reopen retains last line','two bounded rolling segments','oversize Unicode bounded',
                  'native stop reason export','native branch addresses retained','return preserves earlier stop reason',
                  'new run replaces old native status','unwritable native status fails safely'],
        'phone_tested':False,'gameplay_exit_cause_known':False},indent=2)+'\n')
    print('PASS native status survives reopen and retains the first stop reason')

if __name__=='__main__':main()
