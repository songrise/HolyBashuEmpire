"""Native EU5 widgets for affairs cards and its economy automation entry.

AutomationSystemItem's engine list has no script registration directory. Mount a
script-backed AutomationCard in the native filtered list without inventing an
engine item or changing existing automation entries.
"""
from pathlib import Path
import re
from pdxscript import blocks, apply_edits


SCOPE = 'GuiScope.SetRoot(GetPlayer.MakeScope).End'


def shown(key):
    return f"[GetScriptedGui('{key}').IsShown({SCOPE})]"


def execute(key):
    return f"[GetScriptedGui('{key}').Execute({SCOPE})]"


def button(key, label, x, y, width):
    return f'''button_regular = {{ position = {{ {x} {y} }} size = {{ {width} 36 }} text = "{label}"
using = Font_Type_Headers fontsize = 16
enabled = "[GetScriptedGui('{key}').IsValid({SCOPE})]"
onclick = "{execute(key)}" }}'''


def text(label, x, y, width, height=25, header=True, fontsize=None):
    return f'''text_multi = {{ position = {{ {x} {y} }} size = {{ {width} {height} }}
autoresize = no align = left|top text = "{label}" {'using = Font_Type_Headers' if header else ''} {'fontsize = '+str(fontsize) if fontsize else ''} color = {{ 0.94 0.90 0.80 1 }} }}'''


def divider(y):
    # Native texture, kept faint so the content has three distinct reading bands.
    return f'icon = {{ position = {{ 16 {y} }} size = {{ 344 1 }} alwaystransparent = yes using = color_new_gold_texture alpha = 0.35 }}'


def clock():
    return 'icon = { position = { 16 346 } size = { 32 32 } texture = "gfx/interface/icons/text_icons/time.dds" alwaystransparent = yes }'


def build_header_art(out):
    from PIL import Image, ImageOps
    root = Path(__file__).resolve().parents[1]
    dest = Path(out)/'main_menu/gfx/interface/hbe/local_affairs'
    dest.mkdir(parents=True, exist_ok=True)
    for pool in ('national', 'local'):
        with Image.open(root/'assets/local_affairs_headers_v1'/f'{pool}.png') as source:
            banner = ImageOps.fit(source.convert('RGBA'), (1488, 424), method=Image.Resampling.LANCZOS)
            banner.save(dest/f'{pool}_header.dds', pixel_format='DXT5')


def cog(master=False):
    # Same two-frame native cog and right-click action tooltip as automated_tab.
    left = f'''action_tooltip = {{ click_type = left title = "HBE_AF_AUTO_TOGGLE" on_action = "{execute('hbe_af_ui_auto')}" }}''' if master else ''
    return f'''AutomationCheckbox = {{
down = "{shown('hbe_af_ui_auto_state')}"
tooltip = "HBE_AF_COG_TT"
{left}
action_tooltip = {{ click_type = right title = "HBE_AF_AUTO_TOGGLE" on_action = "{execute('hbe_af_ui_auto')}" }}
tooltipwidget = {{ BasicFunctionalTooltip = {{}} }}
}}'''


def ring(var, x, y, size=66):
    progress=f"FixedPointToFloat(GetPlayer.MakeScope.GetVariable('{var}').GetValue)"
    return f'''piechart = {{ position = {{ {x} {y} }} size = {{ {size} {size} }} using = piechart_angles
pieslice = {{ texture = "gfx/interface/pie_charts/pie_chart_blue_progress.dds" value = "[{progress}]" color = {{ 1 1 1 1 }} }}
pieslice = {{ texture = "gfx/interface/pie_charts/pie_chart_blue_progress.dds" value = "[Subtract_float('(float)1.0',{progress})]" color = {{ 0.30 0.30 0.30 1 }} }} }}'''


