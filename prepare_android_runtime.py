#!/usr/bin/env python3
"""Stage exact observed game entries privately, then check Android build prerequisites."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('repo',type=Path)
    p.add_argument('--report',type=Path,default=Path('android-build-preflight.json'))
    p.add_argument('--build',action='store_true')
    args=p.parse_args();repo=args.repo.resolve();root=Path(__file__).resolve().parent
    leaf=root/'leaf-output/observed_leaf_entries.cpp'
    if not leaf.is_file(): p.error('Generate and verify observed entries first')
    target=repo/'ps2xRuntime/src/runner/zz_observed_leaf_entries.cpp'
    previous=target.with_name('observed_leaf_entries.cpp')
    if previous.is_file() and previous.read_bytes()==leaf.read_bytes(): previous.unlink()
    shutil.copy2(leaf,target)
    sdk=os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK_ROOT')
    sdk_path=Path(sdk) if sdk else Path('/usr/lib/android-sdk')
    ndk=sdk_path/'ndk/28.2.13676358'
    checks={'java_available':bool(shutil.which('java')), 'gradle_available':bool(shutil.which('gradle')),
        'sdk_platform_34':(sdk_path/'platforms/android-34/android.jar').is_file(),
        'ndk_28_2':(ndk/'build/cmake/android.toolchain.cmake').is_file(),
        'sdk_cmake_3_22_1':(sdk_path/'cmake/3.22.1/bin/cmake').is_file()}
    missing=[k for k,v in checks.items() if not v]
    command=['gradle','assembleDebug','-Pps2xBootElf=/storage/emulated/0/Android/data/com.ps2x.runner/files/SLUS_204.20']
    report={'checks':checks,'missing':missing,'native_entries_staged':True,
        'apk_built':False,'android_launch_tested':False,'s24_tested':False,
        'build_command':command,'build_directory':str(repo/'android'),
        'required_device_files':'Original SLUS_204.20 and staged disc tree under app external files directory'}
    if args.build and not missing:
        result=subprocess.run(command,cwd=repo/'android',capture_output=True,text=True)
        args.report.with_suffix('.log').write_text(result.stdout+result.stderr)
        apk=repo/'android/app/build/outputs/apk/debug/app-debug.apk'
        report.update(build_returncode=result.returncode,apk_built=result.returncode==0 and apk.is_file())
        if report['apk_built']: report['apk_path']=str(apk)
    elif args.build: report['build_blocked']='Required Android SDK/NDK/Gradle components are unavailable'
    args.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 1 if args.build and not report['apk_built'] else 0

if __name__=='__main__': raise SystemExit(main())
