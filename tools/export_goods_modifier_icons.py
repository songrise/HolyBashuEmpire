"""Register specialty modifier icons and reuse vanilla output/demand badges."""
import hashlib,json,re
from pathlib import Path
from PIL import Image,ImageFilter
import numpy as np
GOODS=('hbe_shu_embroidery','hbe_well_salt','hbe_shu_paper','hbe_border_tea')

def native_badge(folder,name,kind):
    a=np.array(Image.open(folder/(name+'.dds')).convert('RGBA'))
    r,g,b=[a[:,:,i].astype(float) for i in range(3)]
    roi=np.zeros(a.shape[:2],dtype=bool);roi[34:,34:]=True
    color=(g>r*1.25)&(g>b*1.25)&(g>20) if kind=='plus' else (r>g*1.6)&(r>b*1.6)&(r>25)
    seed=roi&(a[:,:,3]>0)&color
    mask=np.array(Image.fromarray((seed*255).astype('uint8')).filter(ImageFilter.MaxFilter(5 if kind=='demand' else 3)))>0
    mask &= ~((b>r*1.1)&(b>g*1.1))
    a[:,:,3]=np.where(mask,a[:,:,3],0);a[a[:,:,3]==0,:3]=0
    assert a[:,:,3].max()>0
    return Image.fromarray(a)

def apply(out,root,game=None):
    out,root=Path(out),Path(root)
    game=Path(game) if game else Path('D:/SteamLibrary/steamapps/common/Europa Universalis V/game')
    native=game/'main_menu/gfx/interface/icons/modifier_types'
    badges={kind:native_badge(native,name,kind) for kind,name in [('plus','fine_cloth_positive'),('minus','fine_cloth_negative'),('demand','global_fine_cloth_pop_demand')]}
    folder=out/'main_menu/gfx/interface/icons/modifier_types';folder.mkdir(parents=True,exist_ok=True)
    keys=[];definitions=out/'main_menu/common/modifier_type_definitions'
    for name in ('hbe_goods_modifiers.txt','hbe_observer_goods_types.txt'):
        keys+=re.findall(r'(?m)^([a-z_]+)\s*=\s*\{',(definitions/name).read_text(encoding='utf-8-sig'))
    assert len(set(keys))==40
    files=[];registrations=[]
    for good in GOODS:
        original=Image.open(out/f'main_menu/gfx/interface/icons/trade_goods/icon_goods_{good}.dds').convert('RGBA')
        base=Image.new('RGBA',(64,64));base.alpha_composite(original.resize((52,52),Image.Resampling.LANCZOS),(1,1))
        variants={kind:Image.alpha_composite(base,badge) for kind,badge in badges.items()}
        plain=original.resize((64,64),Image.Resampling.LANCZOS)
        aliases=[k for k in keys if good in k]+[good+'_positive',good+'_negative']
        for alias in aliases:
            kind='demand' if alias.endswith('_pop_demand') else 'minus' if alias.endswith('_negative') else 'plus' if alias.endswith(('_output_modifier','_establishment_speed','_positive')) else None
            image=variants[kind] if kind else plain
            path=folder/(alias+'.dds');image.save(path,format='DDS',pixel_format='DXT5')
            with Image.open(path) as check:assert check.size==(64,64) and check.getchannel('A').getextrema()[1]>0
            files.append(path.relative_to(out).as_posix())
        for key in keys:
            if good not in key:continue
            negative=f' negative = "gfx/interface/icons/modifier_types/{good}_negative.dds"' if key.endswith(('_output_modifier','_establishment_speed')) else ''
            registrations.append(f'{key} = {{ positive = "gfx/interface/icons/modifier_types/{key}.dds"{negative} }}')
    assert len(files)==48 and len(registrations)==40
    mapping=out/'main_menu/common/modifier_icons/hbe_goods_icons.txt';mapping.parent.mkdir(parents=True,exist_ok=True);mapping.write_text('\n'.join(registrations)+'\n',encoding='utf-8-sig');files.append(mapping.relative_to(out).as_posix())
    manifest_path=out/'build_manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    manifest['files'].update({p:hashlib.sha256((out/p).read_bytes()).hexdigest() for p in files})
    manifest['goods_modifier_icons']={'registered_modifier_types':40,'files':48,'size':[64,64],'source':'Approved specialty goods artwork with mechanically isolated original output plus/minus and demand badges','native_icon_registration':mapping.relative_to(out).as_posix(),'version':'0.3.1'}
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Registered 40 specialty modifier icons, with original output and population-demand badges.')

if __name__=='__main__':
    import sys
    root=Path(sys.argv[1]);apply(root/'mod/holy_bashu_empire',root)