def render(out, put, loc, projects, tiers, game):
    from build_local_affairs_rewards import preview
    build_header_art(out)
    loc.update(
        HBE_AF_AUTO_TOGGLE='切换自动筹办',
        HBE_AF_COG_TT="[Player.Custom('hbe_af_auto_text')]自动筹办。右键切换；详细设置位于自动操作的经济分类。",
        HBE_AF_AUTOMATION='地方事业', HBE_AF_DETAIL='展开／收起地方事业自动设置',
        HBE_AF_ALLOW_NATIONAL='允许全国筹办', HBE_AF_ALLOW_LOCAL='允许地方经营',
        HBE_AF_ALLOW_LARGE='允许大量投入',
        HBE_AF_LARGE_TT='大量投入须解锁「$hbe_af_allow_large_investment$」（$hbe_af_public_funding$）。',
        HBE_AF_RESERVE='保留国库', HBE_AF_BUDGET='年度支出上限', HBE_AF_LIMIT='役负上限',
        HBE_AF_AUTO_RULES='每月从当前双卡中择一；国库、年度预算及役负均须满足限制。战争期间不开新项目，条件不足则等待候选到期更新。',
        HBE_AF_PANEL_STATUS="国库 @gold! [Player.GetCurrencyValue('gold')|2]　　役负 @hbe_burden! [Player.MakeScope.GetVariable('hbe_burden').GetValue|1] / 100",
        HBE_AF_MINUS='−', HBE_AF_PLUS='+', HBE_AF_INVESTMENT='投入规模',
        HBE_AF_SMALL='#color_light_gray 少量投入#!', HBE_AF_LARGE='#color_yellow 大量投入#!',
        HBE_AF_ADOPT='筹办此项', HBE_AF_ACTIVE='#color_yellow 正在筹办#!',
        HBE_AF_WAIT_RING="下轮刷新\\n约 [Player.MakeScope.GetVariable('hbe_af_wait_left').GetValue|0] 个月",
        HBE_AF_ETA="预计于 [Player.MakeScope.GetVariable('hbe_af_eta_year').GetValue|0]年[Player.MakeScope.GetVariable('hbe_af_eta_month').GetValue|0]月 完成\\n（[GuiScope.SetRoot(Player.MakeScope).ScriptValue('hbe_af_remaining')|0]个月后）",
        HBE_AF_PAUSED="暂缓推进\\n尚需 [GuiScope.SetRoot(Player.MakeScope).ScriptValue('hbe_af_remaining')|0] 个月",
        HBE_AF_PAID="已投入 @gold! [Player.MakeScope.GetVariable('hbe_af_paid').GetValue|2]   @hbe_burden! +[Player.MakeScope.GetVariable('hbe_af_load').GetValue|1]",
        HBE_AF_NOTICE='有可筹办的地方事业', HBE_AF_NOTICE_HIDE='隐藏本轮提醒', HBE_AF_NOTICE_TT='本轮有可支付的地方事业。左键查看；右键隐藏本轮提醒。',
    )
    running=shown('hbe_af_ui_running')[1:-1]
    waiting=shown('hbe_af_ui_waiting')[1:-1]
    ready=shown('hbe_af_ui_ready')[1:-1]
    large="GetVariableSystem.Exists('hbe_af_preview_large')"
    cards=[]
    expiry_labels=[]
    for pool,x in [('national',32),('local',432)]:
        contents=[]
        for p in projects:
            if p['pool']!=pool: continue
            pid=p['id']
            selected=f"EqualTo_CFixedPoint(GetPlayer.MakeScope.GetVariable('hbe_af_active').GetValue, '(CFixedPoint){pid}')"
            offer=f"EqualTo_CFixedPoint(GetPlayer.MakeScope.GetVariable('hbe_af_{pool}').GetValue, '(CFixedPoint){pid}')"
            body=text('hbe_af_project_'+str(pid),16,57,292,42,True,22)
            if pool=='local': body+=text('HBE_AF_TARGET',16,153,200,25,fontsize=16)
            body+=divider(181)+divider(336)
            for i,t in enumerate(tiers):
                key=f'{pid}_{t["key"]}'
                tier=f"EqualTo_CFixedPoint(GetPlayer.MakeScope.GetVariable('hbe_af_tier').GetValue, '(CFixedPoint){i+1}')"
                preview_tier=large if i else f'Not({large})'
                # One global preview; once started both cards freeze to the paid tier.
                view=f'Or(And(Not({running}),{preview_tier}),And({running},{tier}))'
                loc['hbe_af_costline_'+key]=f"投入   @gold! [GuiScope.SetRoot(Player.MakeScope).ScriptValue('hbe_af_cost_{key}')|2]    @hbe_burden! +[GuiScope.SetRoot(Player.MakeScope).ScriptValue('hbe_af_load_{key}')|1]"
                colors={'少量':'color_light_gray','中量':'color_green','大量':'color_yellow'}
                benefits=sorted(p['benefits'],key=lambda b:b['priority'],reverse=True)
                loc['hbe_af_bullets_'+key]='\\n'.join('• #'+colors[b['grades'][i]]+' '+b['grades'][i]+'#!'+b['label'] for b in benefits)
                loc['hbe_af_exact_'+key]=preview(p,i)+'\\n\\n'+p['description']
                loc['hbe_af_time_'+key]=f'约 {p["months"][i]} 个月'
                detail=f'widget = {{ size = {{ 376 420 }} visible = "[Not({selected})]" '+text('hbe_af_costline_'+key,16,121,344,30,fontsize=16)+' }'
                detail+=f'''text_multi = {{ position = {{ 16 195 }} size = {{ 344 138 }} autoresize = no align = left|top using = Font_Type_Headers fontsize = 16 color = {{ 0.94 0.90 0.80 1 }}
text = "hbe_af_bullets_{key}" tooltip = "hbe_af_exact_{key}" }}'''
                detail+=f'widget = {{ size = {{ 376 420 }} visible = "[Not({selected})]" '+clock()+text('hbe_af_time_'+key,58,349,302,28,fontsize=16)+button('hbe_af_choose_'+key,'HBE_AF_ADOPT',16,380,344)+' }'
                body+=f'widget = {{ size = {{ 376 420 }} visible = "[{view}]" {detail} }}'
            paused="GreaterThan_CFixedPoint(GetPlayer.MakeScope.GetVariable('hbe_af_pause').GetValue, '(CFixedPoint)0')"
            body+=f'widget = {{ size = {{ 376 420 }} visible = "[{selected}]" '+text('HBE_AF_ACTIVE',224,153,136,25,fontsize=16)+text('HBE_AF_PAID',16,121,344,30,fontsize=16)
            body+=f'widget = {{ size = {{ 376 420 }} visible = "[Not({paused})]" '+clock()+text('HBE_AF_ETA',58,349,302,60,fontsize=16)+' }'
            body+=f'widget = {{ size = {{ 376 420 }} visible = "[{paused}]" '+clock()+text('HBE_AF_PAUSED',58,349,302,60,fontsize=16)+' } }'
            body+=f'''icon = {{ size = {{ 376 420 }} alwaystransparent = yes using = bg_selected_law_frame
blockoverride "bg_selected_law_visible" {{ visible = "[{selected}]" }} }}

icon = {{ size = {{ 376 420 }} alwaystransparent = yes using = color_black_texture alpha = 0.45 visible = "[Or({waiting},And({running},Not({selected})))]" }}'''
            # A foreground translucent veil dims unavailable cards without changing text layout.
            contents.append(f'widget = {{ size = {{ 376 420 }} visible = "[{offer}]" {body} }}')
        empty=f"EqualTo_CFixedPoint(GetPlayer.MakeScope.GetVariable('hbe_af_{pool}').GetValue, '(CFixedPoint)0')"
        contents.append(f'widget = {{ size = {{ 376 420 }} visible = "[{empty}]" '+text('HBE_AF_EMPTY',16,195,344,138,fontsize=20)+' }')
        # Shared art by project pool; native masks stay independent of image pixels.
        header = f'''widget = {{ name = "hbe_af_illustrated_header" position = {{ 2 2 }} size = {{ 372 106 }} alwaystransparent = yes
background = {{ texture = "gfx/interface/hbe/local_affairs/{pool}_header.dds"
modify_texture = {{ texture = "gfx/interface/component_masks/mask_fade_vertical.dds" blend_mode = alphamultiply }} }}
background = {{ using = color_black_texture alpha = 0.66
modify_texture = {{ texture = "gfx/interface/component_masks/mask_fade_horizontal_right.dds" blend_mode = alphamultiply }} }}
}}
'''
        refresh = 'widget = { name = "hbe_af_refresh_reserved" position = { 326 12 } size = { 36 36 } alwaystransparent = yes }'
        if pool == 'local':
            refresh = f'''button_round_shortcut = {{ name = "hbe_af_refresh_local" position = {{ 326 12 }} size = {{ 36 36 }}
visible = "{shown('hbe_af_ui_refresh_local')}"
enabled = "[GetScriptedGui('hbe_af_ui_refresh_local').IsValid({SCOPE})]"
blockoverride "button_texture" {{ texture = "gfx/interface/icons/international_organizations/change.dds" texture_density = 4 }}
tooltip = "HBE_AF_REFRESH_LOCAL_TT"
onclick = "{execute('hbe_af_ui_refresh_local')}"
}}'''
        cards.append(f'widget = {{ position = {{ {x} 124 }} size = {{ 376 420 }} using = hbe_af_card_surface '+header+text('HBE_AF_'+pool.upper(),16,30,292,28,fontsize=14)+' '.join(contents)+refresh+' }')
        loc['HBE_AF_EXPIRY_'+pool.upper()]=f"[Player.MakeScope.GetVariable('hbe_af_{pool}_expires').GetValue|0]个月后过期"
        nonempty=f"GreaterThan_CFixedPoint(GetPlayer.MakeScope.GetVariable('hbe_af_{pool}').GetValue, '(CFixedPoint)0')"
        expiry_labels.append(f'widget = {{ visible = "[And({ready},{nonempty})]" '+text('HBE_AF_EXPIRY_'+pool.upper(),x,550,376,24,fontsize=14).replace('align = left|top','align = center').replace('0.94 0.90 0.80','0.68 0.66 0.60')+' }')
    toggle=[]
    for i in range(2):
        paid_large="EqualTo_CFixedPoint(GetPlayer.MakeScope.GetVariable('hbe_af_tier').GetValue, '(CFixedPoint)2')"
        displayed=f'Or(And(Not({running}),{large}),And({running},{paid_large}))'
        sel=displayed if i else f'Not({displayed})'
        toggle.append(f'''widget = {{ position = {{ {235+i*190} 87 }} size = {{ 180 30 }}
checkbox_round_alt = {{ down = "[{sel}]" enabled = "[And({ready},Not({sel}))]" onclick = "[GetVariableSystem.Toggle('hbe_af_preview_large')]" }}
text_single = {{ position = {{ 38 0 }} size = {{ 140 30 }} autoresize = no using = Font_Type_Headers fontsize = 16 align = left|nobaseline text = "HBE_AF_{'LARGE' if i else 'SMALL'}" {'tooltip = "HBE_AF_LARGE_TT"' if i else ''} }} }}''')
    from build_local_affairs_hud import render as hud_entry
    open_button = hud_entry(loc, out)
    cooldown=f'widget = {{ size = {{ 840 628 }} visible = "[{waiting}]" '+ring('hbe_af_wait_progress',306,564,48)+text('HBE_AF_WAIT_RING',368,564,300,48,fontsize=18)+' }'
    footer=f'widget = {{ size = {{ 840 628 }} visible = "[{running}]" '+button('hbe_af_ui_cancel','HBE_AF_CANCEL',32,571,776)+' }'
    gui=f'''# Native dual cards persist during construction and refresh cooldown.
template hbe_af_panel_surface {{
background = {{ using = color_white_texture color = {{ 0.075 0.085 0.083 1 }} }}
background = {{ using = overlay_paper_03 alpha = 0.10 }}
background = {{ using = tile_frame_squared_texture modify_texture = {{ using = color_new_gold_texture }} }}
}}
template hbe_af_card_surface {{
background = {{ using = color_white_texture color = {{ 0.095 0.090 0.075 1 }} }}
background = {{ using = overlay_paper_03 alpha = 0.10 }}
background = {{ using = tile_frame_squared_texture modify_texture = {{ using = color_new_gold_texture }} alpha = 0.72 }}
}}
types HbeLocalAffairs {{
type hbe_af_overlay = widget {{ name = "hbe_local_affairs" size = {{ 100% 100% }} alwaystransparent = yes
visible = "[And(Not(IsPauseMenuShown),{shown('hbe_af_ui_access')[1:-1]})]"
{open_button}
window = {{ name = "hbe_af_window" size = {{ 840 628 }} position = {{ 0 0 }} parentanchor = center widgetanchor = center movable = yes using = hbe_af_panel_surface
visible = "{shown('hbe_af_ui_panel_visible')}"
window_header_alt = {{ size = {{ 840 42 }} blockoverride "header_text_object" {{ widget = {{ size = {{ 0 0 }} }} }} }}
text_single = {{ position = {{ 0 5 }} size = {{ 840 32 }} autoresize = no align = center using = Font_Type_Headers fontsize = 24 text = "HBE_AF_TITLE" color = {{ 0.94 0.90 0.80 1 }} }}
widget = {{ position = {{ -78 8 }} parentanchor = top|right widgetanchor = top|right size = {{ 30 30 }} {cog()} }}
button_close = {{ position = {{ -10 8 }} parentanchor = top|right widgetanchor = top|right onclick = "{execute('hbe_af_ui_panel_close')}" }}
{text('HBE_AF_PANEL_STATUS',32,53,776,30,fontsize=16).replace('align = left|top', 'align = center')}
{''.join(toggle)}
{''.join(cards)} {''.join(expiry_labels)} {cooldown} {footer}
}} }}
type hbe_af_alert = button {{
visible = "{shown('hbe_af_ui_available')}"
using = alert_banner_setup using = green_alert
blockoverride "icon_texture" {{ texture = "gfx/interface/icons/alerts_icons/decisions.dds" }}
blockoverride "alert_is_new_padding_visible" {{ visible = no }}
tooltip = "HBE_AF_NOTICE_TT"
action_tooltip = {{ title = "HBE_AF_NOTICE" on_action = "{execute('hbe_af_ui_panel_open')}" }}
action_tooltip = {{ click_type = right title = "HBE_AF_NOTICE_HIDE" on_action = "{execute('hbe_af_ui_dismiss_notice')}" }}
tooltipwidget = {{ BasicFunctionalTooltip = {{}} }}
}}
}}'''
    put('in_game/gui/hbe_local_affairs.gui',gui)
    host=(Path(game)/'in_game/gui/ingame_topbar.gui').read_text(encoding='utf-8-sig')
    main=next(b for b in blocks(host,0) if b[0]=='widget' and re.search(r'\bname\s*=\s*"ingame_topbar"',host[b[2]:b[3]]))
    mount='\n\t# HBE: mount the independent affairs panel, not the situation panel.\n\thbe_af_overlay = {}\n'
    host=apply_edits(host,[(main[3],main[3],mount)])
    alert=next(b for b in blocks(host) if b[0]=='alert_manager')
    prefix='hbox = { # HBE affairs alert row\n using = layoutpolicy_expanding ignoreinvisible = yes hbe_af_alert = {}\n'
    suffix='\n} # HBE affairs alert row end'
    host=apply_edits(host,[(alert[1],alert[1],prefix),(alert[4],alert[4],suffix)])
    put('in_game/gui/ingame_topbar.gui',host)
    automation(put,loc,game)


