"""Check gameplay preservation, branch assets and exact native loading canvases."""
from pathlib import Path
import argparse, hashlib, json, re, subprocess, sys
from PIL import Image

parser = argparse.ArgumentParser()
parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument('--baseline', default='df5c2c6', help='Commit before this presentation-only patch')
parser.add_argument('--report', type=Path)
args = parser.parse_args()
R = args.root.resolve()
M = R/'mod/holy_bashu_empire'
sys.path.insert(0, str(R/'tools'))
from pdxscript import tokens, blocks
report=json.loads((R/'data/progress_art_v031.json').read_text(encoding='utf-8'))
checks=[]
def check(label,value):
 checks.append(dict(check=label,passed=bool(value)))
 assert value,label
def clean(t):
 t=re.sub(r'\s*# HBE_PROGRESS_ART_BEGIN.*?# HBE_PROGRESS_ART_END\s*','\n',t,flags=re.S)
 return re.sub(r'illustration_tags\s*=\s*\{[^}]*\}','',t)
affected=0;markers=0
for rel in report['files']:
 p=M/rel
 if not rel.startswith('in_game/events/'):continue
 old=subprocess.check_output(['git','-C',str(R),'show',args.baseline+':mod/holy_bashu_empire/'+rel]).decode('utf-8-sig')
 new=p.read_text(encoding='utf-8-sig')
 check('gameplay token preservation: '+rel,[x.value for x in tokens(clean(old))]==[x.value for x in tokens(clean(new))])
 affected+=len(re.findall(r'illustration_tags\s*=\s*\{\s*1000 = hbe_progress_',new));markers+=new.count('# HBE_PROGRESS_ART_BEGIN')
check('115 intermediate events use dynamic art',affected==115)
check('198 presentation-only choice markers',markers==198)
for route in report['routes']:
 for art,trigger in route['variants']:
  check('art exists: '+route['key']+'/'+art,any((R/('assets/'+folder)/(art+'.png')).exists() for folder in ('event_endings_v031','event_expansion')))
  check('unset variable guarded: '+route['key'],trigger.startswith('has_variable = '))
 check('neutral/old-save fallback exists: '+route['key'],(R/'assets/event_expansion'/(route['neutral_fallback']+'.png')).exists())
sys.path.insert(0,str(R/'devtools/event-browser'));from catalog import build_catalog
c=build_catalog(M);items=[e for e in c['events'] if e.get('illustrationVariants')]
check('browser exposes all 115 changing illustrations',len(items)==115)
for e in items:check('browser default is the chosen branch image: '+e['id'],e['illustration']==e['illustrationVariants'][0]['src'])

report=json.loads((R/'data/loading_art_v031.json').read_text(encoding='utf-8'))
check('exactly four static selections',len(report['assets'])==4 and report['mode']=='static' and report['parallax'] is False)
check('pandas replace the terrace selection',{x['key'] for x in report['assets']}=={'craft','river','observatory','panda_sanctuary'})
t=(M/'loading_screen/gfx/scenes/hbe_loading_scenes.txt').read_text(encoding='utf-8-sig')
check('four single-plane static scenes',t.count('ecs_illustration_image')==4 and t.count('name = "illustration_override"')==4)
check('no parallax animation or UV motion','illustration_override_anims' not in t and 'uv_move_speed' not in t and 'animation' not in t)
images=(M/'loading_screen/gfx/images/hbe_loading_images.txt').read_text(encoding='utf-8-sig')
for row in report['assets']:
 p=M/row['texture']
 with Image.open(p) as im:
  im.load();check(row['key']+' exact vanilla canvas',im.size==(3840,2160));check(row['key']+' opaque canvas',im.convert('RGBA').getchannel('A').getextrema()==(255,255))
 check(row['key']+' native BC3/DXT5 texture',p.read_bytes()[84:88]==b'DXT5')
 check(row['key']+' texture hash',hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'])
 check(row['key']+' approved source hash',hashlib.sha256((R/row['source']).read_bytes()).hexdigest()==row['source_sha256'])
 check(row['key']+' native scene and image link','loading_screen_scene_hbe_'+row['key']+' = {' in t and row['texture'].removeprefix('loading_screen/') in images)
for lang in ('simp_chinese','english'):
 loc=(M/f'loading_screen/localization/{lang}/hbe_load_tips_l_{lang}.yml').read_text(encoding='utf-8-sig')
 check(lang+' four native quote slots',set(re.findall(r'LOADING_TIP_(\d+):',loc))=={'0','1','2','3'})
 check(lang+' native title and attribution formatting',loc.count('#T ')==4 and loc.count('#tooltip_subheading')==4 and loc.count('\\n')==4 and '\\\\n' not in loc)
 check(lang+' four credited excerpts',loc.count('— ')==4)
check('native loading GUI is not overridden',not (M/'loading_screen/gui/loading_screen.gui').exists())
progress=(M/'in_game/gfx/images/hbe_progress_backgrounds.txt').read_text(encoding='utf-8-sig')
for texture in set(re.findall(r'texture_file\s*=\s*"([^"]+)"',progress)):
 check('progress texture resolves: '+texture,(M/'main_menu'/texture).exists())

result = dict(status='passed', check_count=len(checks), checks=checks,
              intermediate_events=affected, art_markers=markers,
              static_loading_scenes=4, dimensions=[3840,2160],
              gameplay_effects_changed=False, baseline=args.baseline)
if args.report:
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='checks'}))
