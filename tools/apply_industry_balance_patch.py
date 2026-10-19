"""Industry integration, limited civilian institutions and focused UI corrections."""
from build_support import snapshot_files
from pathlib import Path
from decimal import Decimal
import re, json, sys
from pdxscript import blocks,apply_edits
GAME=Path('D:/SteamLibrary/steamapps/common/Europa Universalis V/game')
MAPPINGS={'textiles':['hbe_shu_embroidery'],'paper_goods':['hbe_shu_paper'],'beverages':['hbe_border_tea']}

def apply(out,root):
    out,root=Path(out),Path(root);changed=[];report={};loc={}
    def write(rel,t):
        p=out/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t.rstrip()+'\n',encoding='utf-8-sig');changed.append(rel)
    def L(k,cn,en=None):loc[k]=(cn,en or cn)
    # Preserve all original industries and magnitudes; goods lists drive output,
    # demand and the building list natively, including existing promotions.
    t=(GAME/'in_game/common/industry_types/01_industries.txt').read_text(encoding='utf-8-sig');edits=[]
    for name,_,s,e,_ in blocks(t,0):
        if name in MAPPINGS:
            body=t[s:e];g=next(b for b in blocks(body,0) if b[0]=='goods')
            body=apply_edits(body,[(g[3],g[3],' '+' '.join(MAPPINGS[name])+' ')])
            edits.append((s,e,body))
    t=apply_edits(t,edits)+'''\n# Salt has no original industry promotion. Use the native magnitudes.
hbe_salt_industry = {
 color = hsv { 0.12 0.30 0.80 }
 potential = { num_locations > 0 }
 goods = { salt hbe_well_salt }
 output = industry_promotion_output
 pop_demand = industry_promotion_pop_demand
}
'''
    write('in_game/common/industry_types/01_industries.txt',t)
    L('hbe_salt_industry','盐业','Salt Industry');L('hbe_salt_industry_desc','从取卤煎盐到封装运销。扶持盐业，提高本地区普通盐与井盐产出，并扩大国内采办需求。','Salt extraction, refining and distribution. Promotion increases ordinary and well-salt output in the area and domestic population demand.')
    L('beverages','酿造与茶饮业','Brewing and Tea Processing')
    L('beverages_desc','酒坊酿造与茶货加工。扶持本地酒饮与边茶生产，扩大国内饮用和采办需求。','Brewing and tea processing. Supports local beverages and border tea production and expands domestic demand.')
    report['industries']={**MAPPINGS,'hbe_salt_industry':['salt','hbe_well_salt']}

    # A national cap including construction queues, with one level per location.
    write('in_game/common/scripted_triggers/hbe_industry_patch_triggers.txt','''hbe_civil_institution_below_cap = {
 custom_tooltip = { text = hbe_civil_institution_below_cap_tt
  scope:actor = { total_building_levels_including_construction:$type$ < 3 }
 }
}
''')
    L('hbe_civil_institution_below_cap_tt','全国同类机构不足三座（含在建）；每个地点最多一级。','Fewer than three institutions of this type nationwide, including construction; one level per location.')
    p=out/'in_game/common/building_types/hbe_civic_buildings.txt';t=p.read_text(encoding='utf-8-sig');edits=[];institutions=[]
    for name,_,s,e,_ in blocks(t,0):
        body=t[s:e];category=re.search(r'\bcategory\s*=\s*(\w+)',body)
        if not category or category[1]=='military_category':continue
        if '# HBE_INDUSTRY_BALANCE_PATCH' in body:continue
        before=body
        body=re.sub(r'country_has_no_other_copy_of_building\s*=\s*\{\s*type\s*=\s*'+name+r'\s*\}','',body)
        allow=next(b for b in blocks(body,0) if b[0]=='allow')
        body=apply_edits(body,[(allow[3],allow[3],f' hbe_civil_institution_below_cap = {{ type = {name} }} ')])
        modifier=next(b for b in blocks(body,0) if b[0]=='modifier');content=body[modifier[2]:modifier[3]]
        content=re.sub(r'\b(?:can_recruit_regiment_in_this_location|max_regiments_trained_at_same_time)\s*=\s*\w+','',content)
        values=[]
        def halve(m):
            old=Decimal(m[2]);new=old/2;values.append((m[1],str(old),str(new)));return f'{m[1]} = {new.normalize():f}'
        content=re.sub(r'\b(\w+)\s*=\s*(-?\d+(?:\.\d+)?)',halve,content)
        body=apply_edits(body,[(modifier[2],modifier[3],content)])
        # Reduce premium production and its inputs proportionately, keeping
        # ordinary vanilla recipes intact and avoiding worse input margins.
        method_edits=[]
        for part in (b for b in blocks(body,0) if b[0]=='unique_production_methods'):
            methods=body[part[2]:part[3]];me=[]
            for method,_,a,z,_ in blocks(methods,0):
                recipe=methods[a:z]
                if not re.search(r'produced\s*=\s*hbe_',recipe):continue
                recipe=re.sub(r'\b(output|silk|dyes|tools|paper|lumber|salt|tea|hbe_shu_paper)\s*=\s*(\d+(?:\.\d+)?)',lambda m:f'{m[1]} = {(Decimal(m[2])*Decimal("0.6666666667")).quantize(Decimal("0.0001")).normalize():f}',recipe)
                me.append((a,z,recipe))
            if me:method_edits.append((part[2],part[3],apply_edits(methods,me)))
        body=apply_edits(body,method_edits)+'\n # HBE_INDUSTRY_BALANCE_PATCH: national cap 3, civilian modifiers 0.5x.\n'
        edits.append((s,e,body));institutions.append(dict(key=name,category=category[1],modifier_changes=values,cap=3,level_per_location=1,military_recruitment_bonuses_removed=True))
    write(p.relative_to(out).as_posix(),apply_edits(t,edits));report['institutions']=institutions

    # Display the total unconditional prestige once, preserving the net reward.
    prestige_rows=[]
    for p in (out/'in_game/events').glob('hbe_short_*.txt'):
        t=p.read_text(encoding='utf-8-sig');edits=[]
        for key,_,s,e,_ in blocks(t,0):
            if '.' not in key:continue
            event=t[s:e];oe=[]
            for _,_,a,z,_ in (b for b in blocks(event,0) if b[0]=='option'):
                body=event[a:z];matches=list(re.finditer(r'\badd_prestige\s*=\s*(-?\d+(?:\.\d+)?)',body))
                if len(matches)<2:continue
                # The short-chain generator emits these as direct option effects.
                nested=blocks(body)
                assert all(not any(x[2]<=m.start()<x[3] for x in nested) for m in matches)
                total=sum((Decimal(m[1]) for m in matches),Decimal(0))
                replacements=[(m.start(),m.end(),f'add_prestige = {total.normalize():f}' if i==0 and total else '') for i,m in enumerate(matches)]
                name=re.search(r'name\s*=\s*(\S+)',body)[1]
                oe.append((a,z,apply_edits(body,replacements)));prestige_rows.append(dict(option=name,before=[str(m[1]) for m in matches],after=str(total)))
            if oe:edits.append((s,e,apply_edits(event,oe)))
        if edits:write(p.relative_to(out).as_posix(),apply_edits(t,edits))
    report['prestige_merged']=prestige_rows

    # Genuine visible benefits on the compulsory-service policy. The existing
    # two-year burst and five-year cooldown remain unchanged.
    p=out/'in_game/common/laws/hbe_civic_law.txt';t=p.read_text(encoding='utf-8-sig')
    t=t.replace('country_modifier = { peasants_estate_target_satisfaction = -0.03 }','country_modifier = { peasants_estate_target_satisfaction = -0.03 global_construction_speed = 0.08 build_gravel_road_cost_modifier = -0.08 }')
    write(p.relative_to(out).as_posix(),t)
    L('hbe_levy_policy_desc','按府额征集工程人手。常驻建设速度+8%、碎石道路建造花费−8%，农民满意度均衡点−3%。每次地方事业交付役负+6；交付后另得两年建设速度+5%，这项临时奖励五年内只触发一次。','Compulsory public works: construction speed +8%, gravel-road cost −8%, peasants target satisfaction −3%. Each local undertaking delivered adds 6 burden. Delivery also grants +5% construction speed for two years, once every five years.')
    for language,index in [('simp_chinese',0),('english',1)]:
        header='l_simp_chinese:' if index==0 else 'l_english:'
        write(f'main_menu/localization/{language}/hbe_industry_patch_l_{language}.yml',header+'\n'+'\n'.join(f' {k}: "{v[index]}"' for k,v in loc.items()))
        # Avoid duplicate HBE keys; vanilla beverage overrides intentionally
        # replace the vanilla key, with no duplicate inside the mod itself.
        core=out/f'main_menu/localization/{language}/hbe_l_{language}.yml'
        text=core.read_text(encoding='utf-8-sig');text=re.sub(r'(?m)^ hbe_levy_policy_desc:.*\n','',text);write(core.relative_to(out).as_posix(),text)
    report['files']=sorted(set(changed));report['version']='0.3.1'
    return report

if __name__=='__main__':
    root=Path(sys.argv[1]);out=root/'mod/holy_bashu_empire';report=apply(out,root)
    p=out/'build_manifest.json';m=json.loads(p.read_text(encoding='utf-8-sig'));m['industry_patch']=report
    m['files']=snapshot_files(out)
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    dest=root/'docs/testing/industry-balance-patch-v031.json';dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(institutions=len(report['institutions']),merged_options=len(report['prestige_merged']),goods=report['industries']),ensure_ascii=False))
