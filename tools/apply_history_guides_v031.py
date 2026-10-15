"""Append sourced historical concepts and a few explicit inline links."""
from pathlib import Path
import argparse,hashlib,json,re,sys

def apply(out,root,game=None):
 out,root=Path(out),Path(root);sys.path.insert(0,str(root/'data'))
 from history_guides_v031 import GUIDES,ANCHORS,SOURCES,VERIFIED_ON
 changed=[];linked=[]
 def put(rel,text,newline='\r\n'):
  p=out/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text.rstrip()+'\n',encoding='utf-8-sig',newline=newline);changed.append(rel)
 def cid(key):return key if key.startswith('hbe_history_') else 'hbe_history_'+key
 put('main_menu/common/game_concepts/hbe_history_v031.txt','\n'.join(cid(g[0])+' = { }' for g in GUIDES))
 for lang in ('simp_chinese','english'):
  loc={}
  for key,zh,body,en,enbody,sources in GUIDES:
   loc['game_concept_'+cid(key)]=zh if lang=='simp_chinese' else en
   loc['game_concept_'+cid(key)+'_desc']=('#T 历史背景#!\n'+body) if lang=='simp_chinese' else '#T Historical background#!\n'+enbody
  put(f'main_menu/localization/{lang}/hbe_history_v031_l_{lang}.yml','l_'+lang+':\n'+'\n'.join(' '+k+': '+json.dumps(v,ensure_ascii=False) for k,v in loc.items()))
  for family,name in (('base',f'hbe_l_{lang}.yml'),('story',f'hbe_story_l_{lang}.yml')):
   rel=f'main_menu/localization/{lang}/'+name;p=out/rel;raw=p.read_bytes();text=raw.decode('utf-8-sig');ending='\r\n' if b'\r\n' in raw else '\n';rows=text.splitlines();index={}
   for i,line in enumerate(rows):
    m=re.match(r'\s*([^:\s]+):\s*(?:\d+\s*)?(".*")$',line)
    if m:index[m[1]]=(i,json.loads(m[2]))
   for fam,key,phrase,concept in ANCHORS:
    if fam!=family:continue
    i,value=index[key];target=cid(concept);link=f"[Concept('{target}', '{phrase}')|e]"
    if link not in value:
     # Existing native expressions must remain intact. Match one plain-text
     # occurrence outside any [...] expression, keeping the visible wording.
     parts=re.split(r'(\[[^\]]*\])',value);done=False
     for j,part in enumerate(parts):
      if not done and not part.startswith('[') and phrase in part:parts[j]=part.replace(phrase,link,1);done=True
     assert done,(lang,key,phrase)
     value=''.join(parts)
    rows[i]=' '+key+': '+json.dumps(value,ensure_ascii=False);index[key]=(i,value)
    linked.append(dict(language=lang,file=rel,key=key,label=phrase,concept=target))
   put(rel,'\n'.join(rows),newline=ending)
 report=dict(verified_on=VERIFIED_ON,new_concepts=len(GUIDES),new_links_per_language=sum(not a[3].startswith('hbe_history_') for a in ANCHORS),reused_links_per_language=sum(a[3].startswith('hbe_history_') for a in ANCHORS),linked_entries_per_language=len({a[1] for a in ANCHORS}),source_count=len(SOURCES),english_concepts_translated=True,linked=linked,files=changed,gameplay_changes=False)
 mp=out/'build_manifest.json';m=json.loads(mp.read_text(encoding='utf-8'));m['history_guides_v031']={k:v for k,v in report.items() if k not in ('linked','files')}
 m['files']={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.name!='build_manifest.json'}
 mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (root/'data/history_guides_v031.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 doc=['# 0.3 以来新增内容的历史悬浮指南','',f'本轮新增 {len(GUIDES)} 条历史指南，在每种语言中选取 18 处正文与商品说明设置 19 个链接，其中 4 个复用原有指南。只补真实历史背景，不改事件叙事和奖惩。核对日期：{VERIFIED_ON}。','', '## 条目与出处','']
 for key,zh,body,en,enbody,sources in GUIDES:
  doc+=['### '+zh,'',body,'','English: '+enbody,'','出处：'+ '；'.join(f'[{SOURCES[s]["publisher"]}：{SOURCES[s]["title"]}]({SOURCES[s]["url"]})' for s in sources)+'。','']
 doc+=['## 接入位置','','| 文本键 | 悬停词语 | 指南 |','| --- | --- | --- |']
 names={cid(g[0]):g[1] for g in GUIDES};names.update(hbe_history_qiong='邛窑',hbe_history_shudao='蜀道',hbe_history_river='川江',hbe_history_jianmen='剑门关')
 for family,key,phrase,target in ANCHORS:doc.append(f'| `{key}` | {phrase} | {names[cid(target)]} |')
 doc+=['','没有给普通的田租、工钱、师徒、仓房等叙事词汇另建词条；没有为虚构人物和具体纠纷添加史实身份。已有指南保留原文。','']
 (root/'docs/history_guides_v031.md').write_text('\n'.join(doc),encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k not in ('linked','files')},ensure_ascii=False));return report

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);a=ap.parse_args();apply(a.root/'mod/holy_bashu_empire',a.root)
