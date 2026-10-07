#!/usr/bin/env python3
"""Link the diagnostic main against an existing desktop PS2Recomp build.

Reuse actual compiled generated functions and runtime libraries. Rename the
graphics main symbol in a separate object copy; keep the build untouched.
"""
import argparse
import shlex
import subprocess
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    parser.add_argument('build', type=Path)
    parser.add_argument('--constructors', action='store_true')
    parser.add_argument('--source', type=Path, help='Alternative diagnostic or functional-test main')
    parser.add_argument('--output', type=Path, help='Override executable output path')
    args = parser.parse_args()
    repo, build = args.repo.resolve(), args.build.resolve()
    root = Path(__file__).resolve().parent
    runner = build / 'ps2xRuntime'
    objects = runner / 'CMakeFiles/ps2EntryRunner.dir'
    tokens = shlex.split((objects / 'link.txt').read_text())
    if '-o' not in tokens:
        parser.error('Unexpected link command')
    output = root / ('headless-startup-ctors' if args.constructors else 'headless-startup')
    if args.output:
        output = args.output.resolve()
    tokens[tokens.index('-o') + 1] = str(output)
    main_objects = []
    for unity in (objects / 'Unity').glob('*.cxx'):
        if f'{repo}/ps2xRuntime/src/main.cpp' in unity.read_text():
            main_objects.append(Path(str(unity) + '.o'))
    if len(main_objects) != 1:
        parser.error('Expected exactly one compiled graphics-main unity object')
    main_object = main_objects[0]
    renamed = root / 'graphics-main-renamed.o'
    subprocess.run(['objcopy', '--redefine-sym', 'main=ps2_graphics_main',
                    str(main_object), str(renamed)], check=True)
    relative = str(main_object.relative_to(runner))
    if relative not in tokens:
        parser.error('Main object missing from link command')
    tokens[tokens.index(relative)] = str(renamed)
    missing = [token for token in tokens if token.endswith('.o') and
               (not (runner / token).is_file() or (runner / token).stat().st_size == 0)]
    if missing:
        parser.error('Finish the ps2EntryRunner build before linking; missing objects: ' + ', '.join(missing[:5]))
    if args.constructors:
        from compact_registration import compact
        merged = root / 'register_functions.merged.cpp'
        evidence = compact(root / 'split-output/register_functions.cpp', merged,
                           root / 'ctor-output/register_functions.cpp')
        (root / 'registration-merge.json').write_text(json.dumps(evidence, indent=2) + '\n')
        old_unity = objects / 'Unity/unity_0_cxx.cxx'
        replacement = root / 'registration-unity.cpp'
        text = old_unity.read_text()
        original = str(repo / 'ps2xRuntime/src/runner/register_functions.cpp')
        if text.count(original) != 1:
            parser.error('Registration source missing from first unity file')
        replacement.write_text(text.replace(original, str(merged)))
        entry = next(item for item in json.loads((build / 'compile_commands.json').read_text())
                     if item['file'] == str(old_unity))
        command = shlex.split(entry['command'])
        changed_object = root / 'registration-unity.o'
        command[command.index('-o') + 1] = str(changed_object)
        command[command.index('-c') + 1] = str(replacement)
        subprocess.run(command, cwd=entry['directory'], check=True)
        old_relative = str(Path(str(old_unity) + '.o').relative_to(runner))
        tokens[tokens.index(old_relative)] = str(changed_object)
        ctor_unity = root / 'constructors-unity.cpp'
        sources = sorted((root / 'ctor-output').glob('ctor_*.cpp'))
        if len(sources) != 114:
            parser.error('Expected all 114 constructor implementations')
        ctor_unity.write_text(''.join(f'#include "{source}"\n' for source in sources))
        ctor_object = root / 'constructors-unity.o'
        subprocess.run(['g++', '-std=c++20', '-O0', '-msse4.1', '-mavx2',
                        '-I', str(repo / 'ps2xRuntime/include'),
                        '-I', str(repo / 'ps2xRuntime/src/lib/Kernel'),
                        '-I', str(repo / 'ps2xIOP/include'),
                        '-c', str(ctor_unity), '-o', str(ctor_object)], check=True)
        tokens.insert(tokens.index('-o'), str(ctor_object))
    diagnostic = root / 'headless-main.o'
    subprocess.run(['g++', '-std=c++20', '-O0', '-msse4.1', '-mavx2',
                    '-I', str(repo / 'ps2xRuntime/include'),
                    '-I', str(repo / 'ps2xRuntime/src/lib'),
                    '-I', str(repo / 'ps2xRuntime/src/lib/Kernel'),
                    '-I', str(repo / 'ps2xIOP/include'),
                    '-c', str(args.source.resolve() if args.source else root / 'headless_startup.cpp'),
                    '-o', str(diagnostic)], check=True)
    tokens.insert(tokens.index('-o'), str(diagnostic))
    subprocess.run(tokens, cwd=runner, check=True)
    output.chmod(output.stat().st_mode | 0o100)
    print(f'Linked {output}; diagnostic only, not an Android APK')


if __name__ == '__main__':
    main()
