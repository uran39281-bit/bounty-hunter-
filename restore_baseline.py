#!/usr/bin/env python3
"""Restore the baseline generated source snapshot from the deduplicated bundle."""
import hashlib
import json
import shutil
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / 'baseline-source-manifest.json').read_text())
    destination = root / 'split-output'
    destination.mkdir(exist_ok=True)
    for name, expected in manifest.items():
        if Path(name).name != name:
            raise ValueError('Invalid manifest filename')
        source = root / 'baseline-delta' / name
        if not source.is_file():
            source = root / 'corrected-output' / name
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Source mismatch: {name}')
        target = destination / name
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            shutil.copy2(source, target)
    print(f'Restored and verified {len(manifest)} baseline files')


if __name__ == '__main__':
    main()
