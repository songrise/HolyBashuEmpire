"""Finalize the 0.4 fresh-game state after shared content/art generation.

Earlier build stages still consume historical catalogue IDs. Remove their retired
decision shells and event/effect chains only after those stages have run. Current
funding, party actions, project receipts and native policy state remain authoritative.
"""
import re

from build_support import write_preserving_format
from pdxscript import blocks, apply_edits


COUNTERS = ('hbe_water', 'hbe_salt', 'hbe_river', 'hbe_roads', 'hbe_grain', 'hbe_tea', 'hbe_valleys')
VARIABLES = frozenset(COUNTERS + (
    'hbe_feast_helped', 'hbe_round_delivered', 'hbe_round_pledged', 'hbe_declined_project',
    'hbe_project_pending', 'hbe_project_timer', 'hbe_service_cooldown', 'hbe_fund_pledge',
    'hbe_work_burst_cooldown', 'hbe_labor_policy', 'hbe_project_kind', 'hbe_chapter',
    'hbe_contribution', 'hbe_dispute', 'hbe_role_1', 'hbe_role_2', 'hbe_role_3',
    'hbe_ballot_vote', 'hbe_ballot_seat_votes', 'hbe_ballot_circle_votes', 'hbe_ballot_active',
    'hbe_ballot_month', 'hbe_ballot_cooldown', 'hbe_proposal', 'hbe_subsidized_round',
    'hbe_audit_ready', 'hbe_audit_cooldown', 'hbe_civic_audit_cooldown', 'hbe_revision_cooldown',
    'hbe_af_legacy_retired_v1', 'hbe_af_cards_v2', 'hbe_af_expiry_v1', 'hbe_feast_v021',
))
DECISIONS = frozenset((
    'hbe_status', 'hbe_banquet_ledger', 'hbe_civic_ledger', 'hbe_civic_audit', 'hbe_civic_revision',
    'hbe_stance_change_1', 'hbe_stance_change_2', 'hbe_stance_change_3', 'hbe_project_fund',
    'hbe_project_pledge', 'hbe_project_reconsider', 'hbe_project_subsidize', 'hbe_audit_accounts',
))
DECISION_PREFIXES = ('hbe_service_', 'hbe_coordinate_', 'hbe_role_', 'hbe_project_select_',
                     'hbe_propose_charter_', 'hbe_ballot_vote_')
EVENTS = frozenset(('hbe.3', 'hbe.4', 'hbe_civic.2', 'hbe_civic.6', 'hbe_civic.7') +
                   tuple('hbe_banquet.'+str(n) for n in (3,6,7,12,13,14,15,20,21,22,23,30,31,32,33,34,35,36)))
EFFECTS = frozenset((
    'hbe_choose_stance_3', 'hbe_pledge_project', 'hbe_deliver_contract', 'hbe_advance_chapter',
    'hbe_tally_charter', 'hbe_feast_help', 'hbe_banquet_clamp', 'hbe_af_retire_legacy_country',
))


def retired_variable(name):
    return name in VARIABLES or name.startswith(('hbe_service_', 'hbe_recent_delivery_')) or bool(
        re.fullmatch(r'hbe_office_\w+_action_cooldown', name))


def retired_decision(name):
    return name in DECISIONS or name.startswith(DECISION_PREFIXES)


def clean_script(text):
    """Remove writes and deletion of retired state without changing active values."""
    migrations={'hbe_feast_v021','hbe_af_legacy_retired_v1','hbe_af_cards_v2','hbe_af_expiry_v1'}
    edits=[]
    for key,start,a,b,end in blocks(text):
        if key!='if':continue
        body=text[a:b]
        limit=next((body[x:y] for field,_,x,y,_ in blocks(body,0) if field=='limit'),'')
        if any(re.search(r'\bhas_variable\s*=\s*'+name+r'\b',limit) for name in migrations):
            edits.append((start,end,''))
        elif 'has_variable = hbe_stance var:hbe_stance > 2' in limit:
            edits.append((start,end,''))
    text=apply_edits(text,edits)
    edits=[]
    for key,start,a,b,end in blocks(text):
        if key not in ('set_variable','change_variable'):continue
        name=re.search(r'\bname\s*=\s*(hbe_\w+)',text[a:b])
        if name and retired_variable(name[1]):edits.append((start,end,''))
    text=apply_edits(text,edits)
    text=re.sub(r'\b(?:set_variable|remove_variable)\s*=\s*(hbe_\w+)\b',
                lambda m:'' if retired_variable(m[1]) else m[0],text)
    text=re.sub(r'\bNOT\s*=\s*\{\s*has_variable\s*=\s*hbe_work_burst_cooldown\s*\}', '',text)
    text=re.sub(r'\bhbe_banquet_clamp\s*=\s*yes\b','',text)
    # Removal can leave empty old country/organization scopes and if branches.
    while True:
        edits=[]
        for key,start,a,b,end in blocks(text):
            body=text[a:b]
            empty=not body.strip()
            if key=='if':
                children=blocks(body,0)
                only_limit=(len(children)==1 and children[0][0]=='limit' and
                            not apply_edits(body,[(children[0][1],children[0][4],'')]).strip())
                follows_else=re.match(r'\s*else(?:_if)?\s*=',text[end:])
                if only_limit and not follows_else:edits.append((start,end,''))
            elif empty and (key.startswith(('situation:','international_organization:')) or key=='else'):
                edits.append((start,end,''))
        if not edits:break
        # Keep the outermost range when an empty scope contains another removed range.
        outer=[e for e in edits if not any(a<=e[0] and e[1]<=b and (a,b)!=(e[0],e[1]) for a,b,_ in edits)]
        text=apply_edits(text,outer)
    return re.sub(r'\n(?:[ \t]*\n){2,}','\n\n',text)


