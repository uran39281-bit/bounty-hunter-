#!/usr/bin/env python3
"""Compile APK 3's phone diagnostics around the byte-identical APK 2 runtime."""
import argparse
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET
from install_android_import import MANIFEST

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('base-apk','sdk','keystore','output','work-directory'):
        parser.add_argument('--'+name,required=True,type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parent
    work=args.work_directory.resolve()
    if work.exists(): parser.error('Work directory must be new')
    java=work/'java'; classes=work/'classes'; dex=work/'dex/1'
    for folder in (java,classes,dex): folder.mkdir(parents=True,exist_ok=True)
    for name in ('GameSetupActivity.java','BootModules.java','BountyNativeActivity.java','PhoneDiagnostics.java'):
        text=(root/'android-phone'/name).read_text()
        if name=='GameSetupActivity.java':
            text=text.replace('new Intent(this, NativeActivity.class)','new Intent(this, BountyNativeActivity.class)')
        (java/name).write_text(text)
    sdk=args.sdk.resolve(); tools=sdk/'build-tools/34.0.0'; platform=sdk/'platforms/android-34/android.jar'
    subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-source','8','-target','8',
        '-bootclasspath',str(platform)+':'+str(tools/'core-lambda-stubs.jar'),
        '-d',str(classes),*[str(p) for p in sorted(java.glob('*.java'))]],check=True)
    subprocess.run(['java','-cp',str(tools/'lib/d8.jar'),'com.android.tools.r8.D8',
        '--min-api','28','--lib',str(platform),'--output',str(dex),
        *[str(p) for p in sorted(classes.rglob('*.class'))]],check=True)
    ns='http://schemas.android.com/apk/res/android'; ET.register_namespace('android',ns)
    manifest=ET.fromstring(MANIFEST.replace('android.app.NativeActivity','com.ps2x.runner.BountyNativeActivity'))
    manifest.set('package','com.ps2x.runner')
    manifest.set('{'+ns+'}versionCode','3'); manifest.set('{'+ns+'}versionName','0.1.2')
    app=manifest.find('application')
    app.set('{'+ns+'}debuggable','true'); app.set('{'+ns+'}extractNativeLibs','false')
    uses=ET.Element('uses-sdk',{'{'+ns+'}minSdkVersion':'28','{'+ns+'}targetSdkVersion':'34'})
    manifest.insert(0,uses)
    xml=work/'AndroidManifest.xml'; ET.ElementTree(manifest).write(xml,encoding='utf-8',xml_declaration=True)
    compiled=work/'manifest.apk'
    subprocess.run([str(tools/'aapt'),'package','-f','-M',str(xml),'-I',str(platform),'-F',str(compiled)],check=True)
    subprocess.run(['python3',str(root/'package_android_controls_update.py'),
        '--base-apk',str(args.base_apk.resolve()),'--dex-directory',str(work/'dex'),
        '--sdk',str(sdk),'--keystore',str(args.keystore.resolve()),
        '--manifest-apk',str(compiled),'--output',str(args.output.resolve()),
        '--report',str(root/'android-phone-diagnostics-build.json')],check=True)

if __name__=='__main__': main()
