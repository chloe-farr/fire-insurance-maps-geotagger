"""Street-name comparison in fim_georef.py: type-word normalisation, historic spelling folds, fuzzy pool."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fim_georef as fg  # noqa: E402

SEG = np.array([[[0.0, 0.0], [10.0, 0.0]]])


def test_spell_key_folds_both_sides():
    assert fg.spell_key("ROTHENTHURM") == fg.spell_key("ROTENTURM")
    assert fg.spell_key("CARL") == fg.spell_key("KARL")
    assert fg.spell_key("FREYUNG") == fg.spell_key("FREIUNG")
    assert fg.spell_key("JOSEPHS") == fg.spell_key("JOSEFS")
    assert fg.spell_key("YATES") == "YATES"                      # initial Y untouched
    assert fg.spell_key("CHURCH") == "CHURCH"                    # CH is not a hard C


def test_match_streets_uses_folds_and_fused_type_words():
    streets = {"ROTENTURM STRASSE": SEG, "KARNTNER STRASSE": SEG, "DOUGLAS ST": SEG}
    assert fg.match_streets("Rothenthurm-Strasse", streets, {}) == ["ROTENTURM STRASSE"]
    assert fg.match_streets("Karnthnerstraße", streets, {}) == ["KARNTNER STRASSE"]
    assert fg.match_streets("DOUGLAS", streets, {}) == ["DOUGLAS ST"]
    assert fg.match_streets("STRASSE", streets, {}) == []        # a bare type word names nothing


def test_spelling_exact_mode_keeps_letters():
    fg.SPELL_FOLD = False
    try:
        assert fg.match_streets("Rothenthurm-Strasse", {"ROTENTURM STRASSE": SEG}, {}) == []
    finally:
        fg.SPELL_FOLD = True


def test_fuzzy_reports_the_layer_spelling():
    streets = {"HIMMELPFORT GASSE": SEG, "WEIHBURG GASSE": SEG}
    keys, taken_for = fg.fuzzy_streets("Himmelfort-Gasse", streets, {})
    assert keys == ["HIMMELPFORT GASSE"] and taken_for == "HIMMELPFORT"
