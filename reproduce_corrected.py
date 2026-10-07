#!/usr/bin/env python3
"""Repeat the corrected translation with the pinned, already built tools."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from split_analysis_elf import split
from prepare_corrected_config import entries

COMMIT = '2c5fbb9389e11dd95693385969490c9e8e6f57b4'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    parser.add_argument('--tools-build', type=Path)
    parser.add_argument('--executable', type=Path,
                        default=Path(__file__).resolve().parent / 'original/SLUS_204.20')
    args = parser.parse_args()
    root, repo = Path(__file__).resolve().parent, args.repo.resolve()
    if subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip() != COMMIT:
        parser.error('Use the pinned PS2Recomp commit documented in README.txt')
    entries(args.executable)  # Verify original executable hash before touching outputs.
    build = args.tools_build.resolve() if args.tools_build else repo / 'build-tools'
    analyzer, recompiler = build / 'ps2xAnalyzer/ps2_analyzer', build / 'ps2xRecomp/ps2_recomp'
    if not analyzer.is_file() or not recompiler.is_file():
        parser.error('Build ps2_analyzer and ps2_recomp first (see reproduce.py/README.txt)')
    image, config = root / 'SLUS_204.20.corrected.elf', root / 'corrected-config.toml'
    split(args.executable, image, 0x359880, include_constructors=True)
    with (root / 'corrected-analyzer.log').open('w') as log:
        subprocess.run([str(analyzer), str(image), str(config)], stdout=log, stderr=subprocess.STDOUT, check=True)
    subprocess.run([sys.executable, str(root / 'prepare_corrected_config.py'),
                    str(config), str(args.executable.resolve()), '--output-directory',
                    str(root / 'corrected-output')], check=True)
    with (root / 'corrected-recompiler.log').open('w') as log:
        subprocess.run([str(recompiler), str(config)], stdout=log, stderr=subprocess.STDOUT, check=True)
    print('Corrected C++ regenerated. This does not build an Android APK.')


if __name__ == '__main__':
    main()
