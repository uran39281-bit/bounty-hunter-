#!/usr/bin/env python3
"""Package an ARM64 Android toolchain and public dependency cache for offline use.

Runs on a GitHub runner. No game inputs, translations, credentials or APK are
included. Tar retains compiler executable modes and relative symbolic links.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

NDK='28.2.13676358'
def copy_dir(source,destination):
    if not source.is_dir():raise RuntimeError('Missing tool directory: '+str(source))
    shutil.copytree(source,destination,symlinks=True)

def package(args):
    sdk=args.sdk.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    bundle=out/'android-tools';bundle.mkdir(exist_ok=False)
    for name in ['licenses','platforms/android-34','build-tools/34.0.0','cmake/3.22.1']:
        copy_dir(sdk/name,bundle/'sdk'/name)
    source=sdk/'ndk'/NDK;target=bundle/'sdk/ndk'/NDK;target.mkdir(parents=True)
    for name in ['build','meta','sources']:
        copy_dir(source/name,target/name)
    for name in ['source.properties','package.xml','NOTICE','NOTICE.toolchain','CHANGELOG.md']:
        if (source/name).is_file():shutil.copy2(source/name,target/name)
    prebuilt=Path('toolchains/llvm/prebuilt/linux-x86_64')
    for name in ['lib','lib64','share']:
        if (source/prebuilt/name).is_dir():copy_dir(source/prebuilt/name,target/prebuilt/name)
    copy_dir(source/prebuilt/'sysroot/usr/include',target/prebuilt/'sysroot/usr/include')
    copy_dir(source/prebuilt/'sysroot/usr/lib/aarch64-linux-android',target/prebuilt/'sysroot/usr/lib/aarch64-linux-android')
    srcbin=source/prebuilt/'bin';destbin=target/prebuilt/'bin';destbin.mkdir(parents=True)
    copied={}
    def executable(name):
        src=srcbin/name
        if not src.exists():raise RuntimeError('Missing NDK executable: '+name)
        if src.is_symlink():
            resolved=src.resolve()
            if resolved.parent!=srcbin.resolve():raise RuntimeError('Unexpected executable link: '+name)
            executable(resolved.name)
            if not (destbin/name).exists():(destbin/name).symlink_to(resolved.name)
        else:
            identity=(src.stat().st_dev,src.stat().st_ino)
            if identity in copied and copied[identity]!=name:
                if not (destbin/name).exists():(destbin/name).symlink_to(copied[identity])
            elif not (destbin/name).exists():
                shutil.copy2(src,destbin/name);copied[identity]=name
    for name in ['clang','clang++','ld.lld','lld','llvm-ar','llvm-ranlib','llvm-strip',
                 'llvm-nm','llvm-objcopy','llvm-objdump','llvm-readelf','llvm-size']:
        executable(name)
    for src in srcbin.glob('aarch64-linux-android*-clang*'):executable(src.name)
    copy_dir(args.gradle.resolve(),bundle/'gradle')
    copy_dir(args.gradle_cache.resolve()/'caches/modules-2',bundle/'gradle-cache/caches/modules-2')
    for name in ['raylib','sse2neon']:
        copy_dir(args.dependencies.resolve()/name,bundle/'dependencies'/name)
        # Git metadata is unnecessary for FetchContent source overrides.
        shutil.rmtree(bundle/'dependencies'/name/'.git',ignore_errors=True)
    for path in bundle.rglob('*.lock'):path.unlink()
    # Validate the exported compiler against the exported headers/libraries.
    smoke=out/'smoke.c';smoke.write_text('int android_tools_probe(void) { return 7; }\n')
    subprocess.run([str(destbin/'clang'),'--target=aarch64-linux-android28',
        '-fPIC','-shared',str(smoke),'-o',str(out/'smoke.so')],check=True)
    subprocess.run([str(bundle/'sdk/cmake/3.22.1/bin/cmake'),'--version'],check=True)
    archive=out/'android-tools.tar.xz'
    subprocess.run(['tar','-C',str(out),'-I','xz -T2 -6','-cf',str(archive),'android-tools'],check=True)
    report={'format':1,'architecture':'arm64-v8a','host':'linux-x86_64','ndk':NDK,
        'sdk_platform':34,'build_tools':'34.0.0','cmake':'3.22.1','gradle':'8.9',
        'android_gradle_plugin':'8.6.1','compiler_smoke_passed':True,
        'game_inputs_included':False,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
        'archive_size_bytes':archive.stat().st_size}
    (out/'android-tools.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['sdk','gradle','gradle-cache','dependencies','output']:
        parser.add_argument('--'+name,type=Path,required=True)
    package(parser.parse_args())
if __name__=='__main__':main()
