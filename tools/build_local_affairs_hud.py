"""Three-state affairs entry, following the vanilla research-button circle stack."""
from pathlib import Path
from build_local_affairs_gui import shown, execute


ICONS = {
    state: f'gfx/interface/hbe/local_affairs/hud_{state}.dds'
    for state in ('idle', 'local', 'national')
}
COLORS = {'idle': (0.18, 0.22, 0.26), 'local': (0.17, 0.22, 0.18), 'national': (0.26, 0.17, 0.16)}


def export_icons(out):
    from PIL import Image
    from build_icon_assets import fit
    from build_flags import save_dds
    root = Path(__file__).resolve().parents[1]
    for state, texture in ICONS.items():
        with Image.open(root/f'assets/local_affairs_hud_v2/{state}.png') as source:
            assert source.mode == 'RGBA' and source.getchannel('A').getextrema() == (0, 255)
            sprite = fit(source, 128)
        save_dds(Path(out)/'main_menu'/texture, sprite)


def states(projects):
    result = [('hud_idle', 'NOT = { has_variable = hbe_af_active }')]
    for pool in ('local', 'national'):
        ids = ' '.join(f'var:hbe_af_active = {p["id"]}' for p in projects if p['pool'] == pool)
        result.append(('hud_'+pool, f'has_variable = hbe_af_active OR = {{ {ids} }}'))
    return result


def custom_text(projects):
    rows = ' '.join(f'text = {{ trigger = {{ {condition} }} localization_key = HBE_AF_HUD_{state.removeprefix("hud_").upper()} }}'
                    for state, condition in states(projects))
    return [
        'hbe_af_hud_state = { type = country '+rows+' text = { fallback = yes localization_key = HBE_AF_HUD_IDLE } }',
        '''hbe_af_hud_detail = { type = country
text = { trigger = { has_variable = hbe_af_active var:hbe_af_pause > 0 } localization_key = HBE_AF_HUD_PAUSED }
text = { trigger = { has_variable = hbe_af_active } localization_key = HBE_AF_HUD_ACTIVE }
text = { trigger = { has_variable = hbe_af_wait } localization_key = HBE_AF_HUD_WAIT }
text = { trigger = { hbe_af_available = yes } localization_key = HBE_AF_HUD_AVAILABLE }
text = { fallback = yes localization_key = HBE_AF_HUD_EMPTY }
}''',
    ]


def progress(var, visible):
    value = f"FixedPointToFloat(GetPlayer.MakeScope.GetVariable('{var}').GetValue)"
    # Vanilla agenda_view.gui: blue progress slice with a transparent remainder.
    return f'''piechart = {{ name = "hbe_af_hud_{var}_ring" parentanchor = center size = {{ 89% 89% }}
visible = "{visible}" using = piechart_angles alwaystransparent = yes
pieslice = {{ texture = "gfx/interface/pie_charts/pie_chart_blue_progress.dds" value = "[{value}]" color = {{ 1 1 1 1 }} }}
pieslice = {{ texture = "gfx/interface/pie_charts/pie_chart_blue_progress.dds" value = "[Subtract_float('(float)1.0',{value})]" color = {{ 1 1 1 0 }} }}
}}'''


def render(loc, out):
    export_icons(out)
    loc.update(
        HBE_AF_HUD_IDLE='闲置', HBE_AF_HUD_LOCAL='地方事业筹办中', HBE_AF_HUD_NATIONAL='中央事业筹办中',
        HBE_AF_HUD_TT="地方事业 · [Player.Custom('hbe_af_hud_state')]\\n[Player.Custom('hbe_af_hud_detail')]",
        HBE_AF_HUD_ACTIVE="[Player.Custom('hbe_af_active_name')]\\n$HBE_AF_ETA$",
        HBE_AF_HUD_PAUSED="[Player.Custom('hbe_af_active_name')] · 暂停\\n$HBE_AF_PAUSED$",
        HBE_AF_HUD_WAIT="整理中，约 [Player.MakeScope.GetVariable('hbe_af_wait_left').GetValue|0] 个月后可筹办。",
        HBE_AF_HUD_AVAILABLE='有可筹办项目。', HBE_AF_HUD_EMPTY='当前没有可筹办项目。',
    )
    icons = []
    for state, texture in ICONS.items():
        visible = shown('hbe_af_ui_hud_'+state)
        color = ' '.join(f'{n:g}' for n in COLORS[state])
        icons.append(f'''icon = {{ name = "hbe_af_hud_tint_{state}" parentanchor = center size = {{ 70% 70% }}
visible = "{visible}" texture = "gfx/interface/component_tiles/hud_corners/circle_background.dds"
modify_texture = {{ using = color_white_texture color = {{ {color} 1 }} }} alwaystransparent = yes }}
icon = {{ name = "hbe_af_hud_icon_{state}" parentanchor = center size = {{ 65% 65% }}
visible = "{visible}" texture = "{texture}" alwaystransparent = yes }}''')
    running = shown('hbe_af_ui_running')
    waiting = f"[And({shown('hbe_af_ui_waiting')[1:-1]},Not({running[1:-1]}))]"
    return f'''# Same circle background, 89% ring, 65% icon and cultural frame as vanilla research.
widget = {{ name = "hbe_af_hud_entry" parentanchor = bottom|right widgetanchor = bottom|right
position = {{ -24 -96 }} size = {{ 64 64 }}
alwaystransparent = yes filter_mouse = none
icon = {{ texture = "gfx/interface/component_tiles/hud_corners/circle_background.dds" size = {{ 100% 100% }} alwaystransparent = yes }}
icon = {{ texture = "gfx/interface/component_tiles/hud_corners/circle_progress_bg.dds" size = {{ 100% 100% }} alwaystransparent = yes }}
{progress('hbe_af_progress', running)}
{progress('hbe_af_wait_progress', waiting)}
{chr(10).join(icons)}
icon = {{ texture = "[GetGraphicalCultureTexture('circle_frame')]" texture_density = 2 size = {{ 100% 100% }} alwaystransparent = yes }}
# Last sibling owns the click; visual layers do not contain or overlap its children.
button_regular = {{ name = "hbe_af_hud_hitbox" size = {{ 100% 100% }} alpha = 0.001
using = snd_UI_forward tooltip = "HBE_AF_HUD_TT"
onclick = "{execute('hbe_af_ui_panel_open')}" }}
}}'''
