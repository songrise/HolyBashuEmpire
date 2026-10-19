"""Data-driven separation of early industry, military and civic research."""
from pathlib import Path
import json,re
from PIL import Image,ImageDraw,ImageFont
from pdxscript import blocks,tokens,apply_edits
from build_support import snapshot_files,sha256_file,write_preserving_format
from build_flags import save_dds
from build_icon_assets import fit

CONFIG='data/early_research_design.json'
MIL_FILE='in_game/common/advances/hbe_local_military.txt'
TRIGGER_FILE='in_game/common/scripted_triggers/hbe_early_research.txt'

def load_config(root):return json.loads((Path(root)/CONFIG).read_text(encoding='utf-8'))
def military_key(row):return 'hbe_military_'+row['region']
def scalars(body):
    ts=tokens(body);depth=0;result=[]
    for i,t in enumerate(ts):
        if t.value=='{':depth+=1
        elif t.value=='}':depth-=1
        elif not depth and i+2<len(ts) and ts[i+1].value=='=' and ts[i+2].value!='{':
            result.append((t.value,ts[i+2].value,t.start,ts[i+2].end))
    return result
def remove_fields(body,keys):return apply_edits(body,[(a,b,'') for key,_,a,b in scalars(body) if key in keys])
def set_fields(body,values):
    body=remove_fields(body,set(values)).rstrip()
    return body+'\n'+''.join('    '+key+' = '+(f'{value:g}' if isinstance(value,(int,float)) else value)+'\n' for key,value in values.items())
def set_modifiers(body,values):
    numeric={key for key,value,_,_ in scalars(body) if re.fullmatch(r'-?\d+(?:\.\d+)?',value) and key not in {'research_cost','starting_technology_level','content_priority'}}
    return set_fields(remove_fields(body,numeric),values)
def rewrite(path,callback):
    text=path.read_text(encoding='utf-8-sig');edits=[]
    for key,_,a,b,_ in blocks(text,0):
        body=callback(key,text[a:b])
        if body!=text[a:b]:edits.append((a,b,body))
    return apply_edits(text,edits)
def put(path,text,setup=False):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text.rstrip()+'\n',encoding='utf-8' if setup else 'utf-8-sig',newline='\n')
def update_localization(path,values):
    text=path.read_text(encoding='utf-8-sig')
    for key,value in values.items():
        line=' '+key+': '+json.dumps(value,ensure_ascii=False)
        pattern=r'(?m)^[ \t]+'+re.escape(key)+r':[^\n]*$'
        if re.search(pattern,text):text=re.sub(pattern,lambda _:line,text)
        else:text=text.rstrip()+'\n'+line+'\n'
    put(path,text)

