"""End-to-end references and unchanged-choice checks for the art-only patch."""
from pathlib import Path
import hashlib,json,re
from PIL import Image
from pdxscript import blocks

def validate_ending_art(mod,root,manifest,loc,check):
 if 'ending_art_v031' not in manifest:return
 data=json.loads((root/'data/ending_art_v031.json').read_text(encoding='utf-8'))
 check('ending art includes 32 new scenes and 2 reform cards',len(data['assets'])==32 and len(data['reform_icons'])==2)
 check('all 33 short chains have three distinct visual outcomes',len({r['chain'] for r in data['epilogues'] if r['category']=='短链结局回顾'})==33 and all(len({r['art'] for r in data['epilogues'] if r['chain']==chain})==3 for chain in {r['chain'] for r in data['epilogues'] if r['category']=='短链结局回顾'}))
 check('101 narrative afterwords cover 99 short choices and 2 migration endings',len(data['epilogues'])==101 and len(data['hooks'])==101)
 catalog={}
 for p in (mod/'in_game/events').glob('*.txt'):
  t=p.read_text(encoding='utf-8-sig')
  for key,_,b,e,_ in blocks(t,0):catalog[key]=t[b:e]
 images=(mod/'in_game/gfx/images/hbe_ending_backgrounds.txt').read_text(encoding='utf-8-sig')
 scenes=(mod/'in_game/gfx/scenes/hbe_ending_scenes.txt').read_text(encoding='utf-8-sig')
 db=(mod/'loading_screen/gfx/illustrations/database/hbe_ending_illustrations.txt').read_text(encoding='utf-8-sig')
 for row in data['assets']+data['reform_icons']:
  p=mod/row['texture']
  with Image.open(p) as im:im.load();size=list(im.size)
  check(row['key']+' DDS decodes at native dimensions',size==row['dimensions'] and p.read_bytes()[84:88]==b'DXT5')
  check(row['key']+' selected source and texture hash',p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'] and (root/row['source']).is_file())
  if 'scene' in row:check(row['key']+' image scene and illustration linked',row['scene']+' = {' in scenes and row['tag'] in db and row['texture'].removeprefix('main_menu/') in images)
 for region,pair in data['long_branches'].items():
  for n,art in enumerate(pair):check(region+' ending '+str(n+1)+' uses correct artwork','hbe_ending_art_'+art in catalog[f'hbe_story_{region}.{201+n}'])
 for hook in data['hooks']:
  source=hook['source_option'].rsplit('.',1)[0];option=hook['source_option'];t=catalog[source]
  body=next(t[b:e] for k,_,b,e,_ in blocks(t,0) if k=='option' and re.search(r'\bname\s*=\s*'+re.escape(option)+r'\b',t[b:e]))
  clean=re.sub(r'\n?\s*# HBE_ENDING_PRESENTATION_BEGIN.*?# HBE_ENDING_PRESENTATION_END\s*','\n',body,flags=re.S)
  sha=hashlib.sha256(re.sub(r'\s+',' ',clean).strip().encode()).hexdigest()
  check(option+' original rewards costs and conditions unchanged',sha==hook['original_option_sha256'])
  check(option+' exactly one matching afterword queued',body.count('id = '+hook['event']+' ')==1)
 for row in data['epilogues']:
  body=catalog[row['id']]
  check(row['id']+' complete localized narrative',all(row['id']+s in loc for s in ('.title','.desc','.a')))
  check(row['id']+' no gameplay reward or automatic recurring dispatch',not re.search(r'\b(add_|change_|research_|construct_|create_|kill_|destroy_|trigger_event|random_events|dynamic_historical_event)',body))
  options=[body[b:e] for k,_,b,e,_ in blocks(body,0) if k=='option']
  check(row['id']+' one acknowledgement without effects',len(options)==1 and re.fullmatch(r'\s*name\s*=\s*\S+\s+ai_chance\s*=\s*\{\s*base\s*=\s*100\s*\}\s*',options[0]) is not None)
 reforms=(mod/'in_game/common/government_reforms/hbe_shared_reforms.txt').read_text(encoding='utf-8-sig')
 check('both government reform icon keys explicitly registered',all('icon = '+row['key'] in reforms for row in data['reform_icons']))
 check('new events included once in manifest count',manifest['events']==117+manifest['playable_stories']['event_count']+101+manifest.get('common_defense_v032',{}).get('visible_events',0)-len(manifest.get('legacy_state_cleanup',{}).get('events',[]))+(sum(len(blocks((mod/rel).read_text(encoding='utf-8-sig'),0)) for rel in ('in_game/events/hbe_af_results.txt','in_game/events/hbe_opening_family_events.txt')) if 'legacy_state_cleanup' in manifest else 0))
