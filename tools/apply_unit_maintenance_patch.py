"""500-man specialty regiments, 90% of their existing per-strength upkeep."""
from pathlib import Path
from decimal import Decimal
import re
from pdxscript import blocks,apply_edits
GAME=Path('D:/SteamLibrary/steamapps/common/Europa Universalis V/game')
def apply(out,root=None):
    out=Path(out);p=out/'in_game/common/unit_types/hbe_civic_units.txt';t=p.read_text(encoding='utf-8-sig')
    native=(GAME/'in_game/common/goods_demand/army_demands.txt').read_text(encoding='utf-8-sig')
    recipes={key:native[s:e] for key,_,s,e,_ in blocks(native,0)};edits=[];new={};rows=[]
    for key,_,s,e,_ in blocks(t,0):
        body=t[s:e];before=re.search(r'max_strength\s*=\s*(\S+)',body)[1]
        template=re.search(r'copy_from\s*=\s*(\S+)',body)[1]
        age=Decimal(re.search(r'a_age_(\d)_',template)[1])
        inherited=age*(Decimal('.2') if 'light_cavalry' in template else Decimal('.5'))
        strength_delta=Decimal('.5')-inherited
        body=re.sub(r'max_strength\s*=\s*\S+','max_strength = '+f'{strength_delta.normalize():f}',body)
        recipe=re.search(r'maintenance_demand\s*=\s*(\S+)',body)[1].removeprefix('hbe_discount_')
        # Later military stages own their equipment surcharge recipes.
        if recipe not in recipes:
            assert recipe.startswith('hbe_age2_'),recipe
            edits.append((s,e,body))
            rows.append(dict(unit=key,max_strength='0.5',inherited_strength=str(inherited),strength_delta=str(strength_delta),men=500,original_recipe=recipe))
            continue
        body=re.sub(r'maintenance_demand\s*=\s*\S+','maintenance_demand = hbe_discount_'+recipe,body)
        new[recipe]=re.sub(r'(?m)^(\s*\w+\s*=\s*)(\d+(?:\.\d+)?)',lambda m:m[1]+f'{(Decimal(m[2])*Decimal(".9")).normalize():f}',recipes[recipe])
        edits.append((s,e,body));rows.append(dict(unit=key,before_max_strength=before,max_strength='0.5',inherited_strength=str(inherited),strength_delta=str(strength_delta),men=500,upkeep_factor=.9,original_recipe=recipe))
    assert len(rows)==len(blocks(t,0))
    p.write_text(apply_edits(t,edits),encoding='utf-8-sig')
    p=out/'in_game/common/goods_demand/hbe_unit_maintenance.txt'
    p.write_text('# Private recipes; vanilla maintenance definitions remain unchanged.\n'+'\n'.join('hbe_discount_'+key+' = {'+body+'}\n' for key,body in new.items()),encoding='utf-8-sig')
    for lang,inf,cav in [('simp_chinese','特色步兵维护','特色骑兵维护'),('english','Specialty Infantry Maintenance','Specialty Cavalry Maintenance')]:
        p=out/f'main_menu/localization/{lang}/hbe_unit_maintenance_l_{lang}.yml'
        p.write_text(f'l_{lang}:\n hbe_discount_early_infantry_maintenance: "{inf}"\n hbe_discount_cavalry_maintenance: "{cav}"\n',encoding='utf-8-sig')
    return dict(version='0.3.1',units=rows,maintenance_factor=.9)
