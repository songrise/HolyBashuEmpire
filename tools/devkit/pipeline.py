"""Ordered final build passes. Order is a contract; partial execution is not inferred."""
from dataclasses import dataclass
import importlib


@dataclass(frozen=True)
class Stage:
    module: str
    function: str = "apply"
    game: bool = True


FINAL_STAGES = (
    Stage("apply_observer_hotfix", game=False),
    Stage("apply_name_hotfix", game=False),
    Stage("export_goods_modifier_icons", game=False),
    Stage("build_playable_stories", "build", False),
    Stage("export_story_art", "export", False),
    Stage("apply_industry_balance_patch", game=False),
    Stage("apply_advance_gate_patch", game=False),
    Stage("apply_event_balance_patch", game=False),
    Stage("apply_red_turban_caution", game=False),
    Stage("apply_unit_maintenance_patch", game=False),
    Stage("apply_local_ui_patch", game=False),
    Stage("apply_deep_balance_v031", game=False),
    Stage("apply_guest_production_patch", game=False),
    Stage("build_opening_population"),
    Stage("apply_opening_armistice_fix"),
    Stage("apply_formables_units_v031"),
    Stage("apply_annex_industry_v031"),
    Stage("apply_story_logic_v031"),
    Stage("apply_ending_art_v031"),
    Stage("apply_progress_art_v031"),
    Stage("apply_history_guides_v031"),
    Stage("apply_story_narratives_v031"),
    Stage("apply_loading_art_v031"),
    Stage("apply_unit_detail_art_v031"),
    Stage("apply_capital_recruitment_v031"),
    Stage("apply_red_turban_actions_v032"),
    Stage("apply_common_defense_v032"),
    Stage("apply_egret_art_v032"),
    Stage("apply_open_diplomacy_v032"),
    Stage("apply_western_tributes_v032"),
    Stage("apply_diplomacy_restraint_v032"),
    Stage("apply_industry_transmission"),
    Stage("apply_western_opening_v032"),
    Stage("apply_production_advance_semantics_v032"),
    Stage("apply_advance_display_v032"),
    Stage("apply_opening_identity_v032"),
    Stage("apply_population_identity_v032"),
    Stage("build_early_research"),
    Stage("finalize_release_v032"),
    Stage("build_age2_military"),
    # Population allocation precedes territory ownership changes.
    Stage("apply_opening_territory"),
    Stage("build_local_affairs"),
)


def run_final(out, root, game, *, loader=importlib.import_module):
    result = {}
    for stage in FINAL_STAGES:
        module = loader(stage.module)
        if stage.module == "export_story_art":
            previous = module.OUT
            try:
                module.OUT = out
                result[stage.module] = module.export()
            finally:
                module.OUT = previous
        else:
            args = (out, root, game) if stage.game else (out, root)
            result[stage.module] = getattr(module, stage.function)(*args)
    return result
