"""Offline tests for scripts/fim_locate.py and the bbox helpers it shares with fim_fetch_streets.py. No network, no city names."""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fim_fetch_streets  # noqa: E402
import fim_locate as L  # noqa: E402
from fim_crs import bbox_union, pad_bbox_km  # noqa: E402
from fim_georef import street_candidates  # noqa: E402


def tok(text, x=100, y=100, **kw):
    t = {"text": text, "bbox_xyxy_source": [x - 20, y - 5, x + 20, y + 5], "dup_of": None, "id": abs(hash(text)) % 10000}
    t.update(kw)
    return t


def hit(name, lat, lon, box_km=0.5, **address):
    d = box_km / 2 / 111.32
    return {"name": name, "category": "highway", "type": "residential", "lat": lat, "lon": lon,
            "bbox_swne": [lat - d, lon - d, lat + d, lon + d], "display_name": name, "address": address, "osm_type": "way", "osm_id": 1, "importance": 0.1}


class SelectNames(unittest.TestCase):
    def test_tiers_and_skip_reasons(self):
        tokens = [tok("ALPHA ST."), tok("ALPHA"), tok("BETA ST"), tok("GAMMA"), tok("GAMMA"), tok("Delta"), tok("EPSILON"),
                  tok("ALLEY"), tok("ST WEST"), tok("SECTION 107"), tok("Alpha & Beta Co"), tok("Улица"), tok("ZETA BLK"), tok("ETA"), tok("Theta Iota Kappa Lambda")]
        queries, skipped = L.select_names(tokens, min_len=4)
        by = {q["name"]: q for q in queries}
        self.assertEqual(by["ALPHA"]["type"], "ST")  # bare ALPHA and ALPHA ST. merged
        self.assertEqual(by["ALPHA"]["occurrences"], 2)
        self.assertEqual(by["ALPHA"]["tier"], "A")
        self.assertEqual(by["ALPHA"]["query"], "Alpha Street")
        self.assertEqual(by["GAMMA"]["tier"], "B")  # bare, repeated
        self.assertEqual(by["EPSILON"]["tier"], "B")  # bare, all caps, 6+ letters
        self.assertNotIn("DELTA", by)  # bare, once, mixed case -> tier C, not queried by default
        self.assertIn("Delta", skipped["bare_tier_C"])
        self.assertIn("ALLEY", skipped["type_only"])
        self.assertIn("ST WEST", skipped["type_only"])
        self.assertIn("SECTION 107", skipped["digits"])
        self.assertIn("Alpha & Beta Co", skipped["business"])
        self.assertIn("Theta Iota Kappa Lambda", skipped["business"])
        self.assertIn("Улица", skipped["no_letters"])
        self.assertIn("ZETA BLK", skipped["furniture"])
        self.assertIn("ETA", skipped["short"])
        self.assertEqual(queries[0]["name"], "ALPHA")  # typed + repeated ranks first

    def test_sheet_type_word_and_assumed_type(self):
        tokens = [tok("ALPHA ST."), tok("ST."), tok("ST"), tok("BETA AVE"), tok("GAMMA"), tok("GAMMA")]
        self.assertEqual(L.sheet_type_word(tokens), "ST")
        queries, _ = L.select_names(tokens, default_type="ST")
        g = next(q for q in queries if q["name"] == "GAMMA")
        self.assertEqual((g["type"], g["type_assumed"], g["query"]), (None, "ST", "Gamma Street"))
        fused = [tok("Weihburggasse"), tok("Stallburggasse"), tok("Delta"), tok("Delta")]
        self.assertEqual(L.sheet_type_word(fused), "GASSE")
        d = next(q for q in L.select_names(fused, default_type="GASSE")[0] if q["name"] == "DELTA")
        self.assertEqual(d["query"], "Deltagasse")
        self.assertIsNone(L.sheet_type_word([tok("GAMMA")]))
        self.assertEqual(L.select_names([tok("GAMMA"), tok("GAMMA")])[0][0]["query"], "Gamma")

    def test_bare_all_and_force_drop(self):
        tokens = [tok("ALPHA ST"), tok("Delta")]
        queries, _ = L.select_names(tokens, bare="all")
        self.assertEqual({q["name"] for q in queries}, {"ALPHA", "DELTA"})
        queries, skipped = L.select_names(tokens, force=("Omega Road",), drop=("ALPHA ST",))
        self.assertEqual([q["name"] for q in queries], ["OMEGA"])
        self.assertEqual(queries[0]["query"], "Omega Road")
        self.assertIn("dropped", skipped)

    def test_in_block_tokens_skipped_and_fallback(self):
        ring = np.array([[0, 0], [200, 0], [200, 200], [0, 200]], np.float32).reshape(-1, 1, 2)
        inside, outside = tok("ALPHA ST", 100, 100), tok("BETA ST", 400, 400)
        street_candidates([inside, outside], [ring])
        self.assertTrue(inside["in_block"] and not outside["in_block"])
        queries, skipped = L.select_names([inside, outside])
        self.assertEqual([q["name"] for q in queries], ["BETA"])
        self.assertEqual(skipped["in_block"], ["ALPHA ST"])
        # no rings: nothing is flagged, both are queried
        a, b = tok("ALPHA ST"), tok("BETA ST")
        street_candidates([a, b], [])
        self.assertFalse(a["in_block"])
        self.assertEqual(len(L.select_names([a, b])[0]), 2)

    def test_fused_query_uses_osm_spelling(self):
        self.assertEqual(L.build_query("MUSTER", "STRASSE", ["Muster-Strasse."]), "Musterstrasse")
        self.assertEqual(L.build_query("ALPHA IM BETA", "PLATZ", ["Alpha im Beta Platz"]), "Alpha-Im-Beta-Platz")
        self.assertEqual(L.build_query("ALPHA", "AVE"), "Alpha Avenue")
        self.assertEqual(L.build_query("ALPHA", None), "Alpha")


