#!/usr/bin/env python3
"""Stage translated C++ into a dedicated PS2Recomp checkout for a build.

This does not configure, compile, launch a game, or build an APK.
"""
import argparse
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    parser.add_argument('--generated', type=Path,
                        default=Path(__file__).resolve().parent / 'split-output')
    parser.add_argument('--compact-registration', action='store_true')
    args = parser.parse_args()
    runtime = args.repo / 'ps2xRuntime'
    if not (runtime / 'CMakeLists.txt').is_file():
        parser.error('Expected a PS2Recomp checkout')
    sources = sorted(args.generated.glob('*.cpp'))
    headers = [args.generated / name for name in
               ('ps2_recompiled_functions.h', 'ps2_recompiled_stubs.h')]
    if not sources or any(not p.is_file() for p in headers):
        parser.error('Generated sources/headers are missing')
    runner = runtime / 'src/runner'
    runner.mkdir(exist_ok=True)
    for source in sources:
        if args.compact_registration and source.name == 'register_functions.cpp':
            from compact_registration import compact
            compact(source, runner / source.name)
            continue
        destination = runner / source.name
        if destination.is_file() and destination.read_bytes() == source.read_bytes():
            continue
        shutil.copy2(source, runner / source.name)
    for header in headers:
        shutil.copy2(header, runtime / 'include' / header.name)
    print(f'Staged {len(sources)} C++ sources and {len(headers)} headers')


if __name__ == '__main__':
    main()
