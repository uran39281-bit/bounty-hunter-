#!/usr/bin/env python3
"""Prepare a private, ARM64-only Android checkout using an exported offline toolchain."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

PIN = '2c5fbb9389e11dd95693385969490c9e8e6f57b4'

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared-repo', required=True, type=Path)
    p.add_argument('--destination', required=True, type=Path)
    p.add_argument('--tools', required=True, type=Path)
    args = p.parse_args()
    source, target, tools = [x.resolve() for x in (args.prepared_repo, args.destination, args.tools)]
    root = Path(__file__).resolve().parent
    if target.exists(): p.error('Destination must be new; existing work is never overwritten')
    if subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() != PIN:
        p.error('Unexpected upstream revision')
    target.mkdir(parents=True)
    archive = target.parent/'upstream-source.tar'
    subprocess.run(['git', '-C', str(source), 'archive', '-o', str(archive), PIN], check=True)
    with tarfile.open(archive) as t: t.extractall(target, filter='data')
    archive.unlink()
    patch = root/'runtime-experiment.patch'
    subprocess.run(['git', 'apply', '--check', str(patch)], cwd=target, check=True)
    subprocess.run(['git', 'apply', str(patch)], cwd=target, check=True)
    # Carry the coherent, already verified corrected translation and leaf entries.
    runner = target/'ps2xRuntime/src/runner'
    generated = sorted((source/'ps2xRuntime/src/runner').glob('*.cpp'))
    if len(generated) != 7945: p.error('Expected the complete corrected translation plus observed entries')
    manifest = {}
    for f in generated:
        dest = runner/f.name
        shutil.copy2(f, dest)
        manifest[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
    for name in ('ps2_recompiled_functions.h', 'ps2_recompiled_stubs.h'):
        shutil.copy2(source/'ps2xRuntime/include'/name, target/'ps2xRuntime/include'/name)
    if manifest['register_functions.cpp'] != '4461d9452c73d74b0e6878c15fff7a5848404aa2f37d699545b6ea7f57e294b3':
        p.error('Unexpected registration table')
    subprocess.run(['python3', str(root/'install_android_import.py'), str(target)], check=True)
    subprocess.run(['python3', str(root/'install_android_input_fix.py'), str(target)], check=True)
    subprocess.run(['python3', str(root/'install_android_runtime_trace.py'), str(target)], check=True)
    subprocess.run(['python3', str(root/'install_vcallmsr_fix.py'), str(runner)], check=True)
    baseline_manifest=manifest
    manifest={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in runner.glob('*.cpp')}
    gradle = target/'android/app/build.gradle'
    text = gradle.read_text().replace("compileSdk 34", "compileSdk 34\n    buildToolsVersion '34.0.0'")
    text = text.replace('android {', '''def ps2xDebugKeystore = project.findProperty('ps2xDebugKeystore')
android {
    signingConfigs {
        debug {
            if (ps2xDebugKeystore) storeFile file(ps2xDebugKeystore)
        }
    }''', 1)
    text = text.replace("abiFilters 'arm64-v8a', 'x86_64'", "abiFilters 'arm64-v8a'")
    anchor = "arguments '-DPS2X_BUILD_RECOMP=OFF',"
    flags = [
        '-DPS2X_ENABLE_DEBUG_UI=OFF', '-DPS2X_ENABLE_FFMPEG=OFF',
        '-DPS2X_ENABLE_AGRESSIVE_LOGS=OFF', '-DPS2X_ENABLE_IOP_RPC_TRACE=OFF',
        '-DCMAKE_C_FLAGS_RELWITHDEBINFO=-O2 -g0 -DNDEBUG',
        '-DCMAKE_CXX_FLAGS_RELWITHDEBINFO=-O2 -g0 -DNDEBUG',
        f'-DFETCHCONTENT_SOURCE_DIR_RAYLIB={tools}/dependencies/raylib',
        f'-DFETCHCONTENT_SOURCE_DIR_SSE2NEON={tools}/dependencies/sse2neon',
        '-DFETCHCONTENT_FULLY_DISCONNECTED=ON',
    ]
    text = text.replace(anchor, anchor+'\n'+''.join("                        '"+f+"',\n" for f in flags))
    gradle.write_text(text)
    cmake = target/'CMakeLists.txt'
    text = cmake.read_text().replace('project(PS2RetroX)', '''project(PS2RetroX)
# Keep the private offline build within the host memory budget.
set(CMAKE_JOB_POOLS "bounty_compile=2;bounty_link=1")
set(CMAKE_JOB_POOL_COMPILE bounty_compile)
set(CMAKE_JOB_POOL_LINK bounty_link)''')
    cmake.write_text(text)
    (target.parent/'android-source-manifest.json').write_text(json.dumps({
        'upstream_revision': PIN, 'generated_cpp_count': len(generated),
        'generated_cpp_sha256': manifest, 'abi': 'arm64-v8a',
        'generated_cpp_sha256_baseline': baseline_manifest,
        'vcallmsr_cmsar0_operand_corrected': True,
        'optimization': '-O2 -g0 -DNDEBUG', 'fast_math': False,
        'phone_importer': True,
    }, indent=2)+'\n')
    print(f'Prepared {len(generated)} private game sources for offline ARM64 compilation')

if __name__ == '__main__': main()
