#!/usr/bin/env python3
"""Validate and stage DATA or BUNDLES ZIPs at disc-relative paths."""
import argparse
import hashlib
import json
import stat
import zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--max-uncompressed-mib', type=int, default=512)
    args = parser.parse_args()
    destination = args.destination.resolve()
    groups = defaultdict(lambda: {'files': 0, 'bytes': 0})
    records = []
    with zipfile.ZipFile(args.archive) as archive:
        entries = archive.infolist()
        if args.max_uncompressed_mib <= 0 or sum(item.file_size for item in entries) > args.max_uncompressed_mib * 1024 * 1024:
            raise ValueError('Archive exceeds the configured extraction limit')
        names = set()
        for item in entries:
            path = PurePosixPath(item.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in item.filename:
                raise ValueError(f'Unsafe path: {item.filename}')
            if not path.parts or path.parts[0] not in {'ALLOCS', 'ICONS', 'IFACE', 'BUNDLES', 'CHEWIE', 'SOUND', 'VIDEO'}:
                raise ValueError(f'Unexpected folder: {item.filename}')
            if stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError('Symlink entry rejected')
            if item.is_dir():
                continue
            if str(path) in names:
                raise ValueError('Duplicate archive path')
            names.add(str(path))
            target = destination.joinpath(*path.parts)
            if not target.resolve().is_relative_to(destination):
                raise ValueError('Destination escapes extraction root')
            payload = archive.read(item)  # Also validates each file's CRC.
            sha = hashlib.sha256(payload).hexdigest()
            if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != sha:
                raise ValueError(f'Existing asset differs: {target}')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            groups[path.parts[0]]['files'] += 1
            groups[path.parts[0]]['bytes'] += len(payload)
            records.append({'path': 'DATA/' + str(path), 'bytes': len(payload), 'sha256': sha})
    report = {
        'archive_sha256': hashlib.sha256(args.archive.read_bytes()).hexdigest(),
        'archive_bytes': args.archive.stat().st_size,
        'crc_validated': True,
        'files': len(records), 'uncompressed_bytes': sum(x['bytes'] for x in records),
        'folders': dict(groups),
        'missing_top_level_folders': [name for name in
            ['ALLOCS', 'ICONS', 'IFACE', 'BUNDLES', 'CHEWIE', 'SOUND', 'VIDEO']
            if not (destination / name).is_dir()],
        'complete_disc_assets': False,
        'entries': records,
    }
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'entries'}, indent=2))


if __name__ == '__main__':
    main()
