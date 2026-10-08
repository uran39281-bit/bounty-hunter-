#!/usr/bin/env python3
"""Package successful Gradle/D8 outputs with an already built queued-input runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zipfile

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('base-apk','dex-directory','sdk','keystore','output','report'):
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--manifest-apk',type=Path,
        help='Optional aapt-compiled APK providing a replacement AndroidManifest.xml')
    args=parser.parse_args()
    build_tools=args.sdk/'build-tools/34.0.0'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    unsigned=args.output.with_suffix('.unsigned.apk')
    dex=sorted(args.dex_directory.glob('*/classes.dex'),key=lambda p:int(p.parent.name))
    if not dex or not any(b'Landroid/widget/PopupWindow;' in p.read_bytes() for p in dex):
        raise ValueError('Successful current popup-control D8 output is required')
    aapt=build_tools/'aapt'
    manifest=subprocess.check_output([str(aapt),'dump','xmltree',str(args.base_apk),'AndroidManifest.xml'],text=True)
    badging=subprocess.check_output([str(aapt),'dump','badging',str(args.base_apk)],text=True)
    if 'com.ps2x.runner.BountyNativeActivity' not in manifest or "versionCode='2'" not in badging:
        raise ValueError('Base APK must already declare the version-2 queued-input activity')
    with zipfile.ZipFile(args.base_apk) as base, zipfile.ZipFile(unsigned,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as out:
        native='lib/arm64-v8a/libps2EntryRunner.so'
        native_data=base.read(native)
        for method in ('nativeTouch','nativeInputStatus','nativeCancelTouch'):
            if ('Java_com_ps2x_runner_BountyNativeActivity_'+method).encode() not in native_data:
                raise ValueError('Base native runtime lacks queued touch JNI: '+method)
        members=[(native,native_data,zipfile.ZIP_STORED)]
        members += [(i.filename,base.read(i),i.compress_type) for i in base.infolist()
                    if i.filename!=native and not (i.filename.startswith('classes') and i.filename.endswith('.dex'))]
        members += [('classes'+('' if i==0 else str(i+1))+'.dex',p.read_bytes(),zipfile.ZIP_DEFLATED) for i,p in enumerate(dex)]
        if args.manifest_apk:
            with zipfile.ZipFile(args.manifest_apk) as compiled:
                new_manifest=compiled.read('AndroidManifest.xml')
            members=[(name,new_manifest if name=='AndroidManifest.xml' else data,compression)
                     for name,data,compression in members]
        for name,data,compression in members:
            info=zipfile.ZipInfo(name,date_time=(1981,1,1,1,1,0))
            info.compress_type=compression
            alignment=16384 if name==native else 4
            padding=(-(out.fp.tell()+30+len(name.encode())+4))%alignment
            info.extra=struct.pack('<HH',0xa11e,padding)+b'\0'*padding
            out.writestr(info,data)
    subprocess.run(['java','-jar',str(build_tools/'lib/apksigner.jar'),'sign',
        '--ks',str(args.keystore),'--ks-key-alias','androiddebugkey',
        '--ks-pass','pass:android','--key-pass','pass:android',
        '--out',str(args.output),str(unsigned)],check=True)
    with zipfile.ZipFile(args.output) as result:
        assert result.read(native)==native_data
        for i,p in enumerate(dex):
            assert result.read('classes'+('' if i==0 else str(i+1))+'.dex')==p.read_bytes()
    output_badging=subprocess.check_output([str(aapt),'dump','badging',str(args.output)],text=True)
    import re
    version=int(re.search(r"versionCode='(\d+)'",output_badging)[1])
    report={'apk_built':True,'apk_version_code':version,'offline_build':True,
        'packaging':'successful Gradle/D8 output plus byte-identical compiled queued-input native runtime',
        'native_library_sha256':hashlib.sha256(native_data).hexdigest(),
        'apk_sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),
        'apk_size_bytes':args.output.stat().st_size,'device_fix_verified':False}
    args.report.write_text(json.dumps(report,indent=2)+'\n')
    unsigned.unlink()
    print(json.dumps(report))

if __name__=='__main__': main()
