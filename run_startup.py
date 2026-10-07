#!/usr/bin/env python3
"""Capture a bounded startup diagnostic; a zero exit never means a playable port."""
import argparse
import json
import os
import subprocess
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runner', type=Path, required=True)
    parser.add_argument('--disc', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--stop-invalid-copy', action='store_true')
    parser.add_argument('--dump-ram', type=Path)
    parser.add_argument('--reuse-file-descriptors', action='store_true')
    parser.add_argument('--trace-files', action='store_true')
    parser.add_argument('--boot-sifcmd', action='store_true')
    parser.add_argument('--inspect-iop', action='store_true')
    args = parser.parse_args()
    env = os.environ.copy()
    env.pop('PS2X_STOP_INVALID_MEMCPY', None)
    env.pop('PS2X_PRECOPY_RAM_DUMP', None)
    env.pop('PS2X_VFS_REUSE_DESCRIPTORS', None)
    env.pop('PS2X_VFS_TRACE', None)
    env.pop('PS2X_LOAD_BOOT_SIFCMD', None)
    env.pop('PS2X_IOP_SNAPSHOT', None)
    if args.inspect_iop:
        env['PS2X_IOP_SNAPSHOT'] = '1'
    if args.boot_sifcmd:
        env['PS2X_LOAD_BOOT_SIFCMD'] = '1'
    if args.reuse_file_descriptors:
        env['PS2X_VFS_REUSE_DESCRIPTORS'] = '1'
    if args.trace_files:
        env['PS2X_VFS_TRACE'] = '1'
    if args.stop_invalid_copy:
        env['PS2X_STOP_INVALID_MEMCPY'] = '1'
        if args.dump_ram:
            env['PS2X_PRECOPY_RAM_DUMP'] = str(args.dump_ram.resolve())
    timed_out = False
    try:
        r = subprocess.run([str(args.runner.resolve()), str((args.disc / 'SLUS_204.20').resolve())],
                           capture_output=True, text=True, timeout=15, env=env)
        stdout, stderr, returncode = r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired as e:
        timed_out = True
        def decode(x): return x.decode(errors='replace') if isinstance(x, bytes) else (x or '')
        stdout, stderr, returncode = decode(e.stdout), decode(e.stderr), None
    report = {'returncode': returncode, 'timeout': timed_out,
              'stop_before_invalid_copy': args.stop_invalid_copy,
              'reuse_file_descriptors': args.reuse_file_descriptors,
              'partial_sifcmd_boot_probe': args.boot_sifcmd,
              'iop_snapshot_enabled': args.inspect_iop,
              'bundles_present': (args.disc / 'DATA/BUNDLES').is_dir(),
              'stdout': stdout, 'stderr': stderr,
              'game_startup_validated': False, 'graphics_tested': False,
              'audio_tested': False, 'android_tested': False}
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    args.report.with_suffix('.log').write_text(stdout + stderr)
    print(json.dumps({k:v for k,v in report.items() if k not in ['stdout','stderr']}, indent=2))

if __name__ == '__main__':
    main()
