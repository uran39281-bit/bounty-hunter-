#!/usr/bin/env python3
"""Verify and extract the three exported toolchain artifacts without network access."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import zipfile

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--destination', required=True, type=Path)
    p.add_argument('--sdk-destination', type=Path,
        help='Optional separate SDK directory for hosts that truncate large workspace files')
    p.add_argument('archives', nargs=3, type=Path)
    args = p.parse_args()
    dest = args.destination.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    if (dest/'android-tools').exists(): p.error('Toolchain destination already exists')
    found = set()
    for archive in args.archives:
        with zipfile.ZipFile(archive) as z:
            for info in z.infolist():
                if info.filename not in ('android-tools.json', 'android-tools.part.aa', 'android-tools.part.ab', 'android-tools.part.ac'):
                    p.error('Unexpected artifact member: '+info.filename)
                if info.filename in found: p.error('Duplicate artifact member')
                if info.file_size > 315000000: p.error('Artifact member is too large')
                found.add(info.filename)
                with z.open(info) as source, (dest/info.filename).open('wb') as target:
                    shutil.copyfileobj(source, target)
    if len(found) != 4: p.error('Missing toolchain part or manifest')
    manifest = json.loads((dest/'android-tools.json').read_text())
    if manifest.get('architecture') != 'arm64-v8a' or manifest.get('game_inputs_included') is not False:
        p.error('Unexpected toolchain manifest')
    archive = dest/'android-tools.tar.xz'
    sha = hashlib.sha256()
    with archive.open('wb') as target:
        for suffix in ('aa', 'ab', 'ac'):
            part = dest/('android-tools.part.'+suffix)
            with part.open('rb') as source:
                while chunk := source.read(1024*1024):
                    target.write(chunk); sha.update(chunk)
    if sha.hexdigest() != manifest['archive_sha256'] or archive.stat().st_size != manifest['archive_size_bytes']:
        p.error('Toolchain archive verification failed')
    sdk = args.sdk_destination.resolve() if args.sdk_destination else None
    if sdk and sdk.exists(): p.error('Separate SDK destination already exists')
    with tarfile.open(archive, 'r|xz') as t:
        for member in t:
            path = Path(member.name)
            if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0] != 'android-tools':
                p.error('Unsafe toolchain archive member')
            if sdk and (member.name == 'android-tools/sdk' or member.name.startswith('android-tools/sdk/')):
                name = str(path.relative_to('android-tools/sdk'))
                if member.islnk():
                    member = member.replace(linkname=str(Path(member.linkname).relative_to('android-tools/sdk')))
                t.extract(member.replace(name=name), sdk, filter='data')
            else:
                t.extract(member, dest, filter='data')
    if sdk: (dest/'android-tools/sdk').symlink_to(sdk, target_is_directory=True)
    print(json.dumps({'verified_archive_sha256': sha.hexdigest(), 'tools': str(dest/'android-tools'),
        'sdk': str(sdk or dest/'android-tools/sdk')}, indent=2))

if __name__ == '__main__': main()
