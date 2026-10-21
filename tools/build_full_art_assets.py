"""Export painted shared scenes, organization art and decision sprite atlases."""
from build_support import sha256_file as sha, save_png
import json, re
from PIL import Image,ImageDraw,ImageFont,ImageOps
from pdxscript import blocks,apply_edits
from build_flags import save_dds
from build_icon_assets import fit

REGION_SCENES={'chengdu_plain':'water','southern_salt_wine':'salt','eastern_river':'river','northern_shudao':'roads','central_hills':'grain','western_tea_horse':'tea','southwestern_valleys':'valleys'}


def build_full_art_assets(out,root,countries,regions,put,game):
    registry=json.loads((root/'assets/full_art_generation.json').read_text(encoding='utf-8'))
    scenes={};exports=[]
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',24)
    proof=Image.new('RGB',(2160,6*492),'#302a23');draw=ImageDraw.Draw(proof)
    for i,entry in enumerate(registry['scenes']):
        key=entry['key'];image=Image.open(root/entry['source']).convert('RGBA')
        if abs(image.width/image.height-1080/440)>.08:raise ValueError('Unexpected scene proportions: '+key)
        image=ImageOps.fit(image,(1080,440),Image.Resampling.LANCZOS)
        target=out/'main_menu/gfx/interface/hbe/events'/f'{key}.dds';save_dds(target,image)
        scenes[key]=image
        proof.paste(image.convert('RGB'),((i%2)*1080,(i//2)*492));draw.text(((i%2)*1080+12,(i//2)*492+446),entry['name'],font=font,fill='#ead59b')
        exports.append(dict(kind='event_background',key=key,image=target.relative_to(out).as_posix(),sha256=sha(target)))
    assert len(scenes)==12
    proof.save(root/'assets/event_illustrations_preview.png')
    # Private native scene definitions retain EU5 portrait, lighting and paint layers.
    native=(game/'in_game/gfx/scenes/00_scenes_events.txt').read_text(encoding='utf-8-sig')
    first=next(b for b in blocks(native,0) if b[0]=='characters_regular_interior')
    template=native[first[2]:first[3]]
    scene_defs=[];illustration_defs=[];image_lists=[]
    for key in scenes:
        scene_defs.append('hbe_event_scene_'+key+' = {'+template.replace('list = "interior_backgrounds"',f'list = "hbe_event_background_{key}"')+'}')
        illustration_defs.append(f'hbe_event_illustration_{key} = {{ scene = "hbe_event_scene_{key}" tags = {{ 1000 = hbe_event_art_{key} }} }}')
        image_lists.append(f'hbe_event_background_{key} = {{ tag = "hbe_event_background_{key}" illustration_image = {{ texture_file = "gfx/interface/hbe/events/{key}.dds" priority = 100 scope = country trigger = {{ always = yes }} }} }}')
    put('in_game/gfx/scenes/hbe_event_scenes.txt','\n'.join(scene_defs))
    put('loading_screen/gfx/illustrations/database/hbe_event_illustrations.txt','\n'.join(illustration_defs))
    put('in_game/gfx/images/hbe_event_backgrounds.txt','\n'.join(image_lists))
    catalog={e['id']:e for e in json.loads((root/'data/events_v002.json').read_text(encoding='utf-8'))}
    region_names={r[1]:REGION_SCENES[r[0]] for r in regions};tag_regions={c['tag']:REGION_SCENES[c['region']] for c in countries};country_names={c['name']:REGION_SCENES[c['region']] for c in countries}
    events=[]
    for path in sorted((out/'in_game/events').glob('hbe*events.txt')):
        s=path.read_text(encoding='utf-8-sig');edits=[]
        for key,_,a,b,_ in blocks(s,0):
            if not re.fullmatch(r'hbe(?:_banquet)?\.\d+',key):continue
            body=s[a:b];entry=catalog.get(key);scene='council';title=key
            if entry:
                title=entry['title'];category=entry['category']
                if category in region_names:scene=region_names[category]
                elif category in country_names:scene=country_names[category]
                elif category=='generational':scene=['banquet','ledger','council','roads','tea','council','council'][(int(key.split('.')[1])-30)%7]
                elif category in ('accounts',):scene='banquet'
                elif category in ('default','ledger','delivery'):scene='ledger'
                elif category=='crisis':scene='crisis'
                if key=='hbe_banquet.4':scene='river'
                if key=='hbe_banquet.5':scene='crisis'
            else:
                eid=int(key.split('.')[1])
                if 100<=eid<=106:scene=REGION_SCENES[regions[eid-100][0]]
                elif eid==2:scene='academy'
                elif eid in (3,4):scene='ledger'
                elif eid==5:scene='banquet'
                elif eid==13:scene='tea'
            inner=next(v for v in blocks(body,0) if v[0]=='illustration_tags')
            edits.append((a+inner[2],a+inner[3],f' 1000 = hbe_event_art_{scene} '))
            events.append(dict(id=key,title=title,scene=scene))
        put(path.relative_to(out).as_posix(),apply_edits(s,edits))
    assert len(events)==96 and len({e['id'] for e in events})==96
    # Native organization artwork is resolved by the organization type's filename.
    org_proof=Image.new('RGB',(1600,260),'#302a23');op=ImageDraw.Draw(org_proof);small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
    organizations=[]
    for i,entry in enumerate(registry['organizations']):
        key=entry['key'];sprite=fit(Image.open(root/entry['source']),128)
        target=out/'main_menu/gfx/interface/icons/international_organizations'/f'{key}.dds';save_dds(target,sprite)
        scene='council' if key=='hbe_empire' else REGION_SCENES[key.removeprefix('hbe_circle_')]
        panel=out/'main_menu/gfx/interface/illustrations/international_organization_types'/f'{key}.dds';save_dds(panel,scenes[scene])
        organizations.append(dict(key=key,icon=target.relative_to(out).as_posix(),icon_sha256=sha(target),panel=panel.relative_to(out).as_posix(),panel_sha256=sha(panel),shared_scene=scene))
        thumb=sprite.resize((160,160),Image.Resampling.LANCZOS);org_proof.paste(thumb,(i*200+20,20),thumb);op.text((i*200+10,190),entry['name'],font=small,fill='#ead59b')
    assert len(organizations)==8
    org_proof.save(root/'assets/organization_emblems_preview.png')
    hero=registry['situation_panel'];picture=ImageOps.fit(Image.open(root/hero['source']).convert('RGBA'),(1080,440),Image.Resampling.LANCZOS)
    target=out/'main_menu/gfx/interface/hbe/panels/hbe_banquet.dds';save_dds(target,picture)
    gui=out/'in_game/gui/panels/situation/hbe_banquet.gui';put(gui.relative_to(out).as_posix(),gui.read_text(encoding='utf-8-sig').replace('gfx/interface/hbe/placeholder.dds','gfx/interface/hbe/panels/hbe_banquet.dds'))
    picture.save(root/'assets/situation_panel_preview.png')
    # Seven 5x2 sheets supply all non-research decision pictures.
    decisions=[];decision_proof=Image.new('RGB',(1500,7*210+60),'#302a23');dd=ImageDraw.Draw(decision_proof);label=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',12)
    for row,sheet in enumerate(registry['decision_sheets']):
        atlas=Image.open(root/sheet['source']).convert('RGBA')
        if atlas.getchannel('A').getextrema()[0]!=0:raise ValueError('Decision atlas must be transparent')
        for i,cell in enumerate(sheet['cells']):
            key=cell['key'];box=(round(i%5*atlas.width/5),round(i//5*atlas.height/2),round((i%5+1)*atlas.width/5),round((i//5+1)*atlas.height/2))
            sprite=fit(atlas.crop(box),192);card=Image.new('RGBA',(384,192));card.alpha_composite(sprite,(96,0))
            target=out/'main_menu/gfx/interface/hbe/decisions'/f'{key}.dds';save_dds(target,card)
            png=root/'assets/decision_pictures'/f'{key}.png';save_png(png,card)
            decisions.append(dict(key=key,name=cell['name'],image=target.relative_to(out).as_posix(),sha256=sha(target),atlas=sheet['source'],cell=i,crop=list(box)))
            thumb=sprite.resize((130,130),Image.Resampling.LANCZOS);decision_proof.paste(thumb,(i*150+10,row*210+24),thumb)
            dd.text((i*150+5,row*210+160),cell['name'][:11],font=label,fill='#ead59b');dd.text((i*150+5,row*210+178),cell['name'][11:22],font=label,fill='#ead59b')
    assert len(decisions)==70 and len({e['key'] for e in decisions})==70 and len({e['sha256'] for e in decisions})==70
    for path in (out/'in_game/common/decisions').glob('hbe*decisions.txt'):
        s=path.read_text(encoding='utf-8-sig');edits=[]
        for key,_,a,b,_ in blocks(s,0):
            if key.startswith('hbe_tech_'):continue
            match=re.search(r'image\s*=\s*"[^"]+"',s[a:b]);assert match,key
            edits.append((a+match.start(),a+match.end(),f'image = "gfx/interface/hbe/decisions/{key}.dds"'))
        put(path.relative_to(out).as_posix(),apply_edits(s,edits))
    decision_proof.save(root/'assets/decision_pictures_preview.png')
    result=dict(mode='built-in image_gen',event_backgrounds=exports,event_mapping=events,organizations=organizations,situation_panel=dict(image='main_menu/gfx/interface/hbe/panels/hbe_banquet.dds',sha256=sha(out/'main_menu/gfx/interface/hbe/panels/hbe_banquet.dds')),decision_atlases=7,decision_pictures=decisions,source_manifest='assets/full_art_generation.json',style='restrained EU5 painted illustration; visibly reduced photorealism')
    (root/'data/art_v01.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result
