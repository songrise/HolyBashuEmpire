"""Enforce the requested opening-only expiry despite native default truce duration."""
from pathlib import Path
from itertools import combinations
import json,re

def apply(out,root,game):
    out,root,game=map(Path,(out,root,game))
    manifest=json.loads((out/'build_manifest.json').read_text(encoding='utf-8-sig'))
    tags=[c['tag'] for c in manifest['countries']]
    p=out/'in_game/common/scripted_effects/hbe_opening_pacts_effects.txt';text=p.read_text(encoding='utf-8-sig')
    if 'hbe_schedule_opening_expiry' not in text:
        pattern=r'^c:(\w+) \?= \{ add_truce_with = \{ target = c:(\w+) mutual = yes years = 1 \} \}$'
        def tag_pair(m):
            a,b=m.groups()
            return f'c:{a} ?= {{ add_truce_with = {{ target = c:{b} mutual = yes years = 1 }} set_variable = hbe_opening_truce_{b} c:{b} ?= {{ set_variable = hbe_opening_truce_{a} }} }}'
        text,count=re.subn(pattern,tag_pair,text,flags=re.M);assert count==630
        anchor='   every_country = { limit = { hbe_is_prince = yes } set_variable = hbe_opening_truce_done }'
        assert anchor in text
        text=text.replace(anchor,anchor+'\n   every_country = { limit = { hbe_is_prince = yes } hbe_schedule_opening_expiry = yes }')
        p.write_text(text,encoding='utf-8-sig')
    helper='''hbe_schedule_opening_expiry = {
 if = { limit = { NOT = { has_variable = hbe_opening_expiry_scheduled } }
  set_variable = hbe_opening_expiry_scheduled
  trigger_event_silently = { id = hbe_opening_family.2 days = 365 }
 }
}
hbe_expire_opening_pair_flags = {
'''
    for target in tags:
        helper+=f''' if = {{ limit = {{ has_variable = hbe_opening_truce_{target} c:{target} ?= {{ has_variable = hbe_opening_truce_$self$ }} }}
  remove_truce_with = c:{target}
  remove_variable = hbe_opening_truce_{target}
  c:{target} ?= {{ remove_truce_with = root remove_variable = hbe_opening_truce_$self$ }}
 }}
'''
    helper+='}\nhbe_expire_opening_truces = {\n'
    for i,tag in enumerate(tags):helper+=f' {"if" if i==0 else "else_if"} = {{ limit = {{ has_or_had_tag = {tag} }} hbe_expire_opening_pair_flags = {{ self = {tag} }} }}\n'
    helper+=' set_variable = hbe_opening_expiry_completed\n}\nhbe_clear_broken_opening_pair = {\n'
    for tag in tags:
        helper+=f' if = {{ limit = {{ scope:recipient = {{ has_or_had_tag = {tag} }} }} remove_variable = hbe_opening_truce_{tag} }}\n'
        helper+=f' if = {{ limit = {{ root = {{ has_or_had_tag = {tag} }} }} scope:recipient = {{ remove_variable = hbe_opening_truce_{tag} }} }}\n'
    helper+='}\n'
    (out/'in_game/common/scripted_effects/hbe_opening_armistice_effects.txt').write_text(helper,encoding='utf-8-sig')
    p=out/'in_game/events/hbe_opening_family_events.txt';text=p.read_text(encoding='utf-8-sig')
    if 'hbe_opening_family.2' not in text:
        text+='''
hbe_opening_family.2 = {
 type = country_event hidden = yes outcome = neutral title = hbe_opening_family.2.title
 immediate = { hbe_expire_opening_truces = yes }
}
''';p.write_text(text,encoding='utf-8-sig')
    p=out/'in_game/common/on_action/hbe_opening_pacts_on_actions.txt';text=p.read_text(encoding='utf-8-sig')
    # Run initialization before the first daily tick; retain the family repair event.
    anchor='c:BAB ?= { trigger_event_silently = { id = hbe_opening_family.1 days = 1 } }'
    if 'hbe_apply_opening_pacts = yes' not in text:
        assert anchor in text;text=text.replace(anchor,'c:BAB ?= { hbe_apply_opening_pacts = yes trigger_event_silently = { id = hbe_opening_family.1 days = 1 } }')
    p.write_text(text,encoding='utf-8-sig')
    (out/'in_game/common/on_action/hbe_opening_armistice_on_actions.txt').write_text('''on_truce_broken = { on_actions = { hbe_opening_truce_broken } }
hbe_opening_truce_broken = {
 trigger = { hbe_is_prince = yes scope:recipient = { hbe_is_prince = yes } }
 effect = { hbe_clear_broken_opening_pair = yes }
}
''',encoding='utf-8-sig')
    # Match the actual special expiry in existing native tooltip contexts, preserving
    # the native text for outside countries and subsequently broken/replaced truces.
    def pair_guard(first,second):
        return f"And({first}.MakeScope.GetVariable(Concatenate('hbe_opening_truce_', {second}.GetTag)).IsSet, {second}.MakeScope.GetVariable(Concatenate('hbe_opening_truce_', {first}.GetTag)).IsSet)"
    gui=(game/'in_game/gui/cooltip.gui').read_text(encoding='utf-8-sig')
    expr='[GetSelectedCountryOrByLocation.GetTruceToolTip(Country.Self)]'
    assert gui.count('text = "'+expr+'"')==1
    replacement="[Select_CString("+pair_guard('GetSelectedCountryOrByLocation','Country')+", Localize('hbe_opening_truce_map_tt'), GetSelectedCountryOrByLocation.GetTruceToolTip(Country.Self))]"
    gui=gui.replace('text = "'+expr+'"','text = "'+replacement+'"')
    p=out/'in_game/gui/cooltip.gui';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(gui,encoding='utf-8-sig')
    for lang in ('simp_chinese','english'):
        original=(game/f'main_menu/localization/{lang}/diplomacy_l_{lang}.yml').read_text(encoding='utf-8-sig')
        native=re.search(r'^ TRUCE_WITH_COUNTRY_UNTIL:\s*"(.*)"$',original,re.M)[1]
        key='hbe_opening_truce_until'
        conditional="[Select_CString("+pair_guard('GetPlayer','Country')+", Localize('"+key+"'), Localize('hbe_native_truce_until'))]"
        zh=lang=='simp_chinese'
        truce='[Country.GetName]与[GetPlayer.GetName]的开局停战于#V 1338年4月1日#!到期（一年）。' if zh else '[Country.GetName] and [GetPlayer.GetName] have an opening armistice until #V 1 April 1338#! (one year).'
        maptext='[Country.GetName]与[GetSelectedCountryOrByLocation.GetName]的开局停战于#V 1338年4月1日#!到期（一年）。' if zh else '[Country.GetName] and [GetSelectedCountryOrByLocation.GetName] have an opening armistice until #V 1 April 1338#! (one year).'
        strings={'hbe_opening_family.2.title':'开局停战期满' if zh else 'Opening Armistice Expires','hbe_opening_truce_until':truce,'hbe_opening_truce_map_tt':maptext,'hbe_native_truce_until':native}
        text='l_'+lang+':\n'+ '\n'.join(' '+k+': "'+v.replace('"','\\"')+'"' for k,v in strings.items())+'\n'
        (out/f'main_menu/localization/{lang}/hbe_opening_armistice_l_{lang}.yml').write_text(text,encoding='utf-8-sig')
        d=out/f'main_menu/localization/{lang}/replace';d.mkdir(parents=True,exist_ok=True)
        (d/f'hbe_opening_truce_ui_l_{lang}.yml').write_text('l_'+lang+':\n TRUCE_WITH_COUNTRY_UNTIL: "'+conditional+'"\n',encoding='utf-8-sig')
    return dict(years=1,expires='1338.4.1',pairs=630,mechanism='Opening-only scheduled expiry; native default truce years remain unchanged',broken_pairs_exempt=True,initialization_before_first_tick=True,ui_pair_flags=True)
