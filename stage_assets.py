#!/usr/bin/env python3
"""Stage supplied asset archives and original inputs for startup diagnostics."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--bundles', type=Path, required=True)
    parser.add_argument('--extra-assets', type=Path, action='append', default=[],
                        help='Additional folder ZIP; repeat for CHEWIE, SOUND or VIDEO batches')
    parser.add_argument('--disc', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    args.disc.mkdir(parents=True, exist_ok=True)
    for name in ['SLUS_204.20', 'SYSTEM.CNF', 'CDROM.TXT', 'IOPRP254.IMG']:
        src, dst = root / 'original' / name, args.disc / name
        if dst.exists() and hashlib.sha256(dst.read_bytes()).digest() != hashlib.sha256(src.read_bytes()).digest():
            raise ValueError(f'Existing disc input differs: {name}')
        shutil.copy2(src, dst)
    for src in (root / 'game-irx').glob('*.IRX'):
        dst = args.disc / 'IRX' / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and dst.read_bytes() != src.read_bytes():
            raise ValueError(f'Existing IRX differs: {src.name}')
        shutil.copy2(src, dst)
    for module in ['SIFCMD', 'CDVDFSV']:
        boot = args.disc / f'BOOT/{module}.IRX'
        boot.parent.mkdir(parents=True, exist_ok=True)
        src = root / f'iop-system-modules/{module}.irx'
        if boot.exists() and boot.read_bytes() != src.read_bytes():
            raise ValueError(f'Existing {module} boot module differs')
        shutil.copy2(src, boot)
    archives = [('data', args.data), ('bundles', args.bundles)]
    for archive in args.extra_assets:
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        archives.append((f'asset-{digest[:16]}', archive))
    for name, archive in archives:
        subprocess.run([sys.executable, str(root / 'inspect_data.py'), str(archive),
                        '--destination', str(args.disc / 'DATA'), '--report',
                        str(root / f'{name}-inventory.json')], check=True)
    entries = []
    for src in sorted((args.disc / 'DATA').rglob('*')):
        if src.is_file():
            entries.append({'path': src.relative_to(args.disc).as_posix(),
                            'bytes': src.stat().st_size,
                            'sha256': hashlib.sha256(src.read_bytes()).hexdigest()})
    report = {'files': len(entries), 'bytes': sum(e['bytes'] for e in entries),
              'missing_known_folders': [n for n in ['ALLOCS','ICONS','IFACE','BUNDLES','CHEWIE','SOUND','VIDEO']
                                       if not (args.disc / 'DATA' / n).is_dir()],
              'full_disc_completeness_verified': False, 'entries': entries}
    (root / 'combined-assets-inventory.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'entries'}, indent=2))

if __name__ == '__main__':
    main()
