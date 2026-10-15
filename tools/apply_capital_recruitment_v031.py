"""Provide a capital muster point when an HBE member has no native recruitment site."""
from pathlib import Path
import hashlib
import json


EFFECT = '''hbe_ensure_capital_recruitment = {
    every_owned_location = {
        limit = { is_capital = no has_location_modifier = hbe_capital_muster }
        remove_location_modifier = hbe_capital_muster
    }
    if = {
        limit = { is_member_of_international_organization = international_organization:hbe_empire }
        if = {
            limit = { NOT = { any_owned_location = { modifier:can_recruit_regiment_in_this_location = yes } } }
            capital = { add_location_modifier = { modifier = hbe_capital_muster months = 2 mode = replace } }
        }
        else_if = {
            limit = { capital = { has_location_modifier = hbe_capital_muster } }
            capital = { add_location_modifier = { modifier = hbe_capital_muster months = 2 mode = replace } }
        }
    }
    else = {
        every_owned_location = {
            limit = { has_location_modifier = hbe_capital_muster }
            remove_location_modifier = hbe_capital_muster
        }
    }
}'''

ON_ACTION = '''on_game_start = { on_actions = { hbe_capital_recruitment_start } }
hbe_capital_recruitment_start = {
    effect = {
        every_country = {
            limit = { is_member_of_international_organization = international_organization:hbe_empire }
            hbe_ensure_capital_recruitment = yes
        }
    }
}
monthly_country_pulse = { on_actions = { hbe_capital_recruitment_monthly } }
hbe_capital_recruitment_monthly = {
    trigger = {
        OR = {
            is_member_of_international_organization = international_organization:hbe_empire
            any_owned_location = { has_location_modifier = hbe_capital_muster }
        }
    }
    effect = { hbe_ensure_capital_recruitment = yes }
}'''


def apply(out, root=None, game=None):
    out = Path(out)
    texts = {
        'in_game/common/scripted_effects/hbe_capital_recruitment.txt': EFFECT,
        'in_game/common/on_action/hbe_capital_recruitment.txt': ON_ACTION,
        'main_menu/common/static_modifiers/hbe_capital_recruitment.txt':
            'hbe_capital_muster = { can_recruit_regiment_in_this_location = yes }',
        'main_menu/localization/simp_chinese/hbe_capital_recruitment_l_simp_chinese.yml':
            'l_simp_chinese:\n hbe_capital_muster: "府都点兵处"\n STATIC_MODIFIER_NAME_hbe_capital_muster: "$hbe_capital_muster$"\n STATIC_MODIFIER_DESC_hbe_capital_muster: "$hbe_capital_muster_desc$"\n hbe_capital_muster_desc: "本府尚无常备军征募地点，暂以府都办理点兵。兵种科技、机构与兵额限制仍须满足。"',
        'main_menu/localization/english/hbe_capital_recruitment_l_english.yml':
            'l_english:\n hbe_capital_muster: "Capital Muster Point"\n STATIC_MODIFIER_NAME_hbe_capital_muster: "$hbe_capital_muster$"\n STATIC_MODIFIER_DESC_hbe_capital_muster: "$hbe_capital_muster_desc$"\n hbe_capital_muster_desc: "With no regular recruitment site elsewhere in the realm, the capital serves as a muster point. Unit technology, institution and regiment limits still apply."',
    }
    for relative, text in texts.items():
        path = out / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + '\n', encoding='utf-8-sig')
    report = {
        'version': '0.3.2',
        'scope': 'All current HBE members, including formed countries and later members.',
        'rule': 'If the country has no regular recruitment location, give its capital native recruitment permission.',
        'refresh': 'Game start and monthly country pulse; old saves receive it on their next pulse.',
        'expiration_months': 2,
        'extra_recruitment_queue': 0,
        'army_capacity_or_stat_bonus': 0,
        'files': list(texts),
    }
    path = out / 'build_manifest.json'
    manifest = json.loads(path.read_text(encoding='utf8'))
    manifest['capital_recruitment_v031'] = report
    manifest['files'] = {
        p.relative_to(out).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in out.rglob('*') if p.is_file() and p.name != 'build_manifest.json'
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    return report


if __name__ == '__main__':
    import sys
    print(json.dumps(apply(Path(sys.argv[1]) / 'mod/holy_bashu_empire'), ensure_ascii=False))