def export_art(out,root,config):
    image=Image.open(root/config['atlas']).convert('RGBA');w,h=image.size
    # Mechanical sprite extraction; split in the clear gutters of this atlas.
    xs=[0,round(w*.3375),round(w*.6703),w];ys=[0,round(h*.325),round(h*.6414),h]
    proof=Image.new('RGB',(4*200,2*250),'#302a23');draw=ImageDraw.Draw(proof);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',19)
    rows=config['military']+[{'name':'可以跨圈经营','key':config['cross_permission']}];exports=[]
    for i,row in enumerate(rows):
        key=row.get('key') or military_key(row);x,y=i%3,i//3
        top=round(h*2/3) if i==7 else ys[y]
        box=(xs[x],top,xs[x+1],ys[y+1]);sprite=fit(image.crop(box),256)
        png=root/'assets/technology_icons'/f'{key}.png';png.parent.mkdir(parents=True,exist_ok=True);sprite.save(png)
        folders=('advance','hbe/technology') if i<7 else ('icons/modifier_types',)
        for folder in folders:save_dds(out/f'main_menu/gfx/interface/{folder}/{key}.dds',sprite if i<7 else fit(sprite,128))
        px,py=(i%4)*200,(i//4)*250;thumb=sprite.resize((180,180),Image.Resampling.LANCZOS);proof.paste(thumb,(px+10,py+10),thumb);draw.text((px+12,py+204),row['name'],font=font,fill='#e4d3b5')
        exports.append(dict(key=key,crop=list(box),source=config['atlas'],sprite=str(png.relative_to(root)).replace('\\','/'),sprite_sha256=sha256_file(png)))
    proof_path=root/'assets/early_research/icons_preview.png';proof.save(proof_path)
    return exports

def sync_catalogue(root,manifest):
    """Keep generated design references aligned with the final effective database."""
    catalogue=manifest['technology_rewards']
    links={
        'hbe_tech_common_1':'开放本府府议；民役政策与军制分别研究。',
        'hbe_tech_common_2':'开放乡社见证权；整合其他旧府州后，地方援助可以使用10点义气作替代担保。',
        'hbe_tech_common_5':'开放行会雇价保任；仍须采用行会雇办。',
        'hbe_civic_common_1':'开放三种互斥的民役政策与减役补偿；驻防粮额与阶层特权分别开放。',
        'hbe_tech_central_hills_1':'开放分仓义廪基础建造与维护；农业生产方式仍由第二时代后续科技解锁。'}
    for row in catalogue['advances']:
        if row['key'] in links:row['link']=links[row['key']]
    write_preserving_format(root/'data/technology_rewards_v021.json',json.dumps(catalogue,ensure_ascii=False,indent=2)+'\n')
    path=root/'docs/technology_rewards_v021.md'
    text=path.read_text(encoding='utf-8-sig')
    intro='# 0.3.2 科技与地区产业\n\n当前共91项科技：原64项共有与地区科技、16项政制科技、4项产业副产科技及7项军制科技。产业、民役与军制分别研究，详见[早期科技调整](early_research_v032.md)。下表保留原80项课题的有效数值。\n\n'
    text=re.sub(r'\A# [^\n]+\n.*?(?=## 科技表)',lambda _:intro,text,flags=re.S)
    for row in catalogue['advances']:
        pattern=r'(?m)^\|'+re.escape(row['name'])+r'\|[^\n]*$'
        match=re.search(pattern,text)
        if not match:continue
        cells=match.group(0).split('|')
        cells[2]=' '.join(f'{k} = {v:g}' for k,v in row['modifiers'].items()) or '无被动数值加成'
        if row['key'] in links:cells[3]=links[row['key']]
        if row['key']=='hbe_tech_common_4':cells[2]+=' hbe_can_cross_circle_industry = yes'
        text=text[:match.start()]+'|'.join(cells)+text[match.end():]
    write_preserving_format(path,text)

def apply(out,root,game):
    out,root,game=map(Path,(out,root,game));config=load_config(root);mp=out/'build_manifest.json';manifest=json.loads(mp.read_text(encoding='utf-8-sig'))
    military=config['military'];by_region={row['region']:row for row in military};by_unit={row['unit']:row for row in military};permission=config['cross_permission']
    new_units={row['unit']:military_key(row) for row in military}
    building_moves={b:military_key(row) for row in military for b in row['buildings']};building_moves['hbe_community_granary']='hbe_tech_central_hills_1'
    military_nodes=[];triggers=[];entries={lang:{} for lang in ('simp_chinese','english')}
    for row in military:
        region=row['region'];key=military_key(row);tags=[c['tag'] for c in manifest['countries'] if c['region']==region]
        identity='OR = { '+' '.join('has_or_had_tag = '+tag for tag in tags)+' }'
        military_nodes.append(f'''{key} = {{
 age = age_1_traditions starting_technology_level = 99 research_cost = {config['military_cost']:g}
 icon = {key} content_priority = 875
 potential = {{ {identity} }}
 allow = {{ is_member_of_international_organization = international_organization:hbe_empire NOT = {{ has_variable = hbe_research_pending }} }}
 requires = hbe_tech_{region}_1
 unlock_unit = {row['unit']}
 {' '.join('unlock_building = '+b for b in row['buildings'])}
 ai_weight = {{ add = 20 }}
}}''')
        for lang in entries:
            entries[lang][key]=row['name'] if lang=='simp_chinese' else row['english']
            entries[lang]['hbe_has_military_'+region+'_tt']=('已研究「$'+key+'$」' if lang=='simp_chinese' else 'Has researched “$'+key+'$”.')
            entries[lang][key+'_desc']=row['description'] if lang=='simp_chinese' else 'Local muster rolls separate military training, supply and rotations from ordinary craft production. Recruitment still requires the proper maintained institution, manpower and regiment capacity.'
    triggers.append('hbe_has_regional_military_training = { OR = { '+' '.join('has_advance = '+military_key(row) for row in military)+' } }')
    triggers += ['hbe_has_military_'+row['region']+' = { custom_tooltip = { text = hbe_has_military_'+row['region']+'_tt has_advance = '+military_key(row)+' } }' for row in military]
    put(out/MIL_FILE,'\n\n'.join(military_nodes));put(out/TRIGGER_FILE,'\n'.join(triggers))

    files=['in_game/common/advances/hbe_advances.txt','in_game/common/advances/hbe_civic_advances.txt']
    def advance_edit(key,body):
        removals=[(a,b,'') for field,value,a,b in scalars(body) if (field=='unlock_unit' and value in new_units) or (field=='unlock_building' and value in building_moves and building_moves[value]!=key)]
        body=apply_edits(body,removals)
        if key in config['modifiers']:body=set_modifiers(body,config['modifiers'][key])
        if key=='hbe_tech_central_hills_1':
            body=remove_fields(body,{'unlock_building'});body+='\n unlock_building = hbe_community_granary\n'
        if key=='hbe_civic_common_1':body=set_fields(body,{'research_cost':2})
        if key=='hbe_tech_common_4':
            body=set_fields(body,{permission:'yes'});body=remove_fields(body,{'pure_tooltip_entry'})
        if re.fullmatch(r'hbe_civic_(?!common)\w+_1',key):body=set_fields(body,{'age':'age_2_renaissance','requires':'renaissance_development'})
        if key in ('hbe_civic_eastern_river_2','hbe_civic_northern_shudao_2'):
            region=key.removeprefix('hbe_civic_').removesuffix('_2');old='hbe_civic_'+region+'_1'
            body=body.replace('hbe_advance_gate_'+old+' = yes','hbe_has_military_'+region+' = yes')
            body=body.replace('has_advance = '+military_key(by_region[region]),'hbe_has_military_'+region+' = yes')
            body=set_fields(body,{'requires':'renaissance_development'})
        return re.sub(r'\n(?:[ \t]*\n){2,}', '\n\n', body)
    for rel in files:put(out/rel,rewrite(out/rel,advance_edit))

    path=out/'in_game/common/building_types/hbe_civic_buildings.txt'
    def building_edit(key,body):
        if key not in building_moves:return body
        old='hbe_tech_central_hills_3' if key=='hbe_community_granary' else 'hbe_tech_'+next(row['region'] for row in military if key in row['buildings'])+'_2'
        return re.sub(r'has_advance\s*=\s*'+re.escape(old)+r'\b','has_advance = '+building_moves[key],body)
    put(path,rewrite(path,building_edit))
    path=out/'in_game/common/unit_types/hbe_civic_units.txt'
    def unit_edit(key,body):
        if key not in by_unit:return body
        row=by_unit[key];region=row['region'];key_new=military_key(row)
        body=re.sub(r'has_advance\s*=\s*hbe_tech_'+region+r'_2\b','has_advance = '+key_new,body)
        guest='AND = { has_variable = hbe_guest_'+region+' has_advance = hbe_tech_common_4'
        if guest in body and 'hbe_has_regional_military_training = yes' not in body:body=body.replace(guest,guest+' hbe_has_regional_military_training = yes')
        return body
    put(path,rewrite(path,unit_edit))

    path=out/'in_game/common/decisions/hbe_civic_decisions.txt'
    def decision_edit(key,body):
        if key=='hbe_civic_council':body=body.replace('has_advance = hbe_civic_common_1','has_advance = hbe_tech_common_1')
        if key=='hbe_civic_garrison':body=body.replace('has_advance = hbe_civic_common_1','hbe_has_regional_military_training = yes')
        if key.startswith('hbe_guest_'):body=body.replace('has_advance = hbe_tech_common_4','modifier:'+permission+' = yes')
        return body
    put(path,rewrite(path,decision_edit))
    path=out/'in_game/common/estate_privileges/hbe_civic_privileges.txt'
    put(path,rewrite(path,lambda key,body:body.replace('has_advance = hbe_civic_common_1','has_advance = '+('hbe_tech_common_2' if key=='hbe_village_witnesses' else 'hbe_tech_common_5'))))
    path=out/'in_game/common/scripted_effects/hbe_guest_license_effects.txt';put(path,path.read_text(encoding='utf-8-sig').replace('has_advance = hbe_tech_common_4','modifier:'+permission+' = yes'))
    put(out/'main_menu/common/modifier_type_definitions/hbe_early_research.txt',permission+' = { boolean = yes game_data = { category = country } }')
    icon='gfx/interface/icons/modifier_types/'+permission+'.dds'
    put(out/'main_menu/common/modifier_icons/hbe_early_research.txt',permission+' = { positive = "'+icon+'" negative = "'+icon+'" }')
    exports=export_art(out,root,config)
    for lang,local in entries.items():
        chinese=lang=='simp_chinese';name='可以跨圈经营' if chinese else 'Can establish cross-circle industries'
        desc=('允许办理客籍议约；仍须满足当地直属土地、乡社议办、义气和费用条件。整国吞并的基础产业承继沿用原有规则。' if chinese else 'Permits guest compacts, subject to directly owned local land, communal policy, fraternity and payment. Whole-country annexation retains its existing starter-industry inheritance.')
        local.update({permission:name,'MODIFIER_TYPE_NAME_'+permission:name,'MODIFIER_TYPE_DESC_'+permission:desc})
        put(out/f'main_menu/localization/{lang}/hbe_early_research_l_{lang}.yml','l_'+lang+':\n'+'\n'.join(' '+k+': '+json.dumps(v,ensure_ascii=False) for k,v in local.items()))
        core=out/f'main_menu/localization/{lang}/hbe_l_{lang}.yml'
        changes={
            'hbe_tech_common_1_effects':'可召开本府府议；民役政策与军制须分别研究。' if chinese else 'May convene the local council; labor policy and military training require their own research.',
            'hbe_tech_common_2_effects':'开放乡社见证权；授予仍须采用乡社议办，并承担阶层政治影响。' if chinese else 'Enables village witness rights, requiring communal policy and their existing estate-power tradeoff.',
            'hbe_tech_common_4_effects':'',
            'hbe_tech_common_5_effects':'开放行会雇价保任；授予仍须采用行会雇办。' if chinese else 'Enables guild wage guarantees when guild-paid labor policy is adopted.',
            'hbe_civic_common_1_effects':'开放三种互斥的民役政策及减役补偿。驻防粮额改由地方军制开放。' if chinese else 'Enables three mutually exclusive labor policies and labor compensation. Garrison provisioning is governed by local military research.'}
        for row in military:
            region=row['region'];key='hbe_tech_'+region+'_2';base='取得本圈成长验收的课题资格。' if chinese else 'Qualifies for this circle’s growth milestone.'
            if region=='chengdu_plain':base+='\n'+('$hbe_brocade_school$基础上限两座；研究「$hbe_transmission_embroidery$」后增至三座（含在建，每处一级）。' if chinese else '$hbe_brocade_school$: initial cap two, raised to three by $hbe_transmission_embroidery$, including construction; one level per location.')
            if region=='eastern_river':base+='\n'+('江岸转运仓可使用江船备料。' if chinese else 'River warehouses may use their ordinary ship-material production.')
            changes[key+'_effects']=base
        changes['hbe_tech_central_hills_1_effects']='开放分仓义廪的基础营建与日常维护；附田生产仍须第二时代后续科技。' if chinese else 'Enables the community granary and its upkeep; agricultural production remains locked behind its later second-age advance.'
        update_localization(core,changes)
    # Synchronize the effective catalogue rather than retaining superseded unlocks.
    all_defs={}
    for rel in files+[MIL_FILE,'in_game/common/advances/hbe_industry_transmission.txt']:
        text=(out/rel).read_text(encoding='utf-8-sig');all_defs.update({k:text[a:b] for k,_,a,b,_ in blocks(text,0)})
    for row in manifest.get('technology_rewards',{}).get('advances',[]):
        body=all_defs[row['key']]
        if row['key'] in config['modifiers']:row['modifiers']=config['modifiers'][row['key']]
        row['unlocks']=[v for k,v,_,_ in scalars(body) if k=='unlock_production_method']
    for row in manifest.get('technology_rewards',{}).get('production',[]):
        owners=[key for key,body in all_defs.items() if ('unlock_production_method',row['key']) in [(k,v) for k,v,_,_ in scalars(body)]]
        if len(owners)==1:row['advance']=owners[0]
    for row in manifest['social_expansion']['buildings']:
        if row['key'] in building_moves:row['advance']=building_moves[row['key']]
    for row in manifest['social_expansion']['advances']:
        if row['key'].endswith('_1') and row['group']!='common':row.update(age='age_2_renaissance',parent='renaissance_development')
    manifest['research_nodes']=len(all_defs)
    manifest['early_research_design']={'military_count':7,'military':[dict(row,key=military_key(row)) for row in military],'building_moves':building_moves,'modifier_overrides':config['modifiers'],'permission':permission,'art':exports,'civic_first_nodes_moved_to_age_two':7,'automatic_research_grants':False}
    manifest['formables_units_v031']['date_free_advances']=list(all_defs)
    sync_catalogue(root,manifest)
    manifest['files']=snapshot_files(out);mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return manifest['early_research_design']
