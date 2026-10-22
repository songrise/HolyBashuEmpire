"""Chance-based court and cultural rewards using vanilla character/art effects."""


def roll(row, index):
    # Lock both tier dice at start. Switching the preview cannot reroll rewards.
    return ' '.join(
        f'set_variable = {{ name = hbe_af_people_{index}_{tier} value = 0 }} '
        f'random = {{ chance = {chance} set_variable = {{ name = hbe_af_people_{index}_{tier} value = 1 }} }}'
        for tier, chance in enumerate(row['chance']))


def effect(row, index, tier):
    actual = f'hbe_af_actual_{index}'
    if row['type'] == 'courtier':
        reward = ('create_character = { age = { 25 50 } culture = root.culture religion = root.religion '
                  'save_scope_as = hbe_af_new_courtier } '
                  'scope:hbe_af_new_courtier = { move_country = root } '
                  f'set_variable = {{ name = {actual} value = 1 }}')
        reset = ''
    else:
        artists = ' '.join(
            '100 = { create_character = { age = { 25 50 } culture = root.culture religion = root.religion '
            f'trait_category = artist artist = {kind} save_scope_as = hbe_af_new_artist }} '
            'scope:hbe_af_new_artist = { move_country = root } '
            'set_variable = { name = hbe_af_artist_gain value = 1 } }'
            for kind in ('painter', 'writer', 'sculptor'))
        works = ' '.join(
            '100 = { if = { limit = { any_artist = { artist_type = '+artist+' } } '
            'random_artist = { limit = { artist_type = '+artist+' } save_scope_as = hbe_af_art_creator } } '
            'else = { create_character = { age = { 25 50 } culture = root.culture religion = root.religion '
            'trait_category = artist artist = '+artist+' create_in_limbo = yes save_scope_as = hbe_af_art_creator } } '
            f'capital = {{ create_art = {{ type = work_of_art_type:{kind} artist = scope:hbe_af_art_creator }} }} }}'
            for kind, artist in (('painting', 'painter'), ('poem', 'writer'), ('chronicle', 'writer')))
        art = ('if = { limit = { exists = capital } random_list = { '+works+' } '
               'set_variable = { name = hbe_af_art_gain value = 1 } }')
        artist = 'random_list = { '+artists+' }'
        reward = ('if = { limit = { num_artists < modifier:num_possible_artists modifier:has_cultural_maintenance = yes } '
                  'random_list = { 50 = { '+artist+' } 50 = { '+art+' } } } else = { '+art+' } '
                  f'set_variable = {{ name = {actual} value = {{ value = var:hbe_af_artist_gain add = var:hbe_af_art_gain }} }}')
        reset = ('set_variable = { name = hbe_af_artist_gain value = 0 } '
                 'set_variable = { name = hbe_af_art_gain value = 0 } ')
    return reset+f'if = {{ limit = {{ var:hbe_af_people_{index}_{tier} = 1 }} '+reward+' }'


def preview(row, tier):
    chance = row['chance'][tier]
    if row['type'] == 'courtier':
        return f'{chance}%机会招徕一名随机廷臣。'
    return (f'{chance}%机会获得一名艺术家或一件艺术品；艺术家从画家、作家、雕塑家中抽取，'
            '作品从绘画、诗作、编年史中抽取。艺术家名额已满时改为作品。')


def receipt(row, index):
    if row['type'] == 'courtier':
        return f"实际招徕廷臣 [SCOPE.GetValue('af_actual_{index}')|0] 名。"
    return "实际招徕艺术家 [SCOPE.GetValue('af_artist_gain')|0] 名，收获艺术品 [SCOPE.GetValue('af_art_gain')|0] 件。"


def validate(mod, game, data, check):
    from pdxscript import blocks
    text = (mod/'in_game/common/scripted_effects/hbe_af_effects.txt').read_text(encoding='utf-8-sig')
    effects = {k: text[a:b] for k, _, a, b, _ in blocks(text, 0)}
    people = [p for p in data['projects'] if any(r['type'] in ('courtier','patronage') for r in p['rewards'])]
    check('two national talent projects have distinct primary rewards', len(people)==2 and
          all(p['pool']=='national' and len(p['rewards'])==3 and p['rewards'][0]['role']=='primary' for p in people) and
          {p['rewards'][0]['type'] for p in people}=={'courtier','patronage'})
    check('court recruitment uses twenty and forty percent',
          next(p['rewards'][0]['chance'] for p in people if p['rewards'][0]['type']=='courtier')==[20,40])
    for p in people:
        body=effects['hbe_af_roll_rewards_'+str(p['id'])]
        check(p['key']+' dice are locked before completion, without greatness multiplying chance',
              all(f'chance = {chance} set_variable = {{ name = hbe_af_people_0_{i}' in body for i,chance in enumerate(p['rewards'][0]['chance'])))
        for i,tier in enumerate(('small','large')):
            reward=effects[f'hbe_af_reward_{p["id"]}_{tier}']
            guard=next(reward[a:b] for k,_,a,b,_ in blocks(reward,0) if k=='if' and f'var:hbe_af_people_0_{i} = 1' in reward[a:b])
            check(p['key']+' '+tier+' creates rewards only after a successful locked roll',
                  'create_character' in guard and 'add_prestige' in reward and 'add_research_progress' in reward)
    cultural=effects['hbe_af_reward_20_small']
    check('artists respect native capacity and cultural maintenance',
          'num_artists < modifier:num_possible_artists modifier:has_cultural_maintenance = yes' in cultural and
          'create_in_limbo = yes' in cultural and 'artist = root.ruler' not in cultural)
    types=(game/'in_game/common/artist_types/00_default.txt').read_text(encoding='utf-8-sig')
    works=(game/'in_game/common/artist_work/00_default.txt').read_text(encoding='utf-8-sig')
    check('all cultural reward types exist in the installed vanilla catalogue',
          {'painter','writer','sculptor'} <= {k for k,*_ in blocks(types,0)} and
          {'painting','poem','chronicle'} <= {k for k,*_ in blocks(works,0)})
    receipts=effects['hbe_af_receipt_20']
    check('cultural receipt snapshots separate artist and artwork gains',
          'name = af_artist_gain value = var:hbe_af_artist_gain' in receipts and
          'name = af_art_gain value = var:hbe_af_art_gain' in receipts)
