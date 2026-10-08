#!/usr/bin/env python3
"""Build the prepared game APK with the verified toolchain and offline Gradle cache."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', required=True, type=Path)
    p.add_argument('--tools', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--signing-keystore', type=Path,
        help='Reuse a private debug signing key for installable updates')
    args = p.parse_args()
    repo, tools, output = [x.resolve() for x in (args.repo, args.tools, args.output)]
    output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    sdk = tools/'sdk'
    # Workspace transfers may normalize executable modes. Restore trusted tool modes
    # in this process immediately before invoking the compiler through Gradle.
    for directory in (tools/'gradle/bin', sdk/'cmake/3.22.1/bin',
            sdk/'ndk/28.2.13676358/toolchains/llvm/prebuilt/linux-x86_64/bin',
            sdk/'build-tools/34.0.0'):
        for path in directory.iterdir():
            if path.is_file(): path.chmod(path.stat().st_mode | 0o111)
    env.update(ANDROID_HOME=str(sdk), ANDROID_SDK_ROOT=str(sdk), CMAKE_BUILD_PARALLEL_LEVEL='2')
    gradle = tools/'gradle/bin/gradle'
    command = [str(gradle), '--offline', '--no-daemon', '--max-workers=2',
        '-Dorg.gradle.jvmargs=-Xmx2g', '-g', str(tools/'gradle-cache'),
        'assembleDebug', '-Pps2xBootElf=/storage/emulated/0/Android/data/com.ps2x.runner/files/SLUS_204.20']
    key = args.signing_keystore or Path(__file__).resolve().parent/'android-signing/debug.keystore'
    if args.signing_keystore and not key.is_file(): p.error('Signing keystore is missing')
    if key.is_file(): command.append('-Pps2xDebugKeystore='+str(key.resolve()))
    start = time.time()
    result = subprocess.run(command, cwd=repo/'android', env=env)
    source = repo/'android/app/build/outputs/apk/debug/app-debug.apk'
    report = {'returncode': result.returncode, 'apk_built': result.returncode == 0 and source.is_file(),
        'elapsed_seconds': round(time.time()-start, 2), 'abi': 'arm64-v8a',
        'offline_build': True, 's24_tested': False, 'android_launch_tested': False,
        'game_folder_importer': True, 'boot_elf': 'SLUS_204.20',
        'full_playability_established': False}
    if report['apk_built']:
        apk = output/'Bounty-Hunter-ARM64.apk'
        shutil.copy2(source, apk)
        report.update(apk_path=str(apk), apk_size_bytes=apk.stat().st_size,
            apk_sha256=hashlib.sha256(apk.read_bytes()).hexdigest())
    (output/'android-apk-build.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2), flush=True)
    return result.returncode

if __name__ == '__main__': raise SystemExit(main())
