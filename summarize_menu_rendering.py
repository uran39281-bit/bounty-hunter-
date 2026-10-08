#!/usr/bin/env python3
"""Summarize measured packet, upload and native menu evidence."""
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent
def run(name):
    r=json.loads((ROOT/name).read_text());t=r['stdout']+'\n'+r['stderr']
    missing=re.findall(r'\[guest-branch:missing-target\][^\n]*?target=(0x[0-9a-f]+)',t)
    calls=[]
    # Associate handler events with measured pad pulses, rather than assuming
    # the game assigns a distinct event number to each direction.
    labels={'0xfff7':'Start','0xbfff':'Cross','0xffef':'Up','0xffdf':'Right',
            '0xffbf':'Down','0xff7f':'Left','0xdfff':'Circle'}
    button=None
    for line in t.splitlines():
        pulse=re.search(r'SCRIPTED_PAD_INPUT reads=(\d+) buttons=(0x[0-9a-f]+)',line)
        if pulse:button=labels.get(pulse[2])
        call=re.search(r'FRONTEND_CALL target=0x31f280[^\n]*?a1=(0x[0-9a-f]+)[^\n]*?menu_id=(0x[0-9a-f]+)',line)
        if call:calls.append({'button':button,'native_event':call[1],'menu_id':call[2]})
    result={'report':name,'host_seconds':r['deadline_seconds'],'returncode':r['returncode'],
        'timeout':r['timeout'],'menus':list(dict.fromkeys(re.findall(r'menu_id=(0x[0-9a-f]+)',t))),
        'missing_targets':missing,'reached_deadline_without_missing_target':r['returncode']==0 and not r['timeout'] and not missing and 'HEADLESS_DEADLINE' in t,
        'native_input_handler_calls':calls,'scripted_pad_pulses':re.findall(r'SCRIPTED_PAD_INPUT[^\n]*',t),
        'vector_reserved_instruction_reports':t.count('[VU1 reserved'),
        'captured_frame_exists':r['captured_frame_exists'],
        'final_frontend_state':re.findall(r'FRONTEND_STATE[^\n]*',t)}
    frame=(ROOT/name).with_suffix('.ppm')
    if frame.exists():result['private_frame_sha256']=hashlib.sha256(frame.read_bytes()).hexdigest()
    return result

def main():
    names=['menu-vertices-480s.json','menu-vector-360s.json','menu-boundary-360s.json','menu-navigation-480s.json']
    rows=[run(n) for n in names if (ROOT/n).exists()]
    navigation=next((r for r in rows if r['report']=='menu-navigation-480s.json'),None)
    delivered=sorted({c['button'] for c in navigation['native_input_handler_calls']
        if c['button'] and c['menu_id'] not in ['0x0','0x10f']}) if navigation else []
    baseline=(ROOT/'vif-image-baseline-test.log').read_text()
    fixed=(ROOT/'vif-image-fixed-test.log').read_text()
    def upload(name):
        text=(ROOT/name).read_text();m=re.search(r'palette_differences=(\d+) pixel_index_differences=(\d+) of 65536',text)
        return {'palette_differences':int(m[1]),'pixel_index_differences':int(m[2]),'pixel_count':65536}
    direct=(ROOT/'font-replay.ppm').read_bytes();vif=(ROOT/'font-replay-vif.ppm').read_bytes()
    navigation_test=(ROOT/'menu-navigation-test.log').read_text()
    isolated=[]
    for button,event,menu,result,changed,states,passed in re.findall(
        r'NATIVE_MENU_CAPTURE button=(\w+) event=(0x[0-9a-f]+) original_menu=(0x[0-9a-f]+) return_pc=0x101000 result=(-?\d+) changed_ram_bytes=(\d+) state_changes=(\d+) pass=(\d)',navigation_test):
        isolated.append({'button':button,'native_event':event,'original_menu':menu,'result':int(result),
            'changed_ram_bytes':int(changed),'state_changes':int(states),'pass':passed=='1'})
    result={'date':'2026-10-08','original_instructions_changed':False,'forced_menu_flags':False,
        'runtime_fix':'Pending GIF IMAGE payload is consumed only within VIF DIRECT/DIRECTHL payloads. Intervening VIF NOP/MARK/DIRECT commands remain commands.',
        'stream_coverage':'Complete DIRECT blocks across calls and multi-block GIF IMAGE continuations. Arbitrary byte fragmentation inside a DIRECT block is not implemented by this change.',
        'host_menu_controls_pass':(ROOT/'menu-controls-test.log').read_text().startswith('PASS'),
        'regression':{'baseline_reproduces_pixel_corruption':'FAIL: VIFcodes were consumed' in baseline,
            'fixed_cases_pass':fixed.startswith('PASS:'),'cases':fixed.strip()},
        'captured_native_upload':{'baseline':upload('native-vif-baseline.log'),'fixed':upload('native-vif-upload.log')},
        'font_replay_fixture':{'readable_copyright_text':True,'direct_and_vif_pixels_identical':direct==vif,
            'private_pixels_sha256':hashlib.sha256(direct).hexdigest(),
            'limitation':'Isolated packet replay with a separately loaded original atlas; does not establish normal asset loading or full-game rendering.'},
        'runs':rows,'installer_and_patch_exact':json.loads((ROOT/'menu-installation-check.json').read_text())['pinned_source_installation_reproduces_current_patches'],
        'native_control_delivery':{'buttons_after_title':delivered,
            'all_seven_delivered':set(delivered)=={'Start','Cross','Circle','Up','Down','Left','Right'},
            'limitation':'Handler delivery alone does not establish every navigation effect or on-device touch behavior.'},
        'isolated_original_warning_controls':{'pass':len(isolated)==7 and all(c['pass'] for c in isolated),
            'cases':isolated,'fixture':'menu-boundary-360s.ppm.ram',
            'behavior':'Up/Down toggle the captured No selection to Yes. Cross requests original screen 0x4f and deactivates the warning. Left/Right/Circle/Start return -2 and leave menu state unchanged.',
            'limitation':'Each case restores the same private capture and invokes the unchanged native handler. This does not exercise the subsequent screen or on-device touch input.'},
        'android':json.loads((ROOT/'menu-android-preflight.json').read_text()),
        'playable':False,'on_device_controls_validated':False,
        'native_rendering_visual_review':{
            'capture':'menu-boundary-360s.ppm',
            'size':[640,446],
            'readable_warning_text':True,
            'visible_controls':['YES','NO','Cross OK'],
            'selected_option':'NO',
            'comparison_capture':'menu-navigation-480s.ppm',
            'comparison_selected_option':'YES',
            'assessment':'Original save warning, border, text and background now render coherently. Cross opens the warning; Down selects No.',
            'limitation':'Visual review of one original native menu. Full opening sequence, all screens, gameplay and on-device rendering are unverified.'},
        'private_game_material_publicly_uploaded':False}
    (ROOT/'menu-rendering-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'runs':len(rows),'regression_pass':result['regression']['fixed_cases_pass'],'native_upload':result['captured_native_upload']['fixed']}))

if __name__=='__main__':main()
