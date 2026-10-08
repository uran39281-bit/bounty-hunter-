#!/usr/bin/env python3
"""Collect measured title/menu progress without treating a stop trap as success."""
import hashlib
import json
from pathlib import Path
import re
import struct

def main():
    root=Path(__file__).resolve().parent
    names=['title-trace-600s.json','title-fixed-240s.json',
           'title-six-entries-240s.json','title-seven-entries-300s.json']
    rows=[]
    for name in names:
        path=root/name
        if not path.is_file(): continue
        result=json.loads(path.read_text())
        text=result['stderr']+'\n'+result['stdout']
        menus=list(dict.fromkeys(re.findall(r'menu_id=(0x[0-9a-f]+)',text)))
        missing=re.findall(r'\[guest-branch:missing-target\][^\n]*?target=(0x[0-9a-f]+)',text)
        capture=path.with_suffix('.ppm')
        row={'report':name,'deadline_seconds':result['deadline_seconds'],
            'returncode':result['returncode'],'timeout':result['timeout'],
            'observed_menu_ids':menus,'final_frontend_state':re.findall(r'FRONTEND_STATE[^\n]*',text),
            'missing_native_targets':missing,
            'reached_deadline_without_missing_target':not missing and 'HEADLESS_DEADLINE' in text,
            'captured_frame_exists':result['captured_frame_exists'],
            'native_font_draw_reached':'target=0x1d9420' in text,
            'native_glyph_geometry_reached':'target=0x1b9b70' in text}
        if capture.is_file():row['private_capture_sha256']=hashlib.sha256(capture.read_bytes()).hexdigest()
        rows.append(row)
    tests={}
    for name in ['title-timer-test.log','title-leaf-test.log','native-menu-entry-test.log','title-verification.log']:
        text=(root/name).read_text()
        tests[name]={'pass':'PASS' in text and 'FAIL' not in text}
    ram=(root/'font-fast-90s.ppm.ram').read_bytes()
    width,height=struct.unpack_from('<2f',ram,0x7735d0+0x84)
    report={'date':'2026-10-08','original_executable_sha256':'51c56737105d1186f0b14155e39d8af67e63b12c4ac0543e1f0e178ccd6a4304',
            'original_instructions_changed':False,'forced_game_menu_flags':False,
            'timed_title_transition_verified':any('0x110' in r['observed_menu_ids'] for r in rows),
            'cross_reaches_following_screen':any('0x35e' in r['observed_menu_ids'] for r in rows),
            'native_entry_registrations':json.loads((root/'observed-leaf-entries.json').read_text())['entries'],
            'runs':rows,'checks':tests,
            'font_evidence':{'font_files_and_localized_text_loaded':True,
                'original_copyright_layout_width':width,'original_copyright_layout_height':height,
                'native_glyph_path_reached':any(r['native_glyph_geometry_reached'] for r in rows),
                'copyright_text_visible_on_title':False,
                'latest_screen_has_distorted_text_fragments':True,
                'text_rendering_correct':False,
                'interpretation':'Font metrics and native glyph calls are present. The title copyright remains absent; the following screen has distorted text fragments. Rendering is not correct and is not explained by missing strings or collapsed layout.'},
            'android':json.loads((root/'android-build-preflight.json').read_text()),
            'following_screen_renders':True,'menu_rendering_correct':False,
            'playable':False,'s24_tested':False,
            'next_blockers':['Native text rendering','Android SDK/NDK/Gradle prerequisites'],
            'latest_missing_native_targets':rows[-1]['missing_native_targets'] if rows else [],
            'private_material_publicly_uploaded':False}
    (root/'title-result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'runs':len(rows),'latest_missing':report['latest_missing_native_targets'],
                      'timed_transition_verified':report['timed_title_transition_verified']}))

if __name__=='__main__':main()