class Clustering(unittest.TestCase):
    def test_two_places_and_homonym(self):
        P, Q = (10.0, 10.0), (12.7, 10.0)  # ~300 km apart
        rare = {f"R{i}": [hit(f"R{i}", P[0] + i * 0.002, P[1])] for i in range(4)}
        rare.update({f"S{i}": [hit(f"S{i}", Q[0] + i * 0.002, Q[1])] for i in range(2)})
        everywhere = [hit("COMMON", P[0], P[1] + 0.001), hit("COMMON", Q[0], Q[1] + 0.001)] + [hit("COMMON", -30 + i, 50 + i) for i in range(38)]
        cands = L.cluster_hits({**rare, "COMMON": everywhere}, radius_km=6.0)
        self.assertEqual(cands[0]["n_names"], 5)
        self.assertEqual(set(cands[0]["names"]), {"R0", "R1", "R2", "R3", "COMMON"})
        self.assertAlmostEqual(L.name_weight(40), 1 / math.sqrt(40))
        self.assertAlmostEqual(cands[0]["score"], 4 + 1 / math.sqrt(40), places=6)
        self.assertEqual(cands[1]["n_names"], 3)

    def test_many_segments_in_one_city_is_one_place(self):
        segs = [hit("UNIQUE", 49.28 + i * 0.001, -123.1) for i in range(38)]
        self.assertEqual(L.n_places(segs, 6.0), 1)
        self.assertEqual(L.name_weights({"UNIQUE": segs}, 6.0)["UNIQUE"], 1.0)
        self.assertEqual(L.n_places([hit("X", 0, 0), hit("X", 10, 10)], 6.0), 2)

    def test_lone_rare_name_does_not_stop_the_search(self):
        hits = {"LONE": [hit("LONE", 0.0, 0.0)],  # one hit, weight 1: the highest-scoring seed, but not a place
                "A": [hit("A", 49.28, -123.1)] + [hit("A", 20 + i, 30) for i in range(3)],
                "B": [hit("B", 49.281, -123.1)] + [hit("B", -20 - i, 30) for i in range(3)]}
        cands = L.cluster_hits(hits, radius_km=6.0)
        self.assertEqual(len(cands), 1)
        self.assertEqual(set(cands[0]["names"]), {"A", "B"})

    def test_cross_boundary_merges_at_radius(self):
        hits = {f"A{i}": [hit(f"A{i}", 50.0 + i * 0.001, 8.0)] for i in range(3)}
        hits.update({f"B{i}": [hit(f"B{i}", 50.0 + 4 / 111.32 + i * 0.001, 8.0)] for i in range(3)})  # 4 km north
        self.assertEqual(L.cluster_hits(hits, radius_km=6.0)[0]["n_names"], 6)
        two = L.cluster_hits(hits, radius_km=2.0)
        self.assertEqual([c["n_names"] for c in two], [3, 3])

    def test_candidate_bbox_long_way_and_padding(self):
        short = hit("A", 50.0, 8.0, box_km=1.0)
        long = hit("B", 50.0, 8.0)
        long["bbox_swne"] = [49.5, 7.0, 50.5, 9.0]  # a 100+ km highway: point only
        raw, padded = L.candidate_bbox([short, long], pad_km=1.0)
        self.assertLess(raw[2] - raw[0], 0.02)
        self.assertGreater((padded[2] - padded[0]) * 111.32, 2.9)
        deg = pad_bbox_km((50.0, 8.0, 50.0, 8.0), 1.0)
        self.assertAlmostEqual((deg[2] - deg[0]) * 111.32, 2.0, places=3)

    def test_core_prefers_compact_cluster_and_merge(self):
        w = {n: 1.0 for n in "ABCDEFGH"}
        spread = [hit(n, 51.5 + i * 0.05, -0.1) for i, n in enumerate("ABCDEFGH")]  # 8 names, each ~5.5 km apart
        tight = [hit(n, 48.42 + i * 0.002, -123.37) for i, n in enumerate("ABCD")]  # 4 names within 700 m
        self.assertEqual(len(L.core_of(spread, w, 1.5)["names"]), 1)
        self.assertEqual(len(L.core_of(tight, w, 1.5)["names"]), 4)
        a = {"hits": tight[:2], "names": ["A", "B"], "score": 2.0, "n_names": 2, "n_hits": 2}
        b = {"hits": tight[2:], "names": ["C", "D"], "score": 2.0, "n_names": 2, "n_hits": 2}
        far = {"hits": spread[:2], "names": ["A", "B"], "score": 2.0, "n_names": 2, "n_hits": 2}
        merged = L.merge_overlapping([a, b, far], w)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["names"], ["A", "B", "C", "D"])

    def test_describe_two_municipalities(self):
        hits = [hit("A", 0, 0, city="Alpha", state="S", country="C", country_code="cc")] * 3 + [hit("B", 0, 0, town="Beta", state="S", country="C", country_code="cc")] * 2
        place = L.describe_place(hits)
        self.assertEqual(place["municipalities"], ["Alpha", "Beta"])
        self.assertEqual(place["description"], "Alpha / Beta, S, C")
        self.assertEqual(L.slug_for(place), "alpha_locate")

    def test_fetch_command_roundtrip_and_union(self):
        box = (48.41101, -123.38354, 48.43898, -123.34646)
        cmd = L.fetch_command(box, "x")
        arg = cmd.split("--bbox ")[1].split()[0]
        parsed = fim_fetch_streets.parse_bbox(arg)
        for a, b in zip(parsed, box):
            self.assertAlmostEqual(a, b, places=4)
        self.assertEqual(bbox_union([(1, 2, 3, 4), (0, 3, 2, 5)]), (0.0, 2.0, 3.0, 5.0))


if __name__ == "__main__":
    unittest.main()