def automation(put,loc,game):
    settings = []
    for var, label in [('reserve','RESERVE'),('budget','BUDGET'),('limit','LIMIT')]:
        value_key='HBE_AF_SETTING_'+var
        loc[value_key] = f"[Player.MakeScope.GetVariable('hbe_af_{var}').GetValue|0]"
        settings.append(f'''hbox = {{ layoutpolicy_horizontal = expanding spacing = 8 margin = {{ 8 6 }}
text_single = {{ size = {{ -1 26 }} layoutpolicy_horizontal = expanding autoresize = no text = "HBE_AF_{label}" align = left|nobaseline }}
button_regular = {{ size = {{ 28 26 }} text = "HBE_AF_MINUS" onclick = "{execute('hbe_af_'+var+'_minus')}" }}
text_single = {{ size = {{ 54 26 }} autoresize = no text = "{value_key}" }}
button_regular = {{ size = {{ 28 26 }} text = "HBE_AF_PLUS" onclick = "{execute('hbe_af_'+var+'_plus')}" }} }}''')
    flags=[]
    for option in ('national','local','large'):
        flags.append(f'''hbox = {{ layoutpolicy_horizontal = expanding spacing = 8 margin = {{ 8 4 }}
checkbox_square_alt = {{ down = "{shown('hbe_af_allow_'+option)}" onclick = "{execute('hbe_af_allow_'+option)}" }}
text_single = {{ size = {{ -1 28 }} layoutpolicy_horizontal = expanding autoresize = no align = left|nobaseline text = "HBE_AF_ALLOW_{option.upper()}" }} }}''')
    gui = f'''# Native AutomationCard/AutomationCheckbox, scoped to the economy filter.
types HbeAffairsAutomation {{
type hbe_af_automation_card = AutomationCard {{
datacontext = "[FilteredSortedList.GetSearchBar]"
visible = "[And({shown('hbe_af_ui_access')[1:-1]}, Or(Not(AutomationLateralView.IsSearchActive), SearchBar.IsFilterEnabledByKey('automation_filter_economy')))]"
blockoverride "header_button" {{
action_tooltip = {{ click_type = left title = "HBE_AF_DETAIL"
on_action = "{execute('hbe_af_ui_prepare')}"
on_action = "[GetVariableSystem.Toggle('hbe_af_auto_details')]" }} }}
blockoverride "bg_card_header_01_bg" {{ background = {{ using = bg_card_header_01_default blockoverride "header_color" {{ using = color_economy_texture }} }} }}
blockoverride "header_content" {{ hbox = {{ layoutpolicy_horizontal = expanding margin = {{ 10 5 }} spacing = 10
{cog(True)}
text_single = {{ layoutpolicy_horizontal = expanding align = left|nobaseline using = Font_Type_Headers text = "HBE_AF_AUTOMATION" }}
button_minimize = {{ size = {{ 25 25 }} blockoverride "button_texture" {{ texture = "gfx/interface/buttons/flats/goto.dds" texture_density = 2 }}
action_tooltip = {{ title = "HBE_AF_DETAIL" on_action = "{execute('hbe_af_ui_prepare')}" on_action = "[GetVariableSystem.Toggle('hbe_af_auto_details')]" }} }} }} }}
blockoverride "footer_content" {{ vbox = {{ layoutpolicy_horizontal = expanding spacing = 5 margin = {{ 8 10 }}
visible = "[GetVariableSystem.Exists('hbe_af_auto_details')]"
vbox = {{ layoutpolicy_horizontal = expanding using = bg_dynasty_header {' '.join(settings)} }}
vbox = {{ layoutpolicy_horizontal = expanding using = bg_dynasty_header {' '.join(flags)} }}
text_multi = {{ layoutpolicy_horizontal = expanding size = {{ -1 42 }} autoresize = no text = "HBE_AF_AUTO_STATUS" tooltip = "HBE_AF_AUTO_RULES" }}
}} }}
}}
}}'''
    put('in_game/gui/hbe_local_affairs_automation.gui',gui)
    host=(Path(game)/'in_game/gui/automation_lateralview.gui').read_text(encoding='utf-8-sig')
    match=re.search(r'blockoverride "scroll_list_layout"\s*\{\s*vbox\s*=\s*\{\s*using = layoutpolicy_expanding\s*spacing = 10',host)
    if not match:
        raise ValueError('Native automation list structure changed; refusing to replace unrelated GUI')
    mount='\n\t\t\t\t\t\t\t# HBE: script-backed economy automation entry.\n\t\t\t\t\t\t\thbe_af_automation_card = {}\n'
    put('in_game/gui/automation_lateralview.gui',host[:match.end()]+mount+host[match.end():])
