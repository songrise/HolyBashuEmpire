"""Completion-only native context menu; other events retain vanilla GUI bytes."""
from pdxscript import blocks


def build(out, put, loc, game):
    scope='GuiScope.SetRoot(GetPlayer.MakeScope).End'
    labels=('显示全部完工弹窗','仅显示大成功弹窗','不显示完工弹窗')
    entries=[];sguis=[]
    for i,label in enumerate(labels):
        key='hbe_af_notice_mode_'+str(i);loc[key]=label
        sguis.append(f'{key} = {{ scope = country is_shown = {{ hbe_af_access = yes }} is_valid = {{ hbe_af_access = yes }} effect = {{ set_variable = {{ name = hbe_af_notice_mode value = {i} }} }} }}')
        entries.append(f'''button_regular = {{ layoutpolicy_horizontal = expanding size = {{ 300 35 }}
onclick = "[GetScriptedGui('{key}').Execute({scope})]"
hbox = {{ margin = {{ 10 0 }} spacing = 10
icon = {{ size = {{ 22 22 }} using = button_checkbox_template frame = "[Select_int32(EqualTo_CFixedPoint(GetPlayer.MakeScope.GetVariable('hbe_af_notice_mode').GetValue, '(CFixedPoint){i}'), '(int32)2', '(int32)1')]" }}
text_single = {{ layoutpolicy_horizontal = expanding text = "{key}" }} }} }}''')
    loc['HBE_AF_NOTICE_SETTINGS']='地方事业完工通知'
    put('in_game/common/scripted_guis/hbe_af_notice_settings.txt','\n'.join(sguis))
    put('in_game/gui/hbe_af_notice_settings.gui','''types HbeAffairsNoticeSettings {
type HbeAffairsNoticeSettingsMenu = ContextMenuBase {
blockoverride "contextmenu_content" {
ContextMenuSection = {
blockoverride "title_icon" {}
blockoverride "title_text" { text = "HBE_AF_NOTICE_SETTINGS" }
blockoverride "contextmenu_entries" { vbox = { spacing = 3 '''+' '.join(entries)+''' } }
} } }
}''')
    events=(out/'in_game/events/hbe_af_results.txt').read_text(encoding='utf-8-sig')
    keys=[key for key,*_ in blocks(events,0)]
    def any_of(parts):
        if len(parts)==1:return parts[0]
        n=len(parts)//2
        return 'Or('+any_of(parts[:n])+','+any_of(parts[n:])+')'
    visible=any_of([f"EqualTo_string(EventWindow.GetEventKey, '{key}')" for key in keys])
    mount=f'''
 # HBE: completion-only notice preferences, using the native message button and context controls.
 button_list = {{ name = "hbe_af_result_message_settings"
 parentanchor = top|right position = {{ -32 18 }} size = {{ 22 22 }} using = bg_circle_piechart
 visible = "[{visible}]"
 action_tooltip = {{ title = "MESSAGE_SETTINGS_POPUP" on_action = "[PdxGuiWidget.ToggleContextMenu]" }}
 tooltipwidget = {{ BasicFunctionalTooltip = {{}} }}
 contextmenu_widget = {{ HbeAffairsNoticeSettingsMenu = {{}} }}
 }}
'''
    native=(game/'in_game/gui/eventwindow.gui').read_text(encoding='utf-8-sig')
    window=next(b for b in blocks(native,0) if b[0]=='window' and 'name = "event_window"' in native[b[2]:b[3]])
    put('in_game/gui/eventwindow.gui',native[:window[3]]+mount+native[window[3]:])
    # A silent preference still needs a visible way to re-enable notifications.
    path=out/'in_game/gui/hbe_local_affairs_automation.gui'
    text=path.read_text(encoding='utf-8-sig')
    extra='vbox = { layoutpolicy_horizontal = expanding spacing = 2 '+ ' '.join(entries)+' }\n'
    marker='text_multi = { layoutpolicy_horizontal = expanding size = { -1 42 }'
    assert marker in text
    put(path.relative_to(out).as_posix(),text.replace(marker,extra+marker,1))


def validate(out, game, check):
    text=(out/'in_game/gui/eventwindow.gui').read_text(encoding='utf-8-sig')
    native=(game/'in_game/gui/eventwindow.gui').read_text(encoding='utf-8-sig')
    root=next(b for b in blocks(text,0) if b[0]=='window' and 'name = "event_window"' in text[b[2]:b[3]])
    children=blocks(text[root[2]:root[3]],0)
    mount=next(b for b in children if b[0]=='button_list' and 'hbe_af_result_message_settings' in text[root[2]+b[2]:root[2]+b[3]])
    # Compare meaningful vanilla tokens: only a single button was added.
    from pdxscript import tokens
    without=text[:root[2]+mount[1]]+text[root[2]+mount[4]:]
    check('completion settings keeps all unrelated vanilla event controls intact',[t.value for t in tokens(without)]==[t.value for t in tokens(native)])
    check('completion settings uses the native menu button and actual context menu','PdxGuiWidget.ToggleContextMenu' in text and 'contextmenu_widget = { HbeAffairsNoticeSettingsMenu = {} }' in text and 'MessagePopup.GetSettingsItems' not in text)
    effects=(out/'in_game/common/scripted_effects/hbe_af_effects.txt').read_text(encoding='utf-8-sig')
    receipts=[effects[a:b] for k,_,a,b,_ in blocks(effects,0) if k.startswith('hbe_af_receipt_')]
    check('every result receipt respects all great-only and silent modes',all('NOT = { var:hbe_af_notice_mode = 2 }' in b and 'var:hbe_af_outcome = 4' in b for b in receipts))
    check('completion preferences can be re-enabled from economy automation','hbe_af_notice_mode_0' in (out/'in_game/gui/hbe_local_affairs_automation.gui').read_text(encoding='utf-8-sig'))
