"""Monthly participation gate after the shared project affordability/scoring pass."""


def participation_effect(rules):
    personalities = rules['personalities']
    assert {p['id'] for p in personalities} == {1, 2}
    assert all(p['weight'] > 0 and 0 <= p['chance'] <= 100 for p in personalities)
    assignments = ' '.join(
        f"{p['weight']} = {{ set_variable = {{ name = hbe_af_ai_personality value = {p['id']} }} }}"
        for p in personalities
    )
    rolls = ' '.join(
        f"if = {{ limit = {{ var:hbe_af_ai_personality = {p['id']} }} "
        f"random = {{ chance = {p['chance']} hbe_af_auto_start = yes }} }}"
        for p in personalities
    )
    # Store the calendar month even on refusal. Repeated callers cannot reroll.
    # Nothing is assigned or rolled until scoring found an affordable candidate.
    return f'''hbe_af_ai_consider = {{
 if = {{ limit = {{ is_ai = yes hbe_af_idle = yes NOT = {{ at_war = yes }} var:hbe_af_choice > 0 var:hbe_af_best >= 7 }}
  set_variable = {{ name = hbe_af_ai_current_month value = {{ value = current_year multiply = 12 add = current_month }} }}
  if = {{ limit = {{ NOT = {{ has_variable = hbe_af_ai_last_month }} }} set_variable = {{ name = hbe_af_ai_last_month value = -1 }} }}
  if = {{ limit = {{ NOT = {{ var:hbe_af_ai_last_month = var:hbe_af_ai_current_month }} }}
   set_variable = {{ name = hbe_af_ai_last_month value = var:hbe_af_ai_current_month }}
   if = {{ limit = {{ NOT = {{ has_variable = hbe_af_ai_personality }} }} random_list = {{ {assignments} }} }}
   {rolls}
  }}
 }}
}}'''