def apply(out, manifest):
    removed_decisions=set();removed_events=set();removed_effects=set()
    for path in (out/'in_game').rglob('*.txt'):
        text=path.read_text(encoding='utf-8-sig');edits=[]
        for key,start,_,_,end in blocks(text,0):
            bucket=(removed_decisions if path.parent.name=='decisions' and retired_decision(key) else
                    removed_events if path.parent.name=='events' and key in EVENTS else
                    removed_effects if path.parent.name=='scripted_effects' and key in EFFECTS else None)
            if bucket is not None:edits.append((start,end,''));bucket.add(key)
        text=clean_script(apply_edits(text,edits))
        write_preserving_format(path,text)
    legacy=out/'in_game/common/scripted_effects/hbe_af_legacy_effects.txt'
    legacy.unlink(missing_ok=True)
    # Include prior removals when this finalization stage runs twice.
    prior=manifest.get('legacy_state_cleanup',{})
    removed_decisions.update(prior.get('decisions',[]));removed_events.update(prior.get('events',[]))
    removed_effects.update(prior.get('effects',[]))
    removed_effects.update(EFFECTS)
    for path in (out/'main_menu/localization').rglob('hbe*.yml'):
        lines=[]
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            match=re.match(r'\s*([^:\s]+):',line)
            if match:
                key=match[1]
                if (retired_variable(key) or retired_decision(key) or any(key.startswith(n+'.') for n in removed_decisions|EVENTS)
                        or re.search(r"GetVariable\(['\"]("+'|'.join(sorted(VARIABLES))+r")[\"']",line)):
                    continue
                if key in ('hbe_term_contribution','game_concept_hbe_term_contribution'):
                    line=' '+key+': "本届贡献"'
                elif key=='game_concept_hbe_term_contribution_desc':
                    line=' '+key+': "本届对会盟的贡献。出资记1分；地方事业完工按投入、工期和实际成果记入小数贡献，每届项目贡献至多2分。每两年结算后重新计分，明细可在大开席成员行悬浮查看。"'
            lines.append(line)
        write_preserving_format(path,'\n'.join(lines)+'\n')
    # Historical art/source catalogues retain their provenance; public counts refer
    # to registered runtime definitions, including local-affairs result events.
    count=lambda directory:sum(len(blocks(p.read_text(encoding='utf-8-sig'),0)) for p in directory.glob('hbe*.txt'))
    manifest['decisions']=count(out/'in_game/common/decisions')
    manifest['events']=count(out/'in_game/events')
    manifest['recurring_services']=0
    manifest['legacy_state_cleanup']={'baseline':'0.4.0 fresh campaigns','decisions':sorted(removed_decisions),
        'events':sorted(removed_events),'effects':sorted(removed_effects),'variables':sorted(VARIABLES)}


def validate(out, manifest, check):
    if 'legacy_state_cleanup' not in manifest:return
    scripts='\n'.join(p.read_text(encoding='utf-8-sig') for p in (out/'in_game').rglob('*.txt'))
    names=set(re.findall(r'\b(?:var:|name\s*=\s*|has_variable\s*=\s*|set_variable\s*=\s*|remove_variable\s*=\s*)(hbe_\w+)',scripts))
    check('0.4 runtime contains no retired variable operations',not any(retired_variable(n) for n in names))
    decisions={k for p in (out/'in_game/common/decisions').glob('hbe*.txt') for k,*_ in blocks(p.read_text(encoding='utf-8-sig'),0)}
    check('0.4 retired decision shells are absent',not any(retired_decision(k) for k in decisions))
    events={k for p in (out/'in_game/events').glob('hbe*.txt') for k,*_ in blocks(p.read_text(encoding='utf-8-sig'),0)}
    check('0.4 retired event chains are absent',not EVENTS&events)
    check('0.4 retired callbacks have neither definitions nor callers',not any(re.search(r'\b'+k+r'\s*=',scripts) for k in EFFECTS))
    effects=(out/'in_game/common/scripted_effects/hbe_af_effects.txt').read_text(encoding='utf-8-sig')
    check('0.4 current initialization owns the first draw exactly once','NOT = { has_variable = hbe_af_initialized }' in effects and 'hbe_af_idle = yes' in effects and 'hbe_af_migrate_' not in scripts)
    check('0.4 current party and funding effects remain registered',all(k+' = {' in scripts for k in ('hbe_choose_stance_1','hbe_choose_stance_2','hbe_fund_project','hbe_af_record_contribution')))
