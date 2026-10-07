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
    parser.add_argument('--adma-timing', action='store_true')
    parser.add_argument('--trace-iop-imports', action='store_true')
    parser.add_argument('--scratchpad-receive', action='store_true')
    parser.add_argument('--trace-ee-threads', action='store_true')
    parser.add_argument('--allow-zero-priority', action='store_true')
    parser.add_argument('--boot-cdvdfsv', action='store_true')
    parser.add_argument('--cdvd-compat', action='store_true')
    parser.add_argument('--separate-callback-stacks', action='store_true')
    parser.add_argument('--seconds', type=int, default=5)
    parser.add_argument('--capture-frame', type=Path)
    parser.add_argument('--advance-cop0-count', action='store_true')
    parser.add_argument('--trace-boot-graphics', action='store_true')
    parser.add_argument('--ee-va64', action='store_true')
    parser.add_argument('--capture-on-present', action='store_true')
    parser.add_argument('--dump-graphics-memory', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.seconds <= 120:
        parser.error('--seconds must be 1..120')
    if args.boot_cdvdfsv and not args.boot_sifcmd:
        parser.error('--boot-cdvdfsv requires --boot-sifcmd')
    env = os.environ.copy()
    env.pop('PS2X_STOP_INVALID_MEMCPY', None)
    env.pop('PS2X_PRECOPY_RAM_DUMP', None)
    env.pop('PS2X_VFS_REUSE_DESCRIPTORS', None)
    env.pop('PS2X_VFS_TRACE', None)
    env.pop('PS2X_LOAD_BOOT_SIFCMD', None)
    env.pop('PS2X_IOP_SNAPSHOT', None)
    env.pop('PS2X_SPU2_ADMA_TIMING', None)
    env.pop('PS2X_IOP_IMPORT_TRACE', None)
    env.pop('PS2X_SPR_RECVN', None)
    env.pop('PS2X_EE_THREAD_TRACE', None)
    env.pop('PS2X_EE_ZERO_PRIORITY', None)
    env.pop('PS2X_LOAD_BOOT_CDVDFSV', None)
    env.pop('PS2X_CDVD_COMPAT', None)
    env.pop('PS2X_CALLBACK_HEAP_STACKS', None)
    env.pop('PS2X_CAPTURE_FRAME', None)
    env.pop('PS2X_COP0_COUNT', None)
    env.pop('PS2X_DUMP_GRAPHICS_MEMORY', None)
    if args.dump_graphics_memory:
        if not args.capture_frame or not args.trace_boot_graphics:
            parser.error('--dump-graphics-memory requires --capture-frame and --trace-boot-graphics')
        env['PS2X_DUMP_GRAPHICS_MEMORY'] = '1'
    env.pop('PS2X_CAPTURE_ON_PRESENT', None)
    if args.capture_on_present:
        if not args.capture_frame:
            parser.error('--capture-on-present requires --capture-frame')
        env['PS2X_CAPTURE_ON_PRESENT'] = '1'
    env.pop('PS2X_EE_VA64', None)
    if args.ee_va64:
        env['PS2X_EE_VA64'] = '1'
    env.pop('PS2X_BOOT_GRAPHICS_TRACE', None)
    if args.advance_cop0_count:
        env['PS2X_COP0_COUNT'] = '1'
    if args.trace_boot_graphics:
        env['PS2X_BOOT_GRAPHICS_TRACE'] = '1'
    if args.capture_frame:
        if args.capture_frame.exists():
            parser.error('Choose a fresh frame output path')
        env['PS2X_CAPTURE_FRAME'] = str(args.capture_frame.resolve())
    if args.separate_callback_stacks:
        env['PS2X_CALLBACK_HEAP_STACKS'] = '1'
    if args.cdvd_compat:
        env['PS2X_CDVD_COMPAT'] = '1'
    if args.boot_cdvdfsv:
        env['PS2X_LOAD_BOOT_CDVDFSV'] = '1'
    if args.allow_zero_priority:
        env['PS2X_EE_ZERO_PRIORITY'] = '1'
    if args.trace_ee_threads:
        env['PS2X_EE_THREAD_TRACE'] = '1'
    if args.adma_timing:
        env['PS2X_SPU2_ADMA_TIMING'] = '1'
    if args.trace_iop_imports:
        env['PS2X_IOP_IMPORT_TRACE'] = '1'
    if args.scratchpad_receive:
        env['PS2X_SPR_RECVN'] = '1'
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
        r = subprocess.run([str(args.runner.resolve()), str((args.disc / 'SLUS_204.20').resolve()), str(args.seconds)],
                           capture_output=True, text=True, timeout=args.seconds+10, env=env)
        stdout, stderr, returncode = r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired as e:
        timed_out = True
        def decode(x): return x.decode(errors='replace') if isinstance(x, bytes) else (x or '')
        stdout, stderr, returncode = decode(e.stdout), decode(e.stderr), None
    report = {'returncode': returncode, 'timeout': timed_out,
              'deadline_seconds': args.seconds,
              'cop0_count_enabled': args.advance_cop0_count,
              'ee_va64_enabled': args.ee_va64,
              'capture_on_native_display_copy': args.capture_on_present,
              'graphics_memory_dump_enabled': args.dump_graphics_memory,
              'boot_graphics_trace_enabled': args.trace_boot_graphics,
              'captured_frame_exists': bool(args.capture_frame and args.capture_frame.is_file()),
              'stop_before_invalid_copy': args.stop_invalid_copy,
              'reuse_file_descriptors': args.reuse_file_descriptors,
              'partial_sifcmd_boot_probe': args.boot_sifcmd,
              'partial_cdvdfsv_boot_probe': args.boot_cdvdfsv,
              'cdvd_compat_enabled': args.cdvd_compat,
              'callback_heap_stacks_enabled': args.separate_callback_stacks,
              'iop_snapshot_enabled': args.inspect_iop,
              'spu2_adma_timing_enabled': args.adma_timing,
              'iop_import_trace_enabled': args.trace_iop_imports,
              'scratchpad_receive_enabled': args.scratchpad_receive,
              'ee_thread_trace_enabled': args.trace_ee_threads,
              'ee_zero_priority_enabled': args.allow_zero_priority,
              'bundles_present': (args.disc / 'DATA/BUNDLES').is_dir(),
              'stdout': stdout, 'stderr': stderr,
              'game_startup_validated': False, 'graphics_tested': False,
              'audio_tested': False, 'android_tested': False}
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    args.report.with_suffix('.log').write_text(stdout + stderr)
    print(json.dumps({k:v for k,v in report.items() if k not in ['stdout','stderr']}, indent=2))

if __name__ == '__main__':
    main()
