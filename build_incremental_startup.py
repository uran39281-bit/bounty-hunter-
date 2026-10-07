#!/usr/bin/env python3
"""Build a corrected headless diagnostic while reusing unchanged native objects.

Require the baseline desktop build and both source snapshots. Compiler and
runtime sources remain unchanged; rebuild every unit containing changed code,
compile every new function, and replace the complete registration table.
"""
import argparse
import concurrent.futures
import json
import re
import shlex
import subprocess
import hashlib
from pathlib import Path
from compact_registration import compact


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    parser.add_argument('build', type=Path)
    parser.add_argument('--relink-only', action='store_true')
    parser.add_argument('--record-cache-only', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    repo, build = args.repo.resolve(), args.build.resolve()
    original, corrected = root / 'split-output', root / 'corrected-output'
    prior = {p.name: p for p in original.glob('*.cpp')}
    latest = {p.name: p for p in corrected.glob('*.cpp')}
    if set(prior) - set(latest):
        parser.error('Removed functions need a fresh full build')
    changed = {name for name in prior if prior[name].read_bytes() != latest[name].read_bytes()}
    added = sorted(set(latest) - set(prior))
    work = root / 'incremental-build'
    work.mkdir(exist_ok=True)
    compacted = work / 'register_functions.cpp'
    previous = json.loads((root / 'corrected-registration.json').read_text()) if (root / 'corrected-registration.json').is_file() else None
    evidence = compact(latest['register_functions.cpp'], compacted)
    if args.relink_only and previous != evidence:
        parser.error('Registration changed; a full incremental compilation is required')
    (root / 'corrected-registration.json').write_text(json.dumps(evidence, indent=2) + '\n')
    commands = json.loads((build / 'compile_commands.json').read_text())
    units = [item for item in commands if '/ps2EntryRunner.dir/Unity/' in item['file']]
    runner = build / 'ps2xRuntime'
    tokens = shlex.split((runner / 'CMakeFiles/ps2EntryRunner.dir/link.txt').read_text())
    output = root / 'headless-startup-corrected'
    tokens[tokens.index('-o') + 1] = str(output)
    jobs, main_object = [], None
    declarations = f'#undef PS2_RECOMPILED_FUNCTIONS_H\n#include "{corrected / "ps2_recompiled_functions.h"}"\n'
    for unit in units:
        text = Path(unit['file']).read_text()
        included = re.findall(r'#include "([^"]+)"', text)
        names = [Path(path).name for path in included if '/src/runner/' in path]
        current_object = shlex.split(unit['command'])[shlex.split(unit['command']).index('-o') + 1]
        if any(name in changed for name in names):
            for path in included:
                name = Path(path).name
                if '/src/runner/' in path:
                    replacement = compacted if name == 'register_functions.cpp' else latest[name]
                    text = text.replace(path, str(replacement))
            source = work / Path(unit['file']).name
            body = declarations + text
            if not source.is_file() or source.read_text() != body:
                source.write_text(body)
            obj = Path(str(source) + '.o')
            command = shlex.split(unit['command'])
            command[command.index('-o') + 1] = str(obj)
            command[command.index('-c') + 1] = str(source)
            jobs.append((command, unit['directory'], str(source.name)))
            tokens[tokens.index(current_object)] = str(obj)
        else:
            obj = runner / current_object
        if str(repo / 'ps2xRuntime/src/main.cpp') in text:
            main_object = obj
    if main_object is None:
        parser.error('Graphics main object not found')
    template = next(item for item in units if not item['file'].endswith('/unity_0_cxx.cxx'))
    for offset in range(0, len(added), 32):
        source = work / f'added_{offset // 32}.cpp'
        body = declarations + ''.join(f'#include "{latest[name]}"\n' for name in added[offset:offset + 32])
        if not source.is_file() or source.read_text() != body:
            source.write_text(body)
        obj = Path(str(source) + '.o')
        command = shlex.split(template['command'])
        command[command.index('-o') + 1] = str(obj)
        command[command.index('-c') + 1] = str(source)
        jobs.append((command, template['directory'], str(source.name)))
        tokens.insert(tokens.index('-o'), str(obj))
    print(f'Rebuilding {len(changed)} changed sources, {len(added)} new sources in {len(jobs)} compile units', flush=True)
    cache_path = work / 'compile-cache.json'
    cache = json.loads(cache_path.read_text()) if cache_path.is_file() else {}
    header_lines = sorted(line for line in (corrected / 'ps2_recompiled_functions.h').read_text().splitlines() if line.startswith('void '))
    old_lines = cache.get('declarations', [])
    if old_lines and not set(old_lines).issubset(header_lines):
        cache = {}
    header_hash = hashlib.sha256()
    for path in sorted((repo / 'ps2xRuntime/include').rglob('*.h')):
        if path.name.startswith('ps2_recompiled_'):
            continue
        header_hash.update(path.read_bytes())
    common_hash = header_hash.hexdigest()
    def input_key(job):
        command, directory, name = job
        source = Path(command[command.index('-c') + 1])
        digest = hashlib.sha256(json.dumps(command).encode() + common_hash.encode() + source.read_bytes())
        for included in re.findall(r'#include "([^"]+)"', source.read_text()):
            path = Path(included)
            if path.suffix == '.cpp':
                digest.update(path.read_bytes())
        return digest.hexdigest()
    if args.record_cache_only:
        recorded = {}
        for job in jobs:
            command, directory, name = job
            obj = Path(command[command.index('-o') + 1])
            source = Path(command[command.index('-c') + 1])
            if not obj.is_file() or obj.stat().st_mtime_ns < source.stat().st_mtime_ns:
                parser.error('Cannot record cache for an unbuilt source')
            recorded[name] = {'input': input_key(job), 'object': hashlib.sha256(obj.read_bytes()).hexdigest()}
        cache_path.write_text(json.dumps({'units': recorded, 'declarations': header_lines}, indent=2) + '\n')
        print('Recorded cache for completed native build', flush=True)
        return
    updated = {}
    def compile_unit(job):
        command, directory, name = job
        obj = Path(command[command.index('-o') + 1])
        key = input_key(job)
        record = cache.get('units', {}).get(name)
        if record and record['input'] == key and obj.is_file() and hashlib.sha256(obj.read_bytes()).hexdigest() == record['object']:
            updated[name] = record
            return 'cached ' + name
        result = subprocess.run(command, cwd=directory, capture_output=True, text=True)
        (work / f'{name}.log').write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(f'Compile failed: {name}\n{result.stderr[-4000:]}')
        updated[name] = {'input': key, 'object': hashlib.sha256(obj.read_bytes()).hexdigest()}
        return name
    if args.relink_only:
        for command, directory, name in jobs:
            obj = Path(command[command.index('-o') + 1])
            source = Path(command[command.index('-c') + 1])
            if not obj.is_file() or obj.stat().st_mtime_ns < source.stat().st_mtime_ns:
                parser.error(f'Stale/missing object: {obj}; compile first')
        if any(p.stat().st_mtime_ns > min(Path(command[command.index('-o') + 1]).stat().st_mtime_ns for command, directory, name in jobs)
               for p in corrected.glob('*.cpp')):
            parser.error('Generated sources were updated; compile first')
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            for name in executor.map(compile_unit, jobs):
                print('Compiled', name, flush=True)
        cache_path.write_text(json.dumps({'units': updated, 'declarations': header_lines}, indent=2) + '\n')
    renamed = work / 'graphics-main-renamed.o'
    subprocess.run(['objcopy', '--redefine-sym', 'main=ps2_graphics_main', str(main_object), str(renamed)], check=True)
    key = str(main_object) if str(main_object) in tokens else str(main_object.relative_to(runner))
    tokens[tokens.index(key)] = str(renamed)
    diagnostic = work / 'headless-main.o'
    subprocess.run(['g++', '-std=c++20', '-O0', '-msse4.1', '-mavx2',
                    '-I', str(repo / 'ps2xRuntime/include'),
                    '-I', str(repo / 'ps2xRuntime/src/lib'),
                    '-I', str(repo / 'ps2xRuntime/src/lib/Kernel'),
                    '-I', str(repo / 'ps2xIOP/include'),
                    '-c', str(root / 'headless_startup.cpp'), '-o', str(diagnostic)], check=True)
    tokens.insert(tokens.index('-o'), str(diagnostic))
    subprocess.run(tokens, cwd=runner, check=True)
    (root / 'incremental-build-evidence.json').write_text(json.dumps({
        'changed_source_count': len(changed), 'new_source_count': len(added),
        'rebuilt_compile_units': len(jobs), 'unchanged_objects_reused': True,
        'output': output.name}, indent=2) + '\n')
    print(f'Linked {output}', flush=True)


if __name__ == '__main__':
    main()
