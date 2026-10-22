import unittest
from normalize_concept_labels import names, normalize
from normalize_concept_labels import dedicated_labels_override_fallbacks
from pathlib import Path
import tempfile


class ConceptLabelsTest(unittest.TestCase):
    def test_dedicated_feature_owns_label_without_removing_core_only_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            core=Path(tmp)/'hbe_l_english.yml';feature=Path(tmp)/'hbe_feature_l_english.yml'
            core.write_text('l_english:\n hbe_shared: "old fallback"\n hbe_core: "keep"\n',encoding='utf-8')
            feature.write_text('l_english:\n hbe_shared: "feature wording"\n',encoding='utf-8')
            self.assertEqual(dedicated_labels_override_fallbacks([core,feature],core),1)
            self.assertNotIn('hbe_shared:',core.read_text(encoding='utf-8'))
            self.assertIn('hbe_core: "keep"',core.read_text(encoding='utf-8'))
            self.assertEqual(dedicated_labels_override_fallbacks([core,feature],core),0)

    def test_nested_title_is_rendered_before_comparison(self):
        actual=names({'game_concept_hbe_term_regional':"[Concept('hbe_term_local_service', '地方事业')|e]交付"})
        self.assertEqual(actual,{'hbe_term_regional':'地方事业交付'})

    def test_all_aliases_share_one_gameplay_name(self):
        text="[Concept('hbe_term_contract', '旧约')|e]与[Concept('hbe_term_contract', '契书')|e]"
        actual=normalize(text,{'hbe_term_contract':'共同契约'})
        self.assertEqual(actual.count("'共同契约'"),2)
        self.assertEqual(actual,normalize(actual,{'hbe_term_contract':'共同契约'}))

    def test_history_and_native_functions_stay_intact(self):
        text="[Concept('hbe_history_zigong_fossils', '龙骨')|e]：[Player.GetName]"
        self.assertEqual(normalize(text,{'hbe_term_contract':'共同契约'}),text)


if __name__=='__main__':unittest.main()
