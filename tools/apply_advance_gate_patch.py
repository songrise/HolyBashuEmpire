"""Use actual same-age tree edges; preserve compound/cross-age conditions."""
from pathlib import Path
import re,json,hashlib,sys
from pdxscript import blocks,apply_edits,tokens
GAME=Path('D:/SteamLibrary/steamapps/common/Europa Universalis V/game')

def apply(out,root):
    out=Path(out);catalog={};files=list((GAME/'in_game/common/advances').glob('*.txt'))+list((out/'in_game/common/advances').glob('*.txt'))
    for p in files:
        if p.name=='readme.txt':continue
        t=p.read_text(encoding='utf-8-sig')
        for name,_,s,e,_ in blocks(t,0):
            body=t[s:e];age=re.search(r'\bage\s*=\s*(\w+)',body);parent=re.search(r'\brequires\s*=\s*(\w+)',body)
            if age:catalog[name]=dict(age=age[1],parent=parent[1] if parent else None,allows_children=not bool(re.search(r'allow_children\s*=\s*no',body)))
    def ancestor(child,parent):
        seen=set()
        while child in catalog and child not in seen:
            if child==parent:return True
            seen.add(child);child=catalog[child]['parent']
        return False
    def direct_gates(body):
        ts=tokens(body);stack=[];out=[]
        for i,t in enumerate(ts):
            if t.value=='{':stack.append(ts[i-2].value if i>=2 and ts[i-1].value=='=' else '')
            elif t.value=='}':stack.pop()
            elif t.value=='has_advance' and i+2<len(ts) and ts[i+1].value=='=':
                out.append((t.start,ts[i+2].end,ts[i+2].value,tuple(stack)))
        return out
    gate_ids=set();rows=[];changed=[]
    for p in (out/'in_game/common/advances').glob('hbe*.txt'):
        t=p.read_text(encoding='utf-8-sig');edits=[]
        for name,_,s,e,_ in blocks(t,0):
            body=t[s:e];gates=direct_gates(body)
            if not gates:continue
            before=body;parent=catalog[name]['parent'];age=catalog[name]['age'];native=[];replacements=[]
            # A direct AND gate descending from the existing parent can become
            # the real tree parent without weakening any previous requirement.
            candidates=[g[2] for g in gates if g[3] in (('allow',),('potential',)) and g[2] in catalog and catalog[g[2]]['age']==age and catalog[g[2]]['allows_children'] and ancestor(g[2],parent)]
            target=parent
            for candidate in candidates:
                if ancestor(candidate,target):target=candidate
            if target!=parent:
                body=re.sub(r'\brequires\s*=\s*'+re.escape(parent)+r'\b','requires = '+target,body,count=1)
            for a,z,advance,context in direct_gates(body):
                if context in (('allow',),('potential',)) and ancestor(target,advance):
                    replacements.append((a,z,''));native.append(advance)
                else:
                    gate_ids.add(advance);replacements.append((a,z,'hbe_advance_gate_'+advance+' = yes'))
            body=apply_edits(body,replacements)
            edits.append((s,e,body));rows.append(dict(advance=name,age=age,parent_before=parent,parent_after=target,redundant_direct_gates_removed=native,compound_gate_count=len(replacements)-len(native)))
        if edits:p.write_text(apply_edits(t,edits),encoding='utf-8-sig');changed.append(p.relative_to(out).as_posix())
    path=out/'in_game/common/scripted_triggers/hbe_advance_gates.txt';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text('\n'.join(f'hbe_advance_gate_{name} = {{ custom_tooltip = {{ text = hbe_advance_gate_{name}_tt has_advance = {name} }} }}' for name in sorted(gate_ids))+'\n',encoding='utf-8-sig');changed.append(path.relative_to(out).as_posix())
    for language in ('simp_chinese','english'):
        p=out/f'main_menu/localization/{language}/hbe_advance_gates_l_{language}.yml'
        header='l_simp_chinese:' if language=='simp_chinese' else 'l_english:'
        lines=[header]
        for name in sorted(gate_ids):
            label=f'已研究「${name}$」' if language=='simp_chinese' else f'Has researched “${name}$”.'
            lines.append(f' hbe_advance_gate_{name}_tt: "{label}"')
        p.write_text('\n'.join(lines)+'\n',encoding='utf-8-sig');changed.append(p.relative_to(out).as_posix())
    return dict(version='0.3.1',nodes=len(rows),rows=rows,compound_native_conditions=sorted(gate_ids),files=changed,note='Same-age implied prerequisites use requires. Cross-age, OR and NOT gates remain immediate native has_advance checks in named triggers, with no monthly flags or delayed synchronization.')

if __name__=='__main__':
    root=Path(sys.argv[1]);out=root/'mod/holy_bashu_empire';r=apply(out,root)
    (root/'docs/testing/advance-gate-patch-v031.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    p=out/'build_manifest.json';m=json.loads(p.read_text(encoding='utf-8-sig'));m['advance_gate_patch']=r;m['files']={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.name!='build_manifest.json'};p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(nodes=r['nodes'],real_tree_parent_changes=sum(x['parent_before']!=x['parent_after'] for x in r['rows']),compound_conditions=len(r['compound_native_conditions'])),ensure_ascii=False))
