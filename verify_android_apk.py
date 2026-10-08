#!/usr/bin/env python3
"""Verify APK signing, launch metadata, packaged ARM64 ELF files and native entry."""
import argparse
import hashlib
import json
import re
import struct
import subprocess
import tempfile
from pathlib import Path
import zipfile

def dex_extends(data, descriptor, parent):
    """Inspect class definitions rather than trusting a class name in a manifest."""
    if data[:4] != b'dex\n':
        raise ValueError('Unexpected DEX file')
    word = lambda offset: struct.unpack_from('<I', data, offset)[0]
    strings = []
    for i in range(word(56)):
        offset = word(word(60) + i*4)
        while data[offset] & 0x80:
            offset += 1
        offset += 1
        end = data.index(0, offset)
        strings.append(data[offset:end].decode('utf-8', errors='replace'))
    types = [strings[word(word(68)+i*4)] for i in range(word(64))]
    for i in range(word(96)):
        offset = word(100)+i*32
        if types[word(offset)] == descriptor:
            superclass = word(offset+8)
            return superclass != 0xffffffff and types[superclass] == parent
    return False

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('apk', type=Path)
    p.add_argument('--sdk', required=True, type=Path)
    p.add_argument('--report', required=True, type=Path)
    args = p.parse_args()
    apk, sdk = args.apk.resolve(), args.sdk.resolve()
    build_tools = sdk/'build-tools/34.0.0'
    aapt = build_tools/'aapt'
    aapt.chmod(aapt.stat().st_mode | 0o111)
    signing = subprocess.check_output(['java', '-jar', str(build_tools/'lib/apksigner.jar'),
        'verify', '--verbose', '--print-certs', str(apk)], text=True)
    badging = subprocess.check_output([str(aapt), 'dump', 'badging', str(apk)], text=True)
    manifest = subprocess.check_output([str(aapt), 'dump', 'xmltree', str(apk), 'AndroidManifest.xml'], text=True)
    checks = {'signature_valid': True,
        'package_correct': "package: name='com.ps2x.runner'" in badging,
        'importer_is_launcher': "launchable-activity: name='com.ps2x.runner.GameSetupActivity'" in badging,
        'native_activity_present': 'android.app.NativeActivity' in manifest,
        'native_library_configured': 'ps2EntryRunner' in manifest,
        'no_broad_storage_permissions': not any(x in manifest for x in
            ('MANAGE_EXTERNAL_STORAGE', 'READ_EXTERNAL_STORAGE', 'WRITE_EXTERNAL_STORAGE'))}
    elf = []
    entry_exported = False
    controller_exported = set()
    zip_aligned = True
    with zipfile.ZipFile(apk) as z, tempfile.TemporaryDirectory(prefix='bounty-apk-check-') as folder:
        members = z.namelist()
        checks['java_dex_present'] = any(x.startswith('classes') and x.endswith('.dex') for x in members)
        queued_controller = 'com.ps2x.runner.BountyNativeActivity' in manifest
        if queued_controller:
            checks['java_controller_extends_native_activity'] = any(
                dex_extends(z.read(x), 'Lcom/ps2x/runner/BountyNativeActivity;',
                            'Landroid/app/NativeActivity;')
                for x in members if x.startswith('classes') and x.endswith('.dex'))
            checks['native_activity_present'] = checks['java_controller_extends_native_activity']
            checks['java_touch_popup_present'] = any(
                b'Landroid/widget/PopupWindow;' in z.read(x)
                for x in members if x.startswith('classes') and x.endswith('.dex'))
        native = [x for x in members if x.startswith('lib/') and x.endswith('.so')]
        checks['arm64_only'] = bool(native) and all(x.startswith('lib/arm64-v8a/') for x in native)
        checks['runner_packaged'] = 'lib/arm64-v8a/libps2EntryRunner.so' in native
        checks['no_disc_assets_packaged'] = not any(x.endswith(('SLUS_204.20', '.BND', '.IRX')) for x in members)
        reader = sdk/'ndk/28.2.13676358/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-readelf'
        reader.chmod(reader.stat().st_mode | 0o111)
        for member in native:
            info = z.getinfo(member)
            with apk.open('rb') as stream:
                stream.seek(info.header_offset)
                local = struct.unpack('<4s5H3I2H', stream.read(30))
            offset = info.header_offset + 30 + local[-2] + local[-1]
            zip_aligned &= info.compress_type == zipfile.ZIP_STORED and offset % 16384 == 0
            data = z.read(member)
            header = struct.unpack_from('<16sHHIQQQIHHHHHH', data)
            if header[0][:5] != b'\x7fELF\x02' or header[0][5] != 1 or header[2] != 183 or header[1] != 3:
                raise RuntimeError('Unexpected native ELF architecture/type: '+member)
            phoff, phsize, phcount = header[5], header[9], header[10]
            alignments = [struct.unpack_from('<IIQQQQQQ', data, phoff+i*phsize)[7]
                for i in range(phcount) if struct.unpack_from('<I', data, phoff+i*phsize)[0] == 1]
            path = Path(folder)/Path(member).name
            path.write_bytes(data)
            symbols = subprocess.check_output([str(reader), '--dyn-syms', '--wide', str(path)], text=True)
            if any('ANativeActivity_onCreate' in line and 'UND' not in line for line in symbols.splitlines()):
                entry_exported = True
            for method in ('nativeTouch', 'nativeInputStatus', 'nativeCancelTouch'):
                symbol = 'Java_com_ps2x_runner_BountyNativeActivity_'+method
                if any(symbol in line and 'UND' not in line for line in symbols.splitlines()):
                    controller_exported.add(method)
            elf.append({'name': member, 'machine': 'AArch64', 'bytes': len(data),
                'sha256': hashlib.sha256(data).hexdigest(), 'load_segment_alignments': alignments,
                'zip_data_offset': offset})
    checks['native_activity_entry_exported'] = entry_exported
    if queued_controller:
        checks['queued_touch_jni_methods_exported'] = len(controller_exported) == 3
    checks['native_zip_aligned_16kb'] = zip_aligned
    checks['native_elf_aligned_16kb'] = all(all(x >= 16384 for x in f['load_segment_alignments']) for f in elf)
    report = {'checks': checks, 'all_passed': all(checks.values()),
        'apk_sha256': hashlib.sha256(apk.read_bytes()).hexdigest(), 'apk_size_bytes': apk.stat().st_size,
        'native_libraries': elf, 'certificate_sha256': re.findall(r'certificate SHA-256 digest: (\S+)', signing),
        'signing_verification': signing.splitlines(),
        'device_launch_tested': False, 's24_tested': False, 'full_playability_established': False}
    args.report.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    if not report['all_passed']: raise SystemExit(1)

if __name__ == '__main__': main()
