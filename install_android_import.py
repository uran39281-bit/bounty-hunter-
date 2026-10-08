#!/usr/bin/env python3
"""Install the phone-only game-folder picker in a prepared native Android checkout."""
import argparse
from pathlib import Path

MANIFEST = '''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application android:label="Bounty Hunter" android:isGame="true" android:allowBackup="false">
        <activity android:name="com.ps2x.runner.GameSetupActivity" android:screenOrientation="portrait"
            android:configChanges="orientation|screenSize" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
        <activity android:name="android.app.NativeActivity" android:screenOrientation="landscape"
            android:configChanges="orientation|screenSize|screenLayout|keyboard|keyboardHidden|navigation"
            android:exported="false">
            <meta-data android:name="android.app.lib_name" android:value="ps2EntryRunner" />
        </activity>
    </application>
</manifest>
'''

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('repo', type=Path)
    repo = p.parse_args().repo.resolve()
    root = Path(__file__).resolve().parent
    target = repo/'android/app/src/main'
    java = target/'java/com/ps2x/runner'
    java.mkdir(parents=True, exist_ok=True)
    for name in ('GameSetupActivity.java', 'BootModules.java'):
        (java/name).write_bytes((root/'android-phone'/name).read_bytes())
    (target/'AndroidManifest.xml').write_text(MANIFEST)
    print('Installed game-folder picker and native launcher')

if __name__ == '__main__': main()
