"""Grant only local starter recipes through already-signed guest certificates."""
from pathlib import Path
import re,json
from pdxscript import blocks,apply_edits

def apply(out,root=None):
    out=Path(out)
    # A practical cooperation advance replaces the century-late audit only in guest eligibility.
    decisions=out/'in_game/common/decisions/hbe_civic_decisions.txt'
    t=decisions.read_text(encoding='utf-8-sig');changes=[]
    for key,_,start,end,_ in blocks(t,0):
        if key.startswith('hbe_guest_'):
            body=t[start:end].replace('has_advance = hbe_civic_common_2','has_advance = hbe_tech_common_4')
            assert all(v in body for v in ('has_advance = hbe_tech_common_2','has_policy = hbe_communal_policy','var:hbe_yiqi >= 60','any_owned_location','gold >= hbe_paid_bill'))
            changes.append((start,end,body))
    assert len(changes)==7
    decisions.write_text(apply_edits(t,changes),encoding='utf-8-sig')
    sync=out/'in_game/common/scripted_effects/hbe_guest_license_effects.txt'
    sync.write_text(sync.read_text(encoding='utf-8-sig').replace('has_advance = hbe_civic_common_2','has_advance = hbe_tech_common_4'),encoding='utf-8-sig')
    for relative in ('in_game/common/building_types/hbe_civic_buildings.txt','in_game/common/unit_types/hbe_civic_units.txt','in_game/common/scripted_effects/hbe_civic_effects.txt'):
        p=out/relative;t=p.read_text(encoding='utf-8-sig');changes=[]
        for key,_,start,end,_ in blocks(t):
            body=t[start:end]
            if key=='AND' and re.search(r'has_variable\s*=\s*hbe_guest_\w+',body) and 'has_advance = hbe_civic_common_2' in body:
                assert '{' not in body,'Only change flat guest-qualified branches'
                changes.append((start,end,body.replace('has_advance = hbe_civic_common_2','has_advance = hbe_tech_common_4')))
        if changes:p.write_text(apply_edits(t,changes),encoding='utf-8-sig')
    path=out/'in_game/common/advances/hbe_guest_licenses.txt'
    text=path.read_text(encoding='utf-8-sig')
    building_text=(out/'in_game/common/building_types/hbe_civic_buildings.txt').read_text(encoding='utf-8-sig')
    recipes={key for key,_,_,_,_ in blocks(building_text) if re.fullmatch(r'hbe_\w+_(?:basic|ordinary)_production',key)}
    rows=[];edits=[]
    for key,_,start,end,_ in blocks(text,0):
        if not key.startswith('hbe_guest_license_'):continue
        region=key.removeprefix('hbe_guest_license_');body=text[start:end]
        assert 'potential = { has_variable = hbe_guest_'+region+' }' in body
        assert 'allow = { always = no }' in body
        body=body.replace('age = age_2_renaissance','age = age_1_traditions').replace('requires = hbe_civic_common_2','requires = hbe_tech_common_4')
        methods=[f'hbe_{region}_{tier}_production' for tier in ('basic','ordinary') if f'hbe_{region}_{tier}_production' in recipes]
        assert methods and methods[0].endswith('_basic_production'),region
        original=re.findall(r'\bunlock_production_method\s*=\s*(\w+)',body)
        assert set(original)<=set(methods),(key,original)
        for method in methods:
            if method not in original:body+='\n unlock_production_method = '+method+'\n'
        edits.append((start,end,body));rows.append(dict(region=region,certificate=key,methods=methods))
    assert len(rows)==7 and sum(len(x['methods']) for x in rows)==11
    path.write_text(apply_edits(text,edits),encoding='utf-8-sig')
    for lang in ('simp_chinese','english'):
        p=out/f'main_menu/localization/{lang}/hbe_l_{lang}.yml';t=p.read_text(encoding='utf-8-sig')
        for row in rows:
            key=row['certificate']+'_desc'
            desc='本府已承认当地旧约，取得该圈机构、基础生产方式及基础军制的使用资格。营建与生产仍须在该圈土地进行，并维持机构供养；高级工艺仍须另行解锁。这份凭据不授予地区科技的数值加成。' if lang=='simp_chinese' else 'A signed guest compact grants access to this circle’s institutions, starter production methods and basic military system. Construction and production remain confined to its lands and require funded institutions. Advanced recipes retain their own unlocks; regional technology bonuses are not granted.'
            t,n=re.subn(r'(?m)^ '+re.escape(key)+r':.*$',lambda _: ' '+key+': '+json.dumps(desc,ensure_ascii=False),t)
            assert n==1,key
            decision='hbe_guest_'+row['region']
            for suffix in ('.desc','.desc.entry'):
                key=decision+suffix
                desc='整合一处旧府州，并不等于掌握当地所有技艺。本府愿认可旧日见证，承担机构维护，并请当地承办者依原约保留本业。\n\n研究「匠人互访」与「统一度量」，采用「乡社议办」，义气达到60，并拥有该圈至少一处直属土地后，可签订客籍议约。支付按月税贸收入75%计算的雇办费（最低3金币），消耗10义气，取得当地机构、基础生产方式及基础军制资格。营建仍限该圈土地，高级工艺须另行解锁，不复制地区科技的数值加成。' if lang=='simp_chinese' else 'Holding a former prefecture does not confer all its crafts. Recognize local contracts and support the institutions that preserve them.\n\nResearch Craftsmen Exchanges and Common Measures, adopt Communal Deliberation, reach 60 Fraternity and directly own at least one location in this circle. Sign the guest compact for 75% of monthly tax and trade income (minimum 3 gold) and 10 Fraternity. It grants local institutions, starter recipes and basic military access. Regional building restrictions and advanced recipe requirements remain; regional technology bonuses are not granted.'
                t,n=re.subn(r'(?m)^ '+re.escape(key)+r':.*$',lambda _: ' '+key+': '+json.dumps(desc,ensure_ascii=False),t)
                assert n==1,key
        guest_tooltip='开放跨圈经营：满足条件并签订客籍议约后，可在目标圈建造机构并经营基础产业。' if lang=='simp_chinese' else 'Enables cross-circle industry through guest compacts. Meet the compact requirements to build local institutions and operate starter industries in the target circle.'
        t,n=re.subn(r'(?m)^ hbe_tech_common_4_effects:.*$',lambda _: ' hbe_tech_common_4_effects: '+json.dumps(guest_tooltip,ensure_ascii=False),t)
        assert n==1,'Craftsmen Exchanges native technology tooltip'
        p.write_text(t,encoding='utf-8-sig')
    return dict(version='0.3.1',regions=7,starter_recipe_unlocks=11,certificates=rows,guest_prerequisite='hbe_tech_common_4 (Craftsmen Exchanges), replacing the 1437 audit in guest eligibility only.',unchanged='Opening eligibility, direct regional land ownership, Common Measures, Communal policy, 60 fraternity, fees, geography, building caps, advanced recipe unlocks and regional technology bonuses.')
