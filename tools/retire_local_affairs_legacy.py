"""Remove the retired service loop after legacy content generators have run."""
import re

from build_support import write_preserving_format
from pdxscript import blocks, apply_edits


def apply(out, put, regions):
    groups = [r[0] for r in regions]
    obsolete = ['hbe_service_cooldown', 'hbe_project_pending', 'hbe_project_timer']
    for group in groups:
        obsolete += [f'hbe_service_{group}_pending', f'hbe_service_{group}_timer', f'hbe_recent_delivery_{group}']
    cleanup = ' '.join('remove_variable = '+v for v in obsolete)
    put('in_game/common/scripted_effects/hbe_af_legacy_effects.txt',
        'hbe_af_retire_legacy_country = { if = { limit = { NOT = { has_variable = hbe_af_legacy_retired_v1 } } '+cleanup+' set_variable = hbe_af_legacy_retired_v1 } }')

    # Drop only if branches whose own limit tests an obsolete pending order.
    # Enclosing monthly country/organization logic remains intact.
    pending = re.compile(r'\bhas_variable\s*=\s*(?:hbe_service_\w+_pending|hbe_project_pending)\b')
    for rel in ('in_game/common/scripted_effects/hbe_effects.txt',
                'in_game/common/on_action/hbe_simple_banquet_on_actions.txt'):
        path = out/rel
        text = path.read_text(encoding='utf-8-sig')
        edits = []
        for key, start, a, b, end in blocks(text):
            if key != 'if': continue
            body = text[a:b]
            limit = next((body[x:y] for k, _, x, y, _ in blocks(body, 0) if k == 'limit'), '')
            if pending.search(limit): edits.append((start, end, ''))
        write_preserving_format(path, apply_edits(text, edits))

    for path in (out/'in_game').rglob('*.txt'):
        if path.name.startswith('hbe_af_'): continue
        text = path.read_text(encoding='utf-8-sig')
        original = text
        if path.name == 'hbe_decisions.txt':
            edits = []
            for key, _, a, b, _ in blocks(text, 0):
                if not key.startswith('hbe_service_'): continue
                body = text[a:b]
                patches = []
                for field, start, x, y, end in blocks(body, 0):
                    if field in ('potential', 'allow'):
                        patches.append((x,y,' always = no '))
                    elif field == 'option':
                        patches.append((x,y,f' name = {key}.a ai_chance = {{ value = 100 }} effect = {{ }} '))
                edits.append((a,b,apply_edits(body,patches)))
            text = apply_edits(text, edits)
        if path.name == 'hbe_civic_decisions.txt':
            edits = []
            for key, _, a, b, _ in blocks(text, 0):
                if not key.startswith('hbe_coordinate_'): continue
                body = text[a:b]
                potential = next(x for x in blocks(body, 0) if x[0] == 'potential')
                body = apply_edits(body, [(potential[2],potential[3],' always = no ')])
                edits.append((a,b,body))
            text = apply_edits(text, edits)
        if path.name == 'hbe_civic_effects.txt':
            edits = [(start,end,'') for key,start,_,_,end in blocks(text,0)
                     if key.startswith(('hbe_record_service_', 'hbe_pay_service_'))]
            text = apply_edits(text, edits)
        if path.name == 'hbe_civic_advances.txt':
            text = re.sub(r'\bpure_tooltip_entry\s*=\s*hbe_civic_(?:'+'|'.join(groups)+r')_[12]_effects\b','',text)
        if path.name in ('hbe_simple_banquet_effects.txt','hbe_banquet_effects.txt'):
            edits=[]
            for key,_,a,b,_ in blocks(text,0):
                if key in ('hbe_feast_help','hbe_deliver_contract'):
                    # Keep saved event/function references resolvable without rewards.
                    edits.append((a,b,' hbe_af_retire_legacy_country = yes '))
            text=apply_edits(text,edits)
        # Retired hidden feast proposals must not depend on, or recreate, old orders.
        text=re.sub(r'\bNOT\s*=\s*\{\s*any_country\s*=\s*\{\s*has_variable\s*=\s*hbe_project_pending\s*\}\s*\}', '', text)
        obsolete_names = set(obsolete)
        edits=[]
        for key,start,a,b,end in blocks(text):
            if key != 'set_variable': continue
            name=re.search(r'\bname\s*=\s*(\w+)',text[a:b])
            if name and name[1] in obsolete_names: edits.append((start,end,''))
        text=apply_edits(text,edits)
        # Remove obsolete requirements outright; do not substitute another grind.
        old = r'(?:hbe_recent_delivery_\w+|hbe_service_cooldown)'
        text = re.sub(r'\bNOT\s*=\s*\{\s*has_variable\s*=\s*'+old+r'\s*\}', '', text)
        text = re.sub(r'\bhas_variable\s*=\s*'+old+r'\b', '', text)
        if text != original: write_preserving_format(path,text)

    replacements = {
        'hbe_levy_policy_desc': '按府额征集人手。地方项目役负投入提高25%；政令带来营建便利，也增加乡里负担。',
        'hbe_communal_policy_desc': '由乡社见证分摊与期限，按项目列示承担役负；驻防粮额沿用议约。',
        'hbe_paid_policy_desc': '由行会承办项目，地方项目役负投入降低50%；金币费用按项目面板列示。',
        'hbe_banquet_ledger.desc': '查看两派成员、本届贡献与收益。成员悬浮列示出资及项目贡献。',
        'hbe_banquet_ledger.desc.entry': '查看两派成员、本届贡献与收益。成员悬浮列示出资及项目贡献。',
        'game_concept_hbe_term_regional_desc': '本圈机构、产业与项目成果共同构成地方经营。具体资格由相关科技、建筑与决议列示。',
        'game_concept_hbe_term_service_desc': '在地方事业面板选择全国或地方项目，确定投入后自动施工。费用、工期与预计成果由项目列示；完工发放实际成果并计入本届贡献。',
        'game_concept_hbe_term_mission_desc': '每圈五个验收阶段。满足前置阶段、研究及列示的经营条件后，支付金币并承担2点役负。验收增加义气、共同信用与威望，各阶段只能完成一次。',
        'game_concept_hbe_term_delivery_desc': '项目完工后的实际成果记入本届贡献；各国记录可在大开席成员行悬浮查看。',
        'game_concept_hbe_term_civic_office_desc': '须满足委任科技、成长验收及机构运转等列示条件。每圈同时一位主持，每国至多两任，任期五年；断供、退盟或役负达到70会提前退任。',
    }
    old_resource = r'@hbe_(?:water|salt|river|roads|grain|tea|valleys)!\s*\[Concept\([^\]]*\)\|e\]'
    for path in (out/'main_menu/localization').rglob('hbe_l_*.yml'):
        lines=[]
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            match=re.match(r'\s*([^:]+):',line)
            key=match[1] if match else ''
            value=None
            if key in replacements: value=replacements[key]
            elif re.fullmatch(r'hbe_service_\w+\.desc(?:\.entry)?',key):
                value='请在地方事业面板选择项目并筹办。'
            elif re.fullmatch(r'hbe_civic_(?:'+ '|'.join(groups)+r')_[12]_effects',key):
                continue # Their only hook described retired completion rewards.
            if value is not None: line=' '+key+': "'+value+'"'
            if key.startswith('hbe_mission_'):
                line=re.sub(r'消耗\s*10\s*点'+old_resource+r'和\s*\d+\s*金币', '支付列示金币并承担2点役负',line)
                line=line.replace('需要研究、持续交付与真实出资','需要研究与本圈经营资格')
            if key.startswith(('hbe_coordinate_','hbe_seek_')):
                line=line.replace('本届地方储备与','本府财力与').replace('五年内完成本圈事业','本圈机构正常运转')
            if key in ('hbe_term_burden_desc','game_concept_hbe_term_burden_desc'):
                line=line.replace('事业征办+6、议办+2、雇办不增加','地方项目役负按投入档次列示，征办提高25%，雇办降低50%')
            if key == 'game_concept_hbe_term_charter_divided_desc':
                line=re.sub(r'；地区\[Concept\([^\]]+\)\|e\]交付追加2声望','',line)
                line=re.sub(r'\\n\\n它不会免费提供.*?(?="$)','',line)
            if key.endswith('_desc') and key.startswith(('hbe_village_witnesses','hbe_guild_payment_guarantee')):
                line=re.sub(r'撤销前必须降低乡里压力，并终止尚未结算的(?:\[Concept\([^\]]+\)\|e\]|地方事业)','撤销时役负须低于40',line)
            lines.append(line)
        write_preserving_format(path,'\n'.join(lines)+'\n')
