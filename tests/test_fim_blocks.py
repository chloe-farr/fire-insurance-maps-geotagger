"""White-space classification of fim_blocks.py on a synthetic sheet: a street corridor, a closed block, and a block whose
frontage line has a gap so its interior leaks into the street."""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fim_blocks as fb  # noqa: E402


def sheet():
    """600x600 work px. Frame at the border, a horizontal street corridor (y 250-350) crossing the sheet, a closed block
    above it and a block below whose top frontage line has a 12 px gap. Returns (white mask, box, gap centre, centres)."""
    ink = np.zeros((600, 600), np.uint8)
    cv2.rectangle(ink, (5, 5), (594, 594), 1, 2)          # frame
    cv2.rectangle(ink, (60, 40), (540, 250), 1, 2)         # closed block (interior 480x210 = 28% of the sheet)
    cv2.rectangle(ink, (60, 350), (540, 560), 1, 2)        # leaky block
    ink[349:352, 294:306] = 0                              # 12 px gap in its top frontage
    for x in range(80, 540, 60):                           # dashed lot lines inside the leaky block
        for y in range(360, 550, 14):
            ink[y:y + 7, x:x + 2] = 1
    sealed = cv2.dilate(ink, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    content = np.zeros_like(ink); content[8:592, 8:592] = 1
    white = ((1 - sealed) & content).astype(np.uint8)
    return white, [8, 8, 592, 592], (300, 300), (300, 150), (300, 450)


def test_plain_rule_keeps_closed_block_and_loses_leaky_one():
    white, box, street_pt, closed_pt, leaky_pt = sheet()
    args = fb.default_args(Path("."), seal=3, neck_px=0, lot_max=0.05, max_area=0.5)
    enclosed, notes, _ = fb.classify_white(white, box, args, None)
    assert enclosed[closed_pt[1], closed_pt[0]] == 1      # closed interior is enclosed (28% > lot_max but not on border)
    assert enclosed[street_pt[1], street_pt[0]] == 0      # corridor is street
    assert enclosed[leaky_pt[1], leaky_pt[0]] == 0        # leaked interior went with the street


def test_seeded_neck_carving_recovers_leaky_block():
    white, box, street_pt, closed_pt, leaky_pt = sheet()
    paint = np.zeros_like(white); cv2.line(paint, (20, 300), (580, 300), 1, 2)   # modern centreline down the corridor
    args = fb.default_args(Path("."), seal=3, neck_px=16, lot_max=0.05, max_area=0.5, seed_px=20, open_max=0.10)
    enclosed, notes, recovered = fb.classify_white(white, box, args, paint)
    assert enclosed[street_pt[1], street_pt[0]] == 0
    assert enclosed[closed_pt[1], closed_pt[0]] == 1
    assert enclosed[leaky_pt[1], leaky_pt[0]] == 1        # interior pinched off at the 12 px gap and kept
    assert notes["recovered"] >= 1                        # (the corridor is the largest piece, so it needs no centreline seed here)
    assert recovered[leaky_pt[1], leaky_pt[0]] == 1       # and the recovered-interior mask marks it


def test_numeral_reads_fused_block_label():
    assert fb.numeral({"text": "BLOCK 50"}) == "50"
    assert fb.numeral({"text": "16½"}) == "16½"
    assert fb.numeral({"text": "YATES BLK"}) is None


def test_floors_rule_sanborn_opt_in():
    assert fb.floors_of(["2"]) == 2
    assert fb.floors_of(["1½"]) == 1.5
    assert fb.floors_of(["3"]) == 3
    assert fb.floors_of(["4"]) is None                # outside 1-3: a lot number, not floors
    assert fb.floors_of(["1", "2"]) is None            # several numerals: ambiguous
    assert fb.floors_of([]) is None
    assert fb.floors_of(["1895"]) is None
