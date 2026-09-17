# Run history

Generated 2026-09-17 by `scripts/fim_run_history.py` from `runs/`. Re-run it after adding runs.


## HunyuanOCR (`tencent/HunyuanOCR`)

`verdict`: **collapsed** = < 3 KB returned (orientation defeated the model); **runaway/cap** = hit `max_new_tokens`, tail is repetition; **ok** = plausible transcript. Tiled runs list per-tile stats instead.


### runs/hunyuan/2026-09-10_tiles_p06b — tiled (3×3, rotations [0], 1536 px tiles, ≥192 px overlap, work 3788×4096 @ 0.489)

Source `p06b.jpg` 7742×8372; crop 300,150,7000,7980; prompt “This is a fire insurance map of Victoria B.C. in 1895. Return the text…”; cap 8192 tok/tile. **9/9 tiles OCR'd, 373 tokens parsed, 154 overlap duplicates removed, 219 kept.**

| tile | box (work px) | ink | out tok | chars | tokens | cap hit |
|---|---|---|---|---|---|---|
| r0c0 | (147,73)–(1683,1609) | 0.016 | 379 | 548 | 27 | no |
| r0c1 | (1018,73)–(2554,1609) | 0.021 | 1019 | 1496 | 72 | no |
| r0c2 | (1889,73)–(3425,1609) | 0.029 | 1040 | 1535 | 73 | no |
| r1c0 | (147,1221)–(1683,2757) | 0.014 | 115 | 174 | 8 | no |
| r1c1 | (1018,1221)–(2554,2757) | 0.019 | 623 | 914 | 44 | no |
| r1c2 | (1889,1221)–(3425,2757) | 0.043 | 1035 | 1495 | 71 | no |
| r2c0 | (147,2368)–(1683,3904) | 0.011 | 130 | 196 | 8 | no |
| r2c1 | (1018,2368)–(2554,3904) | 0.020 | 338 | 497 | 24 | no |
| r2c2 | (1889,2368)–(3425,3904) | 0.049 | 653 | 959 | 46 | no |

Alphabetic tokens kept (dedupe check by eye): ALLEY, AVE, BASTION, BASTION SQUARE, BROUGHTON, CHANCERY LANE, COMMERCIAL, COURT ALLEY, FORT, Harbour, JOHNSON, LANGLEY, LAW COURTS, ORIENTAL, PROVINCIAL, SCALE 50 FT = 1INCH, Victoria, VICTORIA-B.C.-, WADDINGTON, YATES

### runs/hunyuan/2026-09-10_tiles_p06b_pass2 — tiled (3×2, rotations [0], 1536 px tiles, ≥192 px overlap, work 3788×4096 @ 0.489)

Source `p06b.jpg` 7742×8372; crop 300,150,7000,7980; prompt “This is a fire insurance map of Victoria B.C. in 1895. Return the text…”; cap 8192 tok/tile. **6/6 tiles OCR'd, 476 tokens parsed, 246 overlap duplicates removed, 230 kept.**

| tile | box (work px) | ink | out tok | chars | tokens | cap hit |
|---|---|---|---|---|---|---|
| r0c0 | (582,647)–(2118,2183) | 0.020 | 523 | 769 | 37 | no |
| r0c1 | (1889,647)–(3425,2183) | 0.035 | 1061 | 1570 | 73 | no |
| r1c0 | (582,1507)–(2118,3043) | 0.019 | 330 | 487 | 23 | no |
| r1c1 | (1889,1507)–(3425,3043) | 0.045 | 1016 | 1493 | 70 | no |
| r2c0 | (582,2368)–(2118,3904) | 0.016 | 120 | 180 | 8 | no |
| r2c1 | (1889,2368)–(3425,3904) | 0.049 | 653 | 959 | 46 | no |

Alphabetic tokens kept (dedupe check by eye): ALLEY, AVE, BASTION, BASTION SQUARE, BROUGHTON, CHANCERY LANE, COMMERCIAL, COURT ALLEY, FORT, Harbour, JOHNSON, LANGLEY, LAW COURTS, ORIENTAL, PROVINCIAL, SCALE 50 FT = 1INCH, Victoria, VICTORIA-B.C.-, WADDINGTON, WHARF, YATES

### runs/hunyuan/2026-09-10_tiles_p06b_rot — tiled (3×3, rotations [0, 30, 60], 1536 px tiles, ≥192 px overlap, work 3788×4096 @ 0.489)

Source `p06b.jpg` 7742×8372; crop 300,150,7000,7980; prompt “This is a fire insurance map of Victoria B.C. in 1895. Return the text…”; cap 8192 tok/tile. **9/9 tiles OCR'd, 988 tokens parsed, 736 overlap duplicates removed, 252 kept.**

| tile | box (work px) | ink | out tok | chars | tokens | cap hit |
|---|---|---|---|---|---|---|
| r0c0 | (147,73)–(1683,1609) | 0.016 | 379 | 548 | 69 | no |
| r0c1 | (1018,73)–(2554,1609) | 0.021 | 1019 | 1496 | 193 | no |
| r0c2 | (1889,73)–(3425,1609) | 0.029 | 1040 | 1535 | 196 | no |
| r1c0 | (147,1221)–(1683,2757) | 0.014 | 115 | 174 | 26 | no |
| r1c1 | (1018,1221)–(2554,2757) | 0.019 | 623 | 914 | 110 | no |
| r1c2 | (1889,1221)–(3425,2757) | 0.043 | 1035 | 1495 | 188 | no |
| r2c0 | (147,2368)–(1683,3904) | 0.011 | 130 | 196 | 16 | no |
| r2c1 | (1018,2368)–(2554,3904) | 0.020 | 338 | 497 | 64 | no |
| r2c2 | (1889,2368)–(3425,3904) | 0.049 | 653 | 959 | 126 | no |

Alphabetic tokens kept (dedupe check by eye): ALLEY, AVE, BASTION, BASTION SQUARE, BROUGHTON, CHANCERY LANE, COMMERCIAL ST, COURT ALLEY, FORT, Harbour, JOHNSON, LANGLEY, LAW COURTS, ORIENTAL, PROVINCIAL, SCALE 50 FT = 1 INCH, SCALE 50 FT = 1INCH, Vic T O, Vicona, Victoria, VICTORIA-B.C.-, WADDINGTON, WHARF, YATES

### runs/hunyuan/2026-09-14_tiles_p02_t1024_rot — tiled (5×4, rotations [0, 30, 60], 1024 px tiles, ≥192 px overlap, work 3792×4096 @ 0.487)

Source `p02.jpg` 7794×8418; crop 200,100,6850,8020; prompt “This is a fire insurance map of Victoria B.C. in 1895. Return the text…”; cap 4096 tok/tile. **20/20 tiles OCR'd, 2018 tokens parsed, 1086 overlap duplicates removed, 932 kept.**

| tile | box (work px) | ink | out tok | chars | tokens | cap hit |
|---|---|---|---|---|---|---|
| r0c0 | (97,49)–(1121,1073) | 0.053 | 517 | 822 | 106 | no |
| r0c1 | (834,49)–(1858,1073) | 0.036 | 106 | 192 | 21 | no |
| r0c2 | (1572,49)–(2596,1073) | 0.017 | 189 | 299 | 32 | no |
| r0c3 | (2309,49)–(3333,1073) | 0.032 | 476 | 725 | 75 | no |
| r1c0 | (97,756)–(1121,1780) | 0.040 | 1606 | 2540 | 253 | no |
| r1c1 | (834,756)–(1858,1780) | 0.028 | 288 | 448 | 45 | no |
| r1c2 | (1572,756)–(2596,1780) | 0.022 | 807 | 1275 | 141 | no |
| r1c3 | (2309,756)–(3333,1780) | 0.039 | 980 | 1500 | 171 | no |
| r2c0 | (97,1463)–(1121,2487) | 0.021 | 635 | 1134 | 478 | no |
| r2c1 | (834,1463)–(1858,2487) | 0.017 | 263 | 408 | 42 | no |
| r2c2 | (1572,1463)–(2596,2487) | 0.031 | 915 | 1405 | 151 | no |
| r2c3 | (2309,1463)–(3333,2487) | 0.040 | 693 | 1055 | 129 | no |
| r3c0 | (97,2171)–(1121,3195) | 0.029 | 141 | 217 | 23 | no |
| r3c1 | (834,2171)–(1858,3195) | 0.017 | 328 | 490 | 57 | no |
| r3c2 | (1572,2171)–(2596,3195) | 0.039 | 274 | 410 | 46 | no |
| r3c3 | (2309,2171)–(3333,3195) | 0.074 | 526 | 835 | 105 | no |
| r4c0 | (97,2878)–(1121,3902) | 0.064 | 76 | 105 | 11 | no |
| r4c1 | (834,2878)–(1858,3902) | 0.067 | 205 | 315 | 43 | no |
| r4c2 | (1572,2878)–(2596,3902) | 0.083 | 246 | 468 | 32 | no |
| r4c3 | (2309,2878)–(3333,3902) | 0.106 | 363 | 633 | 57 | no |

Alphabetic tokens kept (dedupe check by eye): 1ST 2ND 1ST&3RD 2ND&4TH-IRON SHUTTERS., A CONTINUED FROM BELOW, ABOVE, ADMIRAL ROAD, AFFORDABLE, ALBANY, ALDERMAN, ALPHA, ALSTON, ANDREW, ANOBEN, ANSON, ARE, ARMIT, BARNS, BAY, Bay, BELTON AVE., BEN, BETA, BLACK, BLUE, BOILERS, Brew, BREWEN, BREWERY, BRICK, BRICK PARAPET WALL., BRIDGE, BRIK, BRINGFIELD, BROAD, BROKEN LINE), BROKENLINE, BROUGH, BUILDINGS, BURNSIDE ROAD, CARRIE, CARROLL, CASTOR, CATAL, CATHERINE, CECILIA, CHARLES, Church, CITY, CITY LIMIT, Co. Wheat, COLORED, COLVILLE ROAD, COMPOSITION, CONNAUGHT, CONNAUGHT ROAD, Constance, Constance Core B, CONTINUED, CORNICE, Cove, CRAIGFLOWER, CUT, Dairy Dock, DALLAS, DALLAS ROAD, DAVID, DD=DETACHED DWELLINGS.S.D.SCATTERED DWGS., DELTA, DOMINION, DOUGLASS ROAD, DRY Dock, DUNEDON, DUNEGON, DUNSMUIR, EASTE, EDERICA, EDGED, EDWARD, ELECTRIC, Electric Tramway, Electrics, Electrics Teamway…

### runs/hunyuan/2026-09-14_tiles_p03_t1024_rot — tiled (5×4, rotations [0, 30, 60], 1024 px tiles, ≥192 px overlap, work 3788×4096 @ 0.489)

Source `p03.jpg` 7742×8372; crop 200,100,6950,7980; prompt “This is a fire insurance map of Victoria B.C. in 1895. Return the text…”; cap 4096 tok/tile. **20/20 tiles OCR'd, 2982 tokens parsed, 2070 overlap duplicates removed, 912 kept.**

| tile | box (work px) | ink | out tok | chars | tokens | cap hit |
|---|---|---|---|---|---|---|
| r0c0 | (98,49)–(1122,1073) | 0.048 | 886 | 1361 | 156 | no |
| r0c1 | (857,49)–(1881,1073) | 0.022 | 644 | 980 | 104 | no |
| r0c2 | (1617,49)–(2641,1073) | 0.023 | 653 | 1023 | 129 | no |
| r0c3 | (2376,49)–(3400,1073) | 0.062 | 591 | 953 | 100 | no |
| r1c0 | (98,757)–(1122,1781) | 0.084 | 1391 | 2119 | 261 | no |
| r1c1 | (857,757)–(1881,1781) | 0.040 | 1363 | 2063 | 325 | no |
| r1c2 | (1617,757)–(2641,1781) | 0.015 | 1293 | 1970 | 229 | no |
| r1c3 | (2376,757)–(3400,1781) | 0.027 | 664 | 999 | 102 | no |
| r2c0 | (98,1465)–(1122,2489) | 0.090 | 1600 | 2419 | 200 | no |
| r2c1 | (857,1465)–(1881,2489) | 0.066 | 1973 | 2968 | 334 | no |
| r2c2 | (1617,1465)–(2641,2489) | 0.016 | 725 | 1059 | 114 | no |
| r2c3 | (2376,1465)–(3400,2489) | 0.025 | 168 | 264 | 27 | no |
| r3c0 | (98,2172)–(1122,3196) | 0.101 | 1487 | 2288 | 260 | no |
| r3c1 | (857,2172)–(1881,3196) | 0.061 | 1410 | 2131 | 235 | no |
| r3c2 | (1617,2172)–(2641,3196) | 0.012 | 364 | 557 | 60 | no |
| r3c3 | (2376,2172)–(3400,3196) | 0.038 | 117 | 190 | 20 | no |
| r4c0 | (98,2880)–(1122,3904) | 0.130 | 1089 | 1670 | 208 | no |
| r4c1 | (857,2880)–(1881,3904) | 0.084 | 598 | 903 | 99 | no |
| r4c2 | (1617,2880)–(2641,3904) | 0.012 | 48 | 64 | 5 | no |
| r4c3 | (2376,2880)–(3400,3904) | 0.048 | 76 | 113 | 14 | no |

Alphabetic tokens kept (dedupe check by eye): 100 FEET = 1 INCH, 100 FEET = 11INCH, 136,605)INCLUDING, 16 SUPERIOR, 28 HALL, 309,869)Gead, 3RD STREET, 50 FEET = 11INCH, 500 FEET = 1 INCH, 54MICHIGAN, 80 Episcopal, Albion, ALE : 500 FEET = 11NCH, ALFRED, AMBRIDGE, AMELIA, AMERICA, ANDREWS, Angela, ARBOUR, AREA, ASJAMES, AVALON RD., AVE, AVE., AVENUE, BALL, BANK, BARRY, BASTION, BASTON, BATTERY, Bay, BAY, BAY AVE., Bay Fire, BAY ROAD, BAYE, Beacon, BEACON, BEECHY, BELCHER, BELCHER AVE., BELGHER, BELLEVILLE, BELLOT, BENCHARD, BIRD, BLANCHARD, BLOVER, BODWELL, BOVD, BOWELL, BRAD, BREWERY, BRINCES, British Columbia, BROAD, BROO, BROUGHTON, Bruge, Buildings, BurDETT, BURKE LAWY, CADBORO, Caledonia, CALEDONIA AVE, CARR, Cathedral, CEDAR HILL ROAD, Cemetery, CENTRAL, CHA, Cha's E.Goad, CHAMBERS, CHANDLER AVE., Chas E. Goad, CHATHAM, CHATT, CHESNUT…

### runs/hunyuan/2026-09-14_tiles_p25_rot — tiled (3×3, rotations [0, 30, 60], 1536 px tiles, ≥192 px overlap, work 3792×4096 @ 0.487)

Source `p25.jpg` 7794×8418; crop 250,120,7110,8040; prompt “This is a fire insurance map of Victoria B.C. in 1895. Return the text…”; cap 8192 tok/tile. **9/9 tiles OCR'd, 6871 tokens parsed, 1919 overlap duplicates removed, 4952 kept.**

| tile | box (work px) | ink | out tok | chars | tokens | cap hit |
|---|---|---|---|---|---|---|
| r0c0 | (122,58)–(1658,1594) | 0.036 | 8192 | 11668 | 869 | **yes** |
| r0c1 | (1023,58)–(2559,1594) | 0.049 | 8192 | 1155 | 630 | **yes** |
| r0c2 | (1924,58)–(3460,1594) | 0.125 | 3112 | 4470 | 632 | no |
| r1c0 | (122,1217)–(1658,2753) | 0.035 | 8192 | 11735 | 1140 | **yes** |
| r1c1 | (1023,1217)–(2559,2753) | 0.031 | 8192 | 6567 | 648 | **yes** |
| r1c2 | (1924,1217)–(3460,2753) | 0.116 | 2607 | 3817 | 460 | no |
| r2c0 | (122,2376)–(1658,3912) | 0.053 | 4320 | 6253 | 1063 | no |
| r2c1 | (1023,2376)–(2559,3912) | 0.038 | 3481 | 5063 | 916 | no |
| r2c2 | (1924,2376)–(3460,3912) | 0.121 | 2939 | 4295 | 513 | no |

Alphabetic tokens kept (dedupe check by eye): 2 GRO., 2STOWDING, [BLM. 217], ABOVE, ALL, and marked N, AVENUE, BAKER, BAKERY, BANERY, BANKER, BARBER, BELOW, BOILED, Boller, BUL.27, Bull, CADBORO, CADBORO BAY, CAMP, CARP, CHAM, COOK, DATING, DAWN, Drill Shed, Driv Shed, DUB, ELECTRIC, FORT, FREDERICK, FROM, GEE, GEORGE, Glass, GREEN, GRO, GYMNASIUM, Heated, HSE, I CONTINUED, JANUARY, Johnson, JOHNSON, Joun, Journons, LIBRARY, MAY 1891-, MEARES, MOSS, N.B. Veneered Buildings are colored red, N.B. Verified/Building, N.PARK, NORTH, NORTH PARK, out, PANDORA, PARK, PUBLIC, REBECCA, ROAD, Scale 100 Feet to 1 Inch., Scale 1000, Scale 400 Feet to 1 Inch., SCHOOL, SEE, SEE SHEET, SEE SHEET NO.30, SHEET, STABLE, STO, TRAMNAV, TRAMWAV, TRAMWAY, VAN, VANCOU, VANCOUVER, VATES, VICTOFA, VICTOR A B.C-…

### runs/hunyuan/2026-09-14_tiles_p25_t1024 — tiled (5×4, rotations [0], 1024 px tiles, ≥192 px overlap, work 3792×4096 @ 0.487)

Source `p25.jpg` 7794×8418; crop 250,120,7110,8040; prompt “This is a fire insurance map of Victoria B.C. in 1895. Return the text…”; cap 4096 tok/tile. **20/20 tiles OCR'd, 2666 tokens parsed, 756 overlap duplicates removed, 1910 kept.**

| tile | box (work px) | ink | out tok | chars | tokens | cap hit |
|---|---|---|---|---|---|---|
| r0c0 | (122,58)–(1146,1082) | 0.038 | 2749 | 3940 | 193 | no |
| r0c1 | (893,58)–(1917,1082) | 0.036 | 2398 | 3456 | 168 | no |
| r0c2 | (1665,58)–(2689,1082) | 0.060 | 1842 | 2660 | 129 | no |
| r0c3 | (2436,58)–(3460,1082) | 0.146 | 1336 | 1907 | 93 | no |
| r1c0 | (122,766)–(1146,1790) | 0.031 | 2257 | 3236 | 158 | no |
| r1c1 | (893,766)–(1917,1790) | 0.030 | 1288 | 1883 | 90 | no |
| r1c2 | (1665,766)–(2689,1790) | 0.052 | 1346 | 1950 | 94 | no |
| r1c3 | (2436,766)–(3460,1790) | 0.161 | 1542 | 2248 | 107 | no |
| r2c0 | (122,1473)–(1146,2497) | 0.040 | 1793 | 2648 | 126 | no |
| r2c1 | (893,1473)–(1917,2497) | 0.033 | 1859 | 2752 | 130 | no |
| r2c2 | (1665,1473)–(2689,2497) | 0.025 | 1678 | 2438 | 119 | no |
| r2c3 | (2436,1473)–(3460,2497) | 0.159 | 877 | 1327 | 60 | no |
| r3c0 | (122,2180)–(1146,3204) | 0.047 | 1623 | 2371 | 114 | no |
| r3c1 | (893,2180)–(1917,3204) | 0.036 | 4096 | 5789 | 275 | **yes** |
| r3c2 | (1665,2180)–(2689,3204) | 0.035 | 4096 | 5796 | 281 | **yes** |
| r3c3 | (2436,2180)–(3460,3204) | 0.162 | 1148 | 1687 | 80 | no |
| r4c0 | (122,2888)–(1146,3912) | 0.070 | 2118 | 3103 | 149 | no |
| r4c1 | (893,2888)–(1917,3912) | 0.048 | 1882 | 2715 | 133 | no |
| r4c2 | (1665,2888)–(2689,3912) | 0.040 | 1342 | 1922 | 95 | no |
| r4c3 | (2436,2888)–(3460,3912) | 0.159 | 1050 | 1525 | 72 | no |

Alphabetic tokens kept (dedupe check by eye): 20 OVEN, ABOVE, ALFRED, ALL, and marked, AVENUE, BAKER, BAKERY, BAY, BELOW, bodies, CABINET, CADBORO, CARP, CHAN, CIGAR, COLLEGE., CONTINUED, COOK, Creek, Drill Shed, ELECTRIC, ELIZABETH, FAC, FARM, FORT, FRED, FREDERICK, FROM, GARBORO, GEORGE, Glass, GREEN, GRO., GYMNASIUM, HSE, I CONTINUED, JOHNSON, Johnson, Jounsen, LOUIS, MAY 1891, Moss, N.B. Veneered Buildings are colored red, N.PARK, NORTH, ONING, OUT, OVER, PANDORA, PARIS, PARK, PUBLIC, PUTNAM, REBECCA, ROAD, Scale 400 Feet to 1 Inch., SCHOOL, School, SEE, SEE SHE, SEE SHEET NO 24 MEARES ST., SEE SHEET NO.30, SHEET, St. Louis, ST. LOUIS, STABLE, TRAMWAY, UGB, VANCOUVER, VATES, VICTOR A B.C., VIEW, YATES, YAYES

### runs/hunyuan/2026-09-15_tiles_vancouver_1912_MAP342a_04 — tiled (5×5, rotations [0, 30, 60], 1536 px tiles, ≥192 px overlap, work 5991×5719 @ 1.000)

Source `vancouver_1912_MAP342a_04.tif` 5991×5719; crop —; prompt “This is a fire insurance map of Vancouver B.C. in 1912. Return the tex…”; cap 8192 tok/tile. **15/25 tiles OCR'd, 2910 tokens parsed, 983 overlap duplicates removed, 1927 kept.**

| tile | box (work px) | ink | out tok | chars | tokens | cap hit |
|---|---|---|---|---|---|---|
| r0c0 | (0,0)–(1536,1536) | 0.001 | — | — | — | skipped_blank |
| r0c1 | (1114,0)–(2650,1536) | 0.006 | 105 | 165 | 20 | no |
| r0c2 | (2228,0)–(3764,1536) | 0.005 | 135 | 200 | 29 | no |
| r0c3 | (3341,0)–(4877,1536) | 0.000 | — | — | — | skipped_blank |
| r0c4 | (4455,0)–(5991,1536) | 0.000 | — | — | — | skipped_blank |
| r1c0 | (0,1046)–(1536,2582) | 0.041 | 455 | 738 | 80 | no |
| r1c1 | (1114,1046)–(2650,2582) | 0.090 | 459 | 738 | 58 | no |
| r1c2 | (2228,1046)–(3764,2582) | 0.057 | 214 | 341 | 43 | no |
| r1c3 | (3341,1046)–(4877,2582) | 0.014 | 123 | 190 | 13 | no |
| r1c4 | (4455,1046)–(5991,2582) | 0.002 | — | — | — | skipped_blank |
| r2c0 | (0,2092)–(1536,3628) | 0.046 | 518 | 793 | 147 | no |
| r2c1 | (1114,2092)–(2650,3628) | 0.126 | 1122 | 1664 | 406 | no |
| r2c2 | (2228,2092)–(3764,3628) | 0.128 | 654 | 988 | 619 | no |
| r2c3 | (3341,2092)–(4877,3628) | 0.064 | 8192 | 2284 | 728 | **yes** |
| r2c4 | (4455,2092)–(5991,3628) | 0.004 | — | — | — | skipped_blank |
| r3c0 | (0,3137)–(1536,4673) | 0.004 | — | — | — | skipped_blank |
| r3c1 | (1114,3137)–(2650,4673) | 0.059 | 8192 | 562 | 156 | **yes** |
| r3c2 | (2228,3137)–(3764,4673) | 0.107 | 1530 | 2313 | 225 | no |
| r3c3 | (3341,3137)–(4877,4673) | 0.079 | 941 | 1401 | 224 | no |
| r3c4 | (4455,3137)–(5991,4673) | 0.001 | — | — | — | skipped_blank |
| r4c0 | (0,4183)–(1536,5719) | 0.000 | — | — | — | skipped_blank |
| r4c1 | (1114,4183)–(2650,5719) | 0.003 | — | — | — | skipped_blank |
| r4c2 | (2228,4183)–(3764,5719) | 0.023 | 600 | 827 | 64 | no |
| r4c3 | (3341,4183)–(4877,5719) | 0.030 | 329 | 453 | 98 | no |
| r4c4 | (4455,4183)–(5991,5719) | 0.000 | — | — | — | skipped_blank |

Alphabetic tokens kept (dedupe check by eye): & Company, 219,915)Water Line, 4 Company, ABBOTT, acitic, Alexander, ALLEY, Atlantec, Ave, B.C. Electric Ry Co, B.C. Electric Ry Co., Bank, BANK, BLACK, Bldg., Blein Co., BLM., BOR, Bra, BRISBERRY BLACK, BRON, Budweiser, Building, Buildings, Bullers, Burward, CAMBIE, Carder, Chambers, Clarke & Stewart, Co Limited, Cobalt Bros. Ltd., Commercial, Company, CORDOVA ST. WEST, CORDOVA ST.WEST, Cordova., Cordovia, Crenne, CRIMID, D. Speer, D. Speier, DAT., Departmental, Deportemental, DISTRICT, DISTRICT LOT 541, Dogs, Dominion, Express Co., Fedde, Freight Shed, FRI, Gavitt Bros., Grain Shed, Grand, Grandview, GRANVILLE ST., Griffin Brooke, HASTINGS ST. WEST, Hight shed, Hobel, Homer, HOMER ST., Hotel, HOTEL, Hotel., Huckay Smi, ian pacific, IBIE ST., Ice House., INLET, inol, JLockie Co, Johnston Bros., Jones Building, Kelly, Douglas, Lavare, Line os on P, Loray Post…

### runs/hunyuan/2026-09-15_tiles_vienna_1912_innere_stadt — tiled (6×6, rotations [0, 30, 60], 1024 px tiles, ≥192 px overlap, work 4800×4800 @ 1.000)

Source `vienna_1912_generalstadtplan_innere_stadt.png` 4800×4800; crop —; prompt “This is a city plan of Vienna, Austria, from 1912, with German street …”; cap 4096 tok/tile. **36/36 tiles OCR'd, 4426 tokens parsed, 1150 overlap duplicates removed, 3276 kept.**

| tile | box (work px) | ink | out tok | chars | tokens | cap hit |
|---|---|---|---|---|---|---|
| r0c0 | (0,0)–(1024,1024) | 0.289 | 319 | 520 | 88 | no |
| r0c1 | (755,0)–(1779,1024) | 0.328 | 1101 | 1630 | 121 | no |
| r0c2 | (1510,0)–(2534,1024) | 0.327 | 804 | 1221 | 336 | no |
| r0c3 | (2266,0)–(3290,1024) | 0.289 | 306 | 469 | 91 | no |
| r0c4 | (3021,0)–(4045,1024) | 0.255 | 147 | 232 | 43 | no |
| r0c5 | (3776,0)–(4800,1024) | 0.257 | 402 | 613 | 131 | no |
| r1c0 | (0,755)–(1024,1779) | 0.363 | 408 | 612 | 90 | no |
| r1c1 | (755,755)–(1779,1779) | 0.358 | 4096 | 3987 | 388 | **yes** |
| r1c2 | (1510,755)–(2534,1779) | 0.353 | 112 | 193 | 37 | no |
| r1c3 | (2266,755)–(3290,1779) | 0.320 | 633 | 957 | 100 | no |
| r1c4 | (3021,755)–(4045,1779) | 0.353 | 47 | 70 | 64 | no |
| r1c5 | (3776,755)–(4800,1779) | 0.304 | 364 | 575 | 42 | no |
| r2c0 | (0,1510)–(1024,2534) | 0.378 | 16 | 23 | 273 | no |
| r2c1 | (755,1510)–(1779,2534) | 0.330 | 36 | 58 | 66 | no |
| r2c2 | (1510,1510)–(2534,2534) | 0.317 | 17 | 29 | 134 | no |
| r2c3 | (2266,1510)–(3290,2534) | 0.315 | 4096 | 5943 | 266 | **yes** |
| r2c4 | (3021,1510)–(4045,2534) | 0.377 | 33 | 48 | 44 | no |
| r2c5 | (3776,1510)–(4800,2534) | 0.360 | 4096 | 4386 | 341 | **yes** |
| r3c0 | (0,2266)–(1024,3290) | 0.408 | 795 | 1248 | 103 | no |
| r3c1 | (755,2266)–(1779,3290) | 0.344 | 4096 | 6205 | 78 | **yes** |
| r3c2 | (1510,2266)–(2534,3290) | 0.295 | 308 | 489 | 61 | no |
| r3c3 | (2266,2266)–(3290,3290) | 0.340 | 35 | 57 | 93 | no |
| r3c4 | (3021,2266)–(4045,3290) | 0.387 | 957 | 1277 | 133 | no |
| r3c5 | (3776,2266)–(4800,3290) | 0.320 | 694 | 1047 | 74 | no |
| r4c0 | (0,3021)–(1024,4045) | 0.416 | 12 | 23 | 17 | no |
| r4c1 | (755,3021)–(1779,4045) | 0.388 | 564 | 861 | 135 | no |
| r4c2 | (1510,3021)–(2534,4045) | 0.343 | 634 | 982 | 75 | no |
| r4c3 | (2266,3021)–(3290,4045) | 0.377 | 4096 | 5459 | 346 | **yes** |
| r4c4 | (3021,3021)–(4045,4045) | 0.361 | 844 | 1264 | 76 | no |
| r4c5 | (3776,3021)–(4800,4045) | 0.281 | 493 | 775 | 90 | no |
| r5c0 | (0,3776)–(1024,4800) | 0.204 | 219 | 339 | 16 | no |
| r5c1 | (755,3776)–(1779,4800) | 0.298 | 754 | 1182 | 95 | no |
| r5c2 | (1510,3776)–(2534,4800) | 0.344 | 773 | 1185 | 129 | no |
| r5c3 | (2266,3776)–(3290,4800) | 0.320 | 447 | 684 | 111 | no |
| r5c4 | (3021,3776)–(4045,4800) | 0.243 | 558 | 855 | 127 | no |
| r5c5 | (3776,3776)–(4800,4800) | 0.241 | 8 | 26 | 12 | no |

Alphabetic tokens kept (dedupe check by eye): 109 Jordanauße, 140 Stern-Gasse, 141 Stern-, 1792 Gymnasium, 1850-60 enthaut), 4 Stock, 4. Stadt 1862, 4. Stock 1862, A. stria-brunne, Abbroch, Abe, Albrecht, Albrecht-Gasse, Altenkirchen, Altes Rathaus 1/65, angelogt 1818., Anlage 1863-1864, Anstalt, Anstatt, Arpr-Land, Bank, Begomen 1868, Bei hans-Platz, Beiche-Kriege, Beitschul-Gasse, Beitschule, Benedictiner, Biber, Bibliothek, Bihrich-Gasse, Bof, Bogarten-Game, Bohenalaufer-Gasse, Braherson, Brandstäbe, Brsher, Brucke, Brunnbilch, Brunner-Strasse, Bschule, Bull-Gasse, Bund, Bäcker-Strasse, Capelle, Cavrman, Centrelle, Cobderi-Gasse, Comhure, ConcordiaPlats, Conradlzatz, Cursalor, dienstagchen Oderma, dienstern, Dire, Domi-, Dominikaner, DONAU-, Dorafleger-Gasse, Dorinikener, Drafsting, Drechsler, E.K.Ministerium, Eisen, Erst, Eugen, Falk, Ferdinand-Brücke, Ferdinandsbrucke, Ferdinandsohucke, Flatz, Fleischmaris, Francianen, Franck-Bonn, Frank, Fransens-Platz, Franzens-Platz, Freisinger-Gasse, Freiung, Friedrich, Ganzaga Gasse…

### runs/hunyuan/2026-09-16_tiles_p04_t1024 — tiled (5×4, rotations [0], 1024 px tiles, ≥192 px overlap, work 3788×4096 @ 0.489)

Source `p04.jpg` 7742×8372; crop 320,160,6880,7970; prompt “This is a fire insurance map of Victoria B.C. in 1895. Return the text…”; cap 4096 tok/tile. **20/20 tiles OCR'd, 954 tokens parsed, 356 overlap duplicates removed, 598 kept.**

| tile | box (work px) | ink | out tok | chars | tokens | cap hit |
|---|---|---|---|---|---|---|
| r0c0 | (157,78)–(1181,1102) | 0.030 | 903 | 1320 | 59 | no |
| r0c1 | (885,78)–(1909,1102) | 0.032 | 1775 | 2567 | 121 | no |
| r0c2 | (1614,78)–(2638,1102) | 0.040 | 1473 | 2175 | 98 | no |
| r0c3 | (2342,78)–(3366,1102) | 0.041 | 1550 | 2319 | 102 | no |
| r1c0 | (157,777)–(1181,1801) | 0.031 | 543 | 822 | 36 | no |
| r1c1 | (885,777)–(1909,1801) | 0.023 | 1044 | 1504 | 66 | no |
| r1c2 | (1614,777)–(2638,1801) | 0.027 | 1063 | 1505 | 72 | no |
| r1c3 | (2342,777)–(3366,1801) | 0.028 | 1222 | 1763 | 73 | no |
| r2c0 | (157,1476)–(1181,2500) | 0.029 | 4096 | 4528 | 25 | **yes** |
| r2c1 | (885,1476)–(1909,2500) | 0.032 | 971 | 1438 | 66 | no |
| r2c2 | (1614,1476)–(2638,2500) | 0.032 | 1127 | 1631 | 75 | no |
| r2c3 | (2342,1476)–(3366,2500) | 0.041 | 1187 | 1756 | 74 | no |
| r3c0 | (157,2176)–(1181,3200) | 0.006 | 33 | 59 | 2 | no |
| r3c1 | (885,2176)–(1909,3200) | 0.015 | 296 | 456 | 20 | no |
| r3c2 | (1614,2176)–(2638,3200) | 0.010 | 48 | 64 | 3 | no |
| r3c3 | (2342,2176)–(3366,3200) | 0.036 | 448 | 654 | 26 | no |
| r4c0 | (157,2875)–(1181,3899) | 0.011 | 111 | 168 | 7 | no |
| r4c1 | (885,2875)–(1909,3899) | 0.019 | 239 | 370 | 16 | no |
| r4c2 | (1614,2875)–(2638,3899) | 0.013 | 88 | 134 | 6 | no |
| r4c3 | (2342,2875)–(3366,3899) | 0.008 | 120 | 180 | 7 | no |

Alphabetic tokens kept (dedupe check by eye): 2 OFF, 2 Sal., 38't o eaves. 60't o ridge., 6"HUMBOLDT, a wall,, ACE, AGENCY, ALL SIDES, AMES,HOLDEN&, AND, ANWALK, BAKERY, BAST, BAST., BAY, BAY VIEW, Being, BLK, BLR 2°, BOARDING, BOAT, BOAT BUILDER, BOAT HO., BOAT SHED, BOOT&SHOE, BRICK, BRIDGE, BRITISH CO, BROUGHTON, CANDY FAC., CANOE, Carpe, CARRAGE SHOP, CHINESE, CLUB, CLUB HOUSE, COLOMBIA SOAP, CONSTM, Corp, COURTENAY, CURTENAY, DOUGLAS, DRUGS, DUNG, EDS, ELECTRIC, EXPRESS OFFICE, FAC., filled, FIREMISES TIDY, FLOATING, FLOATING PLATFORM, FLOOR, FOOT, FOOT WALK, FORGE, FOX, FROM 3/10/15/18/19, FROM 37/7, FURNACE, GLASS, GOVERNMENT, GRO., GROCERY, HEARSE, Heat. Hot air), HOTEL, House, HUMBOLDT, INDIAN, IRON CL., IRON CLAD, IRON LANDINGS, JAMES, JAPANESE, JULY 1895, KITCHEN, LANGLEY, Level, LIMITED…

### runs/hunyuan/2026-09-16_tiles_p05_t1024 — tiled (5×4, rotations [0], 1024 px tiles, ≥192 px overlap, work 3788×4096 @ 0.489)

Source `p05.jpg` 7742×8372; crop 320,160,6880,7970; prompt “This is a fire insurance map of Victoria B.C. in 1895. Return the text…”; cap 4096 tok/tile. **20/20 tiles OCR'd, 1088 tokens parsed, 445 overlap duplicates removed, 643 kept.**

| tile | box (work px) | ink | out tok | chars | tokens | cap hit |
|---|---|---|---|---|---|---|
| r0c0 | (157,78)–(1181,1102) | 0.038 | 766 | 1098 | 53 | no |
| r0c1 | (885,78)–(1909,1102) | 0.045 | 959 | 1397 | 61 | no |
| r0c2 | (1614,78)–(2638,1102) | 0.046 | 795 | 1152 | 54 | no |
| r0c3 | (2342,78)–(3366,1102) | 0.035 | 1025 | 1487 | 71 | no |
| r1c0 | (157,777)–(1181,1801) | 0.032 | 627 | 901 | 43 | no |
| r1c1 | (885,777)–(1909,1801) | 0.031 | 1125 | 1629 | 77 | no |
| r1c2 | (1614,777)–(2638,1801) | 0.036 | 829 | 1192 | 58 | no |
| r1c3 | (2342,777)–(3366,1801) | 0.025 | 610 | 865 | 42 | no |
| r2c0 | (157,1476)–(1181,2500) | 0.057 | 905 | 1317 | 62 | no |
| r2c1 | (885,1476)–(1909,2500) | 0.039 | 865 | 1224 | 60 | no |
| r2c2 | (1614,1476)–(2638,2500) | 0.026 | 641 | 912 | 44 | no |
| r2c3 | (2342,1476)–(3366,2500) | 0.024 | 251 | 365 | 16 | no |
| r3c0 | (157,2176)–(1181,3200) | 0.095 | 1399 | 2031 | 91 | no |
| r3c1 | (885,2176)–(1909,3200) | 0.046 | 1254 | 1797 | 88 | no |
| r3c2 | (1614,2176)–(2638,3200) | 0.027 | 841 | 1218 | 58 | no |
| r3c3 | (2342,2176)–(3366,3200) | 0.032 | 521 | 768 | 35 | no |
| r4c0 | (157,2875)–(1181,3899) | 0.047 | 287 | 429 | 18 | no |
| r4c1 | (885,2875)–(1909,3899) | 0.037 | 495 | 741 | 32 | no |
| r4c2 | (1614,2875)–(2638,3899) | 0.048 | 1157 | 1697 | 78 | no |
| r4c3 | (2342,2875)–(3366,3899) | 0.043 | 687 | 987 | 47 | no |

Alphabetic tokens kept (dedupe check by eye): "ROCCABELLA", 2 Gru, 2 Tenements, 35' to ridge, ASE, AST., AVE., BAST, BK.BAST, BLANCHARD, BLOCK 50, Boarding Ho., BRICK, BURDETT, BURDETT AVE., Cabins, Carp 2, carp 2', CATHEDRAL, CHINESE, CHURCH, CHURCH - WA, COLLINSON, CUTTER, Drying, ECLURE, EPISCOPAL, FOUNDATIONS, Furniture, Gro, Gru., HOME, HOTEL, HOWE BOLOT, HUMB LOT, HUMBOLDT, James Bay, KANE, LANE, LAUNDRY, LUMBER, M.C CLURE, MAY-1891, McCLURE, MTS CLURE, NOT, NOT USED, NOT YET OPENED), NUMBER, OFF., OLD, ORPHAN, OUGLAS, OUT, OUT HO, OUTSIDE, PASSAGE, PATRONE, PENWELL, PIAE, PLASTERED, PROTESTANT, RAE, REFORMED EPISCOPAL, SCALE 50 FT = 1INCH, SCHOOL, SEE, SEE SHEET, SEE SHEET NO 8, SHED, SHEET, Staple, STONE, STORAGE, STREET, SUNDAY, Tei, Tenements 2, Terremerits, To eaves…

### runs/hunyuan/2026-09-16_tiles_p06_t1024 — tiled (5×4, rotations [0], 1024 px tiles, ≥192 px overlap, work 3788×4096 @ 0.489)

Source `p06.jpg` 7742×8372; crop 320,160,6880,7970; prompt “This is a fire insurance map of Victoria B.C. in 1895. Return the text…”; cap 4096 tok/tile. **19/20 tiles OCR'd, 1399 tokens parsed, 417 overlap duplicates removed, 982 kept.**

| tile | box (work px) | ink | out tok | chars | tokens | cap hit |
|---|---|---|---|---|---|---|
| r0c0 | (157,78)–(1181,1102) | 0.017 | 615 | 921 | 41 | no |
| r0c1 | (885,78)–(1909,1102) | 0.019 | 4096 | 6178 | 148 | **yes** |
| r0c2 | (1614,78)–(2638,1102) | 0.040 | 2813 | 4114 | 168 | no |
| r0c3 | (2342,78)–(3366,1102) | 0.031 | 4096 | 5810 | 39 | **yes** |
| r1c0 | (157,777)–(1181,1801) | 0.010 | 17 | 24 | 1 | no |
| r1c1 | (885,777)–(1909,1801) | 0.022 | 1506 | 2255 | 101 | no |
| r1c2 | (1614,777)–(2638,1801) | 0.037 | 4096 | 6313 | 153 | **yes** |
| r1c3 | (2342,777)–(3366,1801) | 0.036 | 4096 | 5904 | 114 | **yes** |
| r2c0 | (157,1476)–(1181,2500) | 0.010 | 35 | 51 | 2 | no |
| r2c1 | (885,1476)–(1909,2500) | 0.023 | 770 | 1177 | 51 | no |
| r2c2 | (1614,1476)–(2638,2500) | 0.043 | 4096 | 5786 | 26 | **yes** |
| r2c3 | (2342,1476)–(3366,2500) | 0.046 | 1783 | 2640 | 119 | no |
| r3c0 | (157,2176)–(1181,3200) | 0.010 | 38 | 56 | 2 | no |
| r3c1 | (885,2176)–(1909,3200) | 0.032 | 645 | 982 | 41 | no |
| r3c2 | (1614,2176)–(2638,3200) | 0.050 | 1451 | 2184 | 91 | no |
| r3c3 | (2342,2176)–(3366,3200) | 0.049 | 1585 | 2350 | 105 | no |
| r4c0 | (157,2875)–(1181,3899) | 0.004 | — | — | — | skipped_blank |
| r4c1 | (885,2875)–(1909,3899) | 0.024 | 409 | 626 | 24 | no |
| r4c2 | (1614,2875)–(2638,3899) | 0.038 | 1240 | 1830 | 81 | no |
| r4c3 | (2342,2875)–(3366,3899) | 0.035 | 1371 | 1956 | 92 | no |

Alphabetic tokens kept (dedupe check by eye): & Clo., & SALTING, & TIN W., & Whse, 2 HAYWHSE, 2 Storeho., 2ND HAND, 3 & BAST, 4 & BASE, ALL, ALLEY, AMERICAN, APPRASERS, AUCTION, AUGITION, BAKERY, BAR, Barrel, BARRELS X STAVES, BASTION, BASTION SQUARE, BAY, BEETON, BEST, BLD, BLOCK, BLOCK 107, BLOCK 15½, BLOCK 16½, BONDED WHSE, BOUR, BRICK, BROUGHTON, BURNES, C. Morley, CAL, CANADIAN, CANADIAN PACIFIC NAVIGATION C°, CARE, CCADENTAL, CHANCERY LANE, CIGARS, CIO. Prr 2nd, CISTER, CLOTHING), CLOTHLINED, COAL, Coal Shed, COLONIAL HOTEL, COMMERCIAL, Cooper, COPPER, CURING, CUSTOM, CUSTOM HO., CUSTOMS, CUSTOMS WHSE., DIM, Dining, DINING, DRIVEWAY, DRUGS, EAST, Electric Tramway, Ethridge & Mann 2", Eve, EXC, EXCISE, FAC., Fancy Goods, FIRING, Floors supported, Flour & C., FORT, FREIGHT, FREIGHT SHED, FRUIT, FRUITS& PRODUCE, Fruits&Produce, Fuel: Sawdust…

### runs/hunyuan/2026-09-16_tiles_p07_t1024 — tiled (5×4, rotations [0], 1024 px tiles, ≥192 px overlap, work 3788×4096 @ 0.489)

Source `p07.jpg` 7742×8372; crop 320,160,6880,7970; prompt “This is a fire insurance map of Victoria B.C. in 1895. Return the text…”; cap 4096 tok/tile. **20/20 tiles OCR'd, 2347 tokens parsed, 631 overlap duplicates removed, 1716 kept.**

| tile | box (work px) | ink | out tok | chars | tokens | cap hit |
|---|---|---|---|---|---|---|
| r0c0 | (157,78)–(1181,1102) | 0.053 | 3343 | 4950 | 229 | no |
| r0c1 | (885,78)–(1909,1102) | 0.050 | 4096 | 5819 | 86 | **yes** |
| r0c2 | (1614,78)–(2638,1102) | 0.051 | 4096 | 5889 | 86 | **yes** |
| r0c3 | (2342,78)–(3366,1102) | 0.050 | 2474 | 3573 | 167 | no |
| r1c0 | (157,777)–(1181,1801) | 0.047 | 4096 | 4822 | 3 | **yes** |
| r1c1 | (885,777)–(1909,1801) | 0.058 | 3271 | 4765 | 216 | no |
| r1c2 | (1614,777)–(2638,1801) | 0.054 | 4096 | 5985 | 169 | **yes** |
| r1c3 | (2342,777)–(3366,1801) | 0.060 | 4096 | 5873 | 95 | **yes** |
| r2c0 | (157,1476)–(1181,2500) | 0.076 | 4096 | 6606 | 130 | **yes** |
| r2c1 | (885,1476)–(1909,2500) | 0.108 | 3987 | 5818 | 231 | no |
| r2c2 | (1614,1476)–(2638,2500) | 0.076 | 4096 | 5427 | 23 | **yes** |
| r2c3 | (2342,1476)–(3366,2500) | 0.067 | 4096 | 5322 | 11 | **yes** |
| r3c0 | (157,2176)–(1181,3200) | 0.053 | 2145 | 3189 | 141 | no |
| r3c1 | (885,2176)–(1909,3200) | 0.099 | 4096 | 5774 | 123 | **yes** |
| r3c2 | (1614,2176)–(2638,3200) | 0.083 | 4096 | 3509 | 1 | **yes** |
| r3c3 | (2342,2176)–(3366,3200) | 0.066 | 2079 | 3113 | 125 | no |
| r4c0 | (157,2875)–(1181,3899) | 0.045 | 1496 | 2164 | 101 | no |
| r4c1 | (885,2875)–(1909,3899) | 0.086 | 4096 | 6324 | 81 | **yes** |
| r4c2 | (1614,2875)–(2638,3899) | 0.087 | 3818 | 5525 | 196 | no |
| r4c3 | (2342,2875)–(3366,3899) | 0.057 | 1936 | 2760 | 133 | no |

Alphabetic tokens kept (dedupe check by eye): 1acover), 2.B.RAST, 28&Basb., 2D OVER, 3&Basb., 453)-VICTORIA B.C, 6th thick - BK Walls 20 "above - Interior Walls, AMFIRE, ANDERSON, ANGER, ANUFY, ARCADE, ATTACHES, attachments inside theatre - 111 parcillons, AUCTION, B.C.BLOCK, B.K.WALL 14, BAB, BAKE, BAKE HRS, BAKERY, BAKES, BANCA, BANK OF, BAR, BAR & BILLIARS, BARBER BATHS, BARS, BAS:2.3, BASI, BASTION, BATCH 18, BATHS, BDGE, BEEHIVE, BELMONTBLOCH, BHA. 1st, Bindery, Ble, BLK., BLOCK, BLOOD, Boarding, BOARDING, BOGE, Book Bindery, BOTH, BOTTLES, BRICK 18, BRICK 1ST, BRICK TO, BRITISH COLUMBIA, BROAD, BROUGHTON, BRunsmoke, BULARY, CABINS, CALE 50 FT = 1 INCH, CAN.PAC., Carifee, CARR, Carriage, CHANCERY LANE, CIGAR, CLAD, Clo., CLOD, COFFEE, COLONIST, Courage, CROCHERY, cup, DELL, DELUGE, DINING, Dining Room, DOANE BLK, DOANE BUILDINGS, Douglas, DOUGLAS…

### runs/hunyuan/2026-09-16_tiles_p08_t1024 — tiled (5×4, rotations [0], 1024 px tiles, ≥192 px overlap, work 3788×4096 @ 0.489)

Source `p08.jpg` 7742×8372; crop 320,160,6880,7970; prompt “This is a fire insurance map of Victoria B.C. in 1895. Return the text…”; cap 4096 tok/tile. **20/20 tiles OCR'd, 1996 tokens parsed, 696 overlap duplicates removed, 1300 kept.**

| tile | box (work px) | ink | out tok | chars | tokens | cap hit |
|---|---|---|---|---|---|---|
| r0c0 | (157,78)–(1181,1102) | 0.062 | 2291 | 3391 | 152 | no |
| r0c1 | (885,78)–(1909,1102) | 0.020 | 1721 | 2545 | 117 | no |
| r0c2 | (1614,78)–(2638,1102) | 0.020 | 1066 | 1574 | 71 | no |
| r0c3 | (2342,78)–(3366,1102) | 0.028 | 1225 | 1803 | 73 | no |
| r1c0 | (157,777)–(1181,1801) | 0.043 | 2244 | 3288 | 130 | no |
| r1c1 | (885,777)–(1909,1801) | 0.035 | 1523 | 2260 | 102 | no |
| r1c2 | (1614,777)–(2638,1801) | 0.023 | 1218 | 1811 | 82 | no |
| r1c3 | (2342,777)–(3366,1801) | 0.015 | 1614 | 2340 | 104 | no |
| r2c0 | (157,1476)–(1181,2500) | 0.048 | 2092 | 3009 | 131 | no |
| r2c1 | (885,1476)–(1909,2500) | 0.031 | 983 | 1443 | 65 | no |
| r2c2 | (1614,1476)–(2638,2500) | 0.031 | 1441 | 2099 | 98 | no |
| r2c3 | (2342,1476)–(3366,2500) | 0.025 | 1809 | 2585 | 117 | no |
| r3c0 | (157,2176)–(1181,3200) | 0.053 | 4096 | 6185 | 14 | **yes** |
| r3c1 | (885,2176)–(1909,3200) | 0.045 | 1476 | 2168 | 90 | no |
| r3c2 | (1614,2176)–(2638,3200) | 0.031 | 1808 | 2653 | 120 | no |
| r3c3 | (2342,2176)–(3366,3200) | 0.038 | 1802 | 2611 | 120 | no |
| r4c0 | (157,2875)–(1181,3899) | 0.053 | 1911 | 2751 | 128 | no |
| r4c1 | (885,2875)–(1909,3899) | 0.058 | 1569 | 2312 | 96 | no |
| r4c2 | (1614,2875)–(2638,3899) | 0.045 | 1605 | 2317 | 105 | no |
| r4c3 | (2342,2875)–(3366,3899) | 0.032 | 1197 | 1727 | 81 | no |

Alphabetic tokens kept (dedupe check by eye): 10 OVER, 23' TO EAVES, 2nd Hand, 30' TO EAVES, 35' TO RIDGE, 38' TO EAVES, 38' TO RIDGE, 4"BN=2OVER, 4"BROOVER, 40SPINE, 75 TO EAVES, 75'TO RIDGE, 8 DRYING, A&Bust, A.O.U.W.HALLS, ALCONER, ALL, ARCHBISHOPS, AUCTION, B'SMA & MACHINE, BAKE, BAKERY, BALMORAL HOTEL, BANCHARD, BAR, Bar &, BC.STEAM DYE WHS., BELFAV, BETTLE, BLANCHARD, BLANKHARD, ble, BRICK, BRICK & STONE, BRICK ST, BRIDGE, BRIGH WALL T.&2., BRUSH, BSH, CABIN, CABINS, CARDB, CARP, CARP., CARRAGE, CARRIAGA SHOP, Carriage, CARRIAGE SHED, CARRIAGES, CATHEDRAL, CATHOLIC, CENTER, CHINESE, CHURCH, CIGAR, CIST", CONVENT, DAYANG, Dining, Dining', DOMINION, DOUBAS, DOUGAS, Douglas, DOUGLAS, DRUGS, DRYING, DRYING ROOM, DWG, Dye Wks., EAVES, ELECTRIC, ENGRAV, ENGRAVER, EXCHANGE, FAG., FAQ., FEST, FORT, FRAME OVER…

### runs/hunyuan/2026-09-16_tiles_p09_t1024 — tiled (5×4, rotations [0], 1024 px tiles, ≥192 px overlap, work 3788×4096 @ 0.489)

Source `p09.jpg` 7742×8372; crop 320,160,6880,7970; prompt “This is a fire insurance map of Victoria B.C. in 1895. Return the text…”; cap 4096 tok/tile. **20/20 tiles OCR'd, 1357 tokens parsed, 525 overlap duplicates removed, 832 kept.**

| tile | box (work px) | ink | out tok | chars | tokens | cap hit |
|---|---|---|---|---|---|---|
| r0c0 | (157,78)–(1181,1102) | 0.035 | 4096 | 5868 | 24 | **yes** |
| r0c1 | (885,78)–(1909,1102) | 0.019 | 1005 | 1468 | 65 | no |
| r0c2 | (1614,78)–(2638,1102) | 0.018 | 926 | 1356 | 61 | no |
| r0c3 | (2342,78)–(3366,1102) | 0.023 | 449 | 646 | 30 | no |
| r1c0 | (157,777)–(1181,1801) | 0.030 | 1469 | 2165 | 102 | no |
| r1c1 | (885,777)–(1909,1801) | 0.019 | 956 | 1368 | 67 | no |
| r1c2 | (1614,777)–(2638,1801) | 0.016 | 733 | 1060 | 52 | no |
| r1c3 | (2342,777)–(3366,1801) | 0.025 | 737 | 1080 | 51 | no |
| r2c0 | (157,1476)–(1181,2500) | 0.031 | 1462 | 2093 | 93 | no |
| r2c1 | (885,1476)–(1909,2500) | 0.026 | 1774 | 2565 | 111 | no |
| r2c2 | (1614,1476)–(2638,2500) | 0.024 | 866 | 1234 | 61 | no |
| r2c3 | (2342,1476)–(3366,2500) | 0.040 | 413 | 618 | 28 | no |
| r3c0 | (157,2176)–(1181,3200) | 0.037 | 1642 | 2387 | 110 | no |
| r3c1 | (885,2176)–(1909,3200) | 0.033 | 1895 | 2718 | 121 | no |
| r3c2 | (1614,2176)–(2638,3200) | 0.025 | 1218 | 1733 | 77 | no |
| r3c3 | (2342,2176)–(3366,3200) | 0.036 | 672 | 976 | 45 | no |
| r4c0 | (157,2875)–(1181,3899) | 0.044 | 1214 | 1779 | 80 | no |
| r4c1 | (885,2875)–(1909,3899) | 0.029 | 1220 | 1776 | 77 | no |
| r4c2 | (1614,2875)–(2638,3899) | 0.025 | 862 | 1254 | 51 | no |
| r4c3 | (2342,2875)–(3366,3899) | 0.027 | 734 | 1058 | 51 | no |

Alphabetic tokens kept (dedupe check by eye): 16' TO EAVES, 2 OPEN, CARPAGE, CASIN, CHINESE, CIGAR, Coal, COOLER, Drying, DRYING, ELECTRIC, ELECTRICAL, EMBY, END, FAC., FLORIST, FLOUR, FONT, FORT, GRO., HETTLER, HIGH, JOHNSON, JULY, JURORA, KANE, LAUNDRY, LEVEL, MAY, 1891., MEARES, MKARES, NONER, NOT, OPEN, OPEN AT, Orchard, ORY, PLATFORM, Platform, PUMPIA, PUMPING, PUMPING ST, QUADRA, RIMES, SCALE 50 FT = 1INCH, SEE, SEE SHEET, SEE SHEET NO 13, SHEET, Slope, STORAGE, TRAMWAY, VACANT, VANCOUVER, VENNA, VICTORIA ASSEMBLY ROOMS, VICTORIA, B.C., VIEW, WASHOP, YATES

### runs/hunyuan/2026-09-16_tiles_p10_t1024 — tiled (5×4, rotations [0], 1024 px tiles, ≥192 px overlap, work 3788×4096 @ 0.489)

Source `p10.jpg` 7742×8372; crop 320,160,6880,7970; prompt “This is a fire insurance map of Victoria B.C. in 1895. Return the text…”; cap 4096 tok/tile. **20/20 tiles OCR'd, 1978 tokens parsed, 673 overlap duplicates removed, 1305 kept.**

| tile | box (work px) | ink | out tok | chars | tokens | cap hit |
|---|---|---|---|---|---|---|
| r0c0 | (157,78)–(1181,1102) | 0.016 | 291 | 441 | 15 | no |
| r0c1 | (885,78)–(1909,1102) | 0.009 | 691 | 1027 | 46 | no |
| r0c2 | (1614,78)–(2638,1102) | 0.011 | 1428 | 2111 | 87 | no |
| r0c3 | (2342,78)–(3366,1102) | 0.015 | 1457 | 2165 | 97 | no |
| r1c0 | (157,777)–(1181,1801) | 0.033 | 816 | 1213 | 44 | no |
| r1c1 | (885,777)–(1909,1801) | 0.012 | 1312 | 1930 | 89 | no |
| r1c2 | (1614,777)–(2638,1801) | 0.019 | 2672 | 3895 | 140 | no |
| r1c3 | (2342,777)–(3366,1801) | 0.019 | 1737 | 2522 | 114 | no |
| r2c0 | (157,1476)–(1181,2500) | 0.047 | 1298 | 1928 | 84 | no |
| r2c1 | (885,1476)–(1909,2500) | 0.018 | 2009 | 2929 | 136 | no |
| r2c2 | (1614,1476)–(2638,2500) | 0.036 | 2294 | 3348 | 149 | no |
| r2c3 | (2342,1476)–(3366,2500) | 0.063 | 3471 | 5011 | 212 | no |
| r3c0 | (157,2176)–(1181,3200) | 0.089 | 1906 | 2898 | 122 | no |
| r3c1 | (885,2176)–(1909,3200) | 0.051 | 2598 | 3838 | 170 | no |
| r3c2 | (1614,2176)–(2638,3200) | 0.089 | 4096 | 5805 | 53 | **yes** |
| r3c3 | (2342,2176)–(3366,3200) | 0.107 | 4096 | 4871 | 6 | **yes** |
| r4c0 | (157,2875)–(1181,3899) | 0.050 | 833 | 1274 | 52 | no |
| r4c1 | (885,2875)–(1909,3899) | 0.042 | 1828 | 2706 | 122 | no |
| r4c2 | (1614,2875)–(2638,3899) | 0.072 | 2772 | 4087 | 162 | no |
| r4c3 | (2342,2875)–(3366,3899) | 0.074 | 4096 | 6286 | 78 | **yes** |

Alphabetic tokens kept (dedupe check by eye): "C"PAINT, & ICE FAC., &BAST, &ME KITRICK, 1 DWG, 100' Hase, 15'TO EAVES, 2 & BAST, 2 & BAST., 2 SAL., 2& BAST, 2&BAST., 20 TO EAVES, 22'70 EAVES, 33' RIDGE, 35&BAST, 38&BAST, AIV, ALBION, ALL, ALL TOT, AND CO., ARMORANT, ASTRICO BLK, B.C. COLDSTORAGE, B.C. WHSE. & OLD, B.SM.&WAGON, BAR, BEYOND, BILLOS, BOILER FAC., BOILER HSE, BOLLER, BRICK, BRICK FUNACE, BRIDGE, CABINS, CAINESE, CANADA, CAP.7 TONS A DAY, CAREY BLOCK, CASES, CHATHAM, Chine, CHINE, CHINESE, CHINESE AND, CHINESE OCCUPANC, CHINESE THEATRE, CHINESE WASH HSE, CHURCH, CIGAR, CITY, CLAD, COAL, COAL & HAY, COAL SHED, COLOR, COOKING, COOLED, COOPERA, COORDWOOD PILED INR AROUND SHED, COPPER, COR. IRON CLAD), CORON, COVE WITH SHINGLE, CUPAN, DEPOT, DINING, Dmg, DOCK, DRAG, DREGOR, KNIGHT, Drive, DRIVEWAY, DRIVEWORM, DRUG, DRYING, DUNSMUIR'S, DWGS & OFF'S…

### runs/hunyuan/p06b_rot_coords_run

Prompts used: “This is a fire insurance map of Victoria B.C. in 1895. It has been rot…”

| stem | fed size | in tok | out tok | content bytes | overlays | verdict |
|---|---|---|---|---|---|---|
| fireinsurance_victoria_1895_p06b_rot000 | 969×1048 | 1105 | 16384 | 17706 | 0 | runaway/cap |
| fireinsurance_victoria_1895_p06b_rot090 | 1048×969 | 1102 | 914 | 1337 | 0 | collapsed |
| fireinsurance_victoria_1895_p06b_rot105 | 1048×1001 | 1136 | 16384 | 24537 | 0 | runaway/cap |
| fireinsurance_victoria_1895_p06b_rot112 | 1048×1013 | 1170 | 12631 | 19725 | 0 | ok |

### runs/hunyuan/single_page

Prompts used: “This is a fire insurance map of Victoria B.C. in 1895. It has been rot…”; “This is a fire insurance map of Victoria B.C. in 1895. Return the text…”; “This is a fire insurance map of Victoria B.C. in 1895. Return the text…”; “This is a fire insurance map of Victoria B.C. in 1895. Return the word…”; “检测并识别图片中的文字，将文本坐标格式化输出。”

| stem | fed size | in tok | out tok | content bytes | overlays | verdict |
|---|---|---|---|---|---|---|
| fireinsurance_victoria_1895_p02_rot000 | 970×1048 | 1071 | 16384 | 24037 | 0 | runaway/cap |
| fireinsurance_victoria_1895_p02_rot019 | 1009×1048 | 1137 | 2982 | 4436 | 0 | ok |
| fireinsurance_victoria_1895_p02_rot050 | 1048×1040 | 1136 | 1003 | 1436 | 0 | collapsed |
| fireinsurance_victoria_1895_p02_rot085 | 1048×982 | 1102 | 1171 | 1760 | 0 | collapsed |
| fireinsurance_victoria_1895_p02_rot096 | 1048×984 | 1102 | 622 | 925 | 0 | collapsed |
| fireinsurance_victoria_1895_p02_rot114 | 1048×1017 | 1136 | 16384 | 21833 | 0 | runaway/cap |
| fireinsurance_victoria_1895_p02_rot126 | 1048×1035 | 1136 | 422 | 536 | 0 | collapsed |
| fireinsurance_victoria_1895_p02_rot127 | 1048×1036 | 1136 | 1404 | 2003 | 0 | collapsed |
| fireinsurance_victoria_1895_p06_rot090 | 1048×969 | 1068 | 1528 | 2098 | 0 | collapsed |
| fireinsurance_victoria_1895_p06_rot105 | 1048×1001 | 1102 | 1219 | 1807 | 0 | collapsed |
| fireinsurance_victoria_1895_p06_rot112 | 1048×1013 | 1136 | 15921 | 23926 | 0 | ok |
| fireinsurance_victoria_1895_p06_rot180 | 969×1048 | 1071 | 16384 | 22921 | 0 | runaway/cap |
| fireinsurance_victoria_1895_p06_rot200 | 1010×1048 | 1137 | 5485 | 8269 | 0 | ok |
| fireinsurance_victoria_1895_p06_rot270 | 1048×969 | 1068 | 1580 | 2251 | 0 | collapsed |
| fireinsurance_victoria_1895_p06_rot359 | 971×1048 | 1071 | 16384 | 25049 | 0 | runaway/cap |
| fireinsurance_victoria_1895_p06b_rot000_cropped | 1262×1536 | 1949 | 16384 | 24522 | 1 | runaway/cap |
| fireinsurance_victoria_1895_p06b_rot000 | 1420×1536 | 2194 | 2 | 1 | 0 | collapsed |
| fireinsurance_victoria_1895_p06b_rot090 | 2048×1893 | 3864 | 16384 | 23512 | 1 | runaway/cap |
| fireinsurance_victoria_1895_p06b_rot105 | 2048×1957 | 3994 | 16384 | 24141 | 1 | runaway/cap |
| fireinsurance_victoria_1895_p06b_rot112_filtered | 1024×990 | 1052 | 2690 | 392 | 0 | collapsed |
| fireinsurance_victoria_1895_p06b_rot112 | 1024×990 | 1052 | 2690 | 4065 | 1 | ok |
| fireinsurance_victoria_1895_p06b_rot180 | 969×1048 | 1071 | 257 | 406 | 0 | collapsed |
| fireinsurance_victoria_1895_p25_rot000 | 1422×1536 | 2180 | 16384 | 2368 | 1 | collapsed |
| fireinsurance_victoria_1895_p25_rot087 | 2048×1910 | 3948 | 8 | 13 | 0 | collapsed |
| fireinsurance_victoria_1895_p25_rot356 | 1915×2048 | 3952 | 16384 | 25138 | 0 | runaway/cap |
| fireinsurance_victoria_1895_p25_rot358 | 1906×2048 | 3952 | 16384 | 23313 | 0 | runaway/cap |

### Rotation sensitivity (single-image runs)

Same sheet, HunyuanOCR at different page rotations; content bytes ≈ how much of the page was read.

| sheet | rotation → content bytes |
|---|---|
| p02 | 0°: 24,037, 19°: 4,436, 50°: 1,436, 85°: 1,760, 96°: 925, 114°: 21,833, 126°: 536, 127°: 2,003 |
| p06 | 90°: 2,098, 105°: 1,807, 112°: 23,926, 180°: 22,921, 200°: 8,269, 270°: 2,251, 359°: 25,049 |
| p06b | 0°: 1, 0°: 17,706, 0°_cropped: 24,522, 90°: 1,337, 90°: 23,512, 105°: 24,141, 105°: 24,537, 112°: 392, 112°: 4,065, 112°: 19,725, 180°: 406 |
| p25 | 0°: 2,368, 87°: 13, 356°: 25,138, 358°: 23,313 |

## HunyuanOCR rotation probes (`scripts/fim_rotation_probe.py`)


### runs/hunyuan/2026-09-10_rotprobe_p06b_r1c1
Upright pass: 44 tokens inside the tile. Each other row: the same 1536px view rotated about its centre (PIL, CCW; corners filled from the neighbouring map), OCR'd with `text_coords`, boxes mapped back; a token counts as recovered if the same text lands within 30 px of its upright position.

| angle | canvas | s | tokens | upright tokens recovered | alphabetic recovered | not in upright | alphabetic extras |
|---|---|---|---|---|---|---|---|
| 0° | 1536×1536 | 9.9 | 44 | 44/44 (100%) | 3/3 | 0 |  |
| 30° | 1536×1536 | 8.8 | 39 | 25/44 (57%) | 1/3 | 7 | COMMERCIAL ST |
| 60° | 1536×1536 | 8.9 | 40 | 26/44 (59%) | 1/3 | 8 | BASTION SQUARE, WHARF |
| 90° | 1536×1536 | 8.9 | 41 | 34/44 (77%) | 3/3 | 7 | WHARF |
| 120° | 1536×1536 | 7.8 | 35 | 20/44 (46%) | 0/3 | 11 | BASTION S, COMMERCIAL ST, WHARF |
| 150° | 1536×1536 | 8.9 | 41 | 27/44 (61%) | 0/3 | 9 | BASTION SQUARE, COMMERCIA |
| 180° | 1536×1536 | 9.6 | 45 | 39/44 (89%) | 3/3 | 6 | A, A3, WHARF |
| 210° | 1536×1536 | 9.1 | 42 | 22/44 (50%) | 2/3 | 12 | BASTION S |
| 240° | 1536×1536 | 7.1 | 31 | 20/44 (46%) | 0/3 | 8 | BASTION SQUARE, COMMERCIA, WHARF |
| 270° | 1536×1536 | 9.5 | 44 | 36/44 (82%) | 3/3 | 8 | WHARF |
| 300° | 1536×1536 | 8.9 | 41 | 22/44 (50%) | 2/3 | 12 |  |
| 330° | 1536×1536 | 9.1 | 42 | 31/44 (70%) | 0/3 | 6 | BASTION SQUARE, COMMERCIA |

Alphabetic tokens found only when rotated (text → angles): A → [180], A3 → [180], BASTION S → [120, 210], BASTION SQUARE → [60, 150, 240, 330], COMMERCIA → [150, 240, 330], COMMERCIAL ST → [30, 120], WHARF → [60, 90, 120, 180, 240, 270]


## Surya text-line detection (`surya.detection`, no vLLM) — runs/surya/

Line polygons only (no text). Run under a surya ≥0.22 interpreter — the shared /opt/venvs/vllm build (0.20) returns flat heatmaps. See `scripts/fim_surya_detect.py`.

| run dir | source | tiles | detect s | polygons kept | horizontal / vertical / rotated | median box h×w (work px) |
|---|---|---|---|---|---|---|
| `2026-09-10_detect_p06b` | `p06b.jpg` | 9 | 7.52 | 213 | 148 / 57 / 8 | 27×33 |

## Surya OCR 2 (`datalab-to/surya-ocr-2` via local vLLM) — block-level layout + HTML

| run dir | image | blocks | labels | table rows | text chars | s |
|---|---|---|---|---|---|---|
| `2026-09-10_ocr2` | `fireinsurance_victoria_1885_Index_col1.jpg` | 62 | SectionHeader×9, Text×53 | 40 | 2,534 | 43.0 |
| `2026-09-10_ocr2` | `inside-front-cover-index-to-streets-col1.jpg` | 12 | SectionHeader×6, TableOfContents×6 | 69 | 2,203 | 10.2 |
| `2026-09-10_ocr2` | `p06b.jpg` | 12 | Figure×2, PageHeader×4, Picture×3, Text×3 | 0 | 54 | 33.8 |
| `2026-09-10_ocr2_fullpage` | `fireinsurance_victoria_1885_Index_col1.jpg` | 73 | SectionHeader×5, Text×68 | 0 | 2,300 | 36.6 |
| `2026-09-10_ocr2_fullpage` | `fireinsurance_victoria_1885_Index_col2.jpg` | 1 | Table×1 | 71 | 2,225 | 5.8 |
| `2026-09-10_ocr2_fullpage` | `inside-front-cover-block-numbers_col1.jpg` | 1 | Table×1 | 81 | 1,359 | 4.6 |
| `2026-09-10_ocr2_fullpage` | `inside-front-cover-block-numbers_col2.jpg` | 2 | Table×2 | 81 | 1,332 | 3.9 |
| `2026-09-10_ocr2_fullpage` | `inside-front-cover-block-numbers.jpg` | 5 | SectionHeader×3, Table×2 | 84 | 2,394 | 7.4 |
| `2026-09-10_ocr2_fullpage` | `inside-front-cover-index-to-streets-col1.jpg` | 12 | PageHeader×1, SectionHeader×5, TableOfContents×6 | 72 | 2,098 | 6.0 |
| `2026-09-10_ocr2_fullpage` | `inside-front-cover-index-to-streets-col2.jpg` | 17 | SectionHeader×8, Table×9 | 63 | 2,413 | 7.5 |
| `2026-09-10_ocr2_fullpage` | `inside-front-cover-index-to-streets-col3.jpg` | 16 | SectionHeader×8, TableOfContents×8 | 62 | 2,552 | 8.2 |
| `2026-09-10_ocr2_fullpage` | `inside-front-cover-index-to-streets.jpg` | 5 | PageHeader×1, SectionHeader×1, Table×3 | 216 | 6,728 | 49.0 |
| `2026-09-10_ocr2_fullpage` | `inside-front-cover-index.jpg` | 19 | Picture×2, SectionHeader×8, Table×5, Text×4 | 392 | 16,148 | 145.7 |
| `2026-09-10_ocr2_fullpage` | `inside-front-cover-specials-addendum.jpg` | 3 | SectionHeader×2, TableOfContents×1 | 32 | 898 | 4.1 |
| `2026-09-10_ocr2_fullpage` | `inside-front-cover-specials-col1.jpg` | 20 | SectionHeader×11, TableOfContents×9 | 54 | 2,317 | 7.6 |
| `2026-09-10_ocr2_fullpage` | `inside-front-cover-specials-col2.jpg` | 6 | TableOfContents×6 | 28 | 1,010 | 3.1 |
| `2026-09-10_ocr2_fullpage` | `inside-front-cover-specials.jpg` | 4 | SectionHeader×2, TableOfContents×2 | 140 | 4,472 | 13.6 |
| `2026-09-10_ocr2_fullpage` | `inside-front-cover.jpg` | 17 | Picture×3, SectionHeader×5, Table×4, Text×5 | 221 | 9,191 | 54.1 |
| `2026-09-10_ocr2_fullpage` | `inside-front-cover_top.jpg` | 12 | Picture×2, SectionHeader×2, Table×1, Text×7 | 7 | 1,476 | 7.2 |

## Chandra (`datalab-to/chandra`, hf method, custom prompts) — runs/chandra/

| run dir | date (UTC) | input | elapsed | prompt | output |
|---|---|---|---|---|---|
| `fireinsurance_victoria_1885_Index_col2` | — (no log; pre-`--prompt` CLI) | `fireinsurance_victoria_1885_Index_col2` | — | ? (1785 tokens) | `fireinsurance_victoria_1885_Index_col2.md` (6,123 chars) |
| `fireinsurance_victoria_1885_Index_col3` | — (no log; pre-`--prompt` CLI) | `fireinsurance_victoria_1885_Index_col3` | — | ? (1667 tokens) | `fireinsurance_victoria_1885_Index_col3.md` (4,275 chars) |
| `fireinsurance_victoria_1885_Index_col4` | — (no log; pre-`--prompt` CLI) | `fireinsurance_victoria_1885_Index_col4` | — | ? (946 tokens) | `fireinsurance_victoria_1885_Index_col4.md` (4,539 chars) |
| `fireinsurance_victoria_1885_Index_table` | 2026-03-12 19:33 | `fireinsurance_victoria_1885_Index.jpg` | 0:05:27 | This is a cropped scan of an Index from a Sanborn fire insurance map book from 1885. Export it as a table to m… | `fireinsurance_victoria_1885_Index/fireinsurance_victoria_1885_Index.md` (142,914 chars) |
| `fireinsurance_victoria_1885_Index_table` | 2026-03-12 19:40 | `` | — | This is a cropped scan of an Index from a Sanborn fire insurance map book from 1885. Export it as a table to m… | `fireinsurance_victoria_1885_Index/fireinsurance_victoria_1885_Index.md` (142,914 chars) |
| `fireinsurance_victoria_1885_Index_table_col1` | 2026-03-12 21:27 | `fireinsurance_victoria_1885_Index_col1.jpg` | 0:00:29 | This is a cropped scan of an Index from a Sanborn fire insurance map book from 1885. Export it as a table to m… | `fireinsurance_victoria_1885_Index_col1/fireinsurance_victoria_1885_Index_col1.md` (1,923 chars) |
| `fireinsurance_victoria_1885_Index_table_col1` | 2026-03-12 21:32 | `fireinsurance_victoria_1885_Index_col1.jpg` | — | This is a cropped scan of an Index from a Sanborn fire insurance map book from 1885. Export it as a table to m… | `fireinsurance_victoria_1885_Index_col1/fireinsurance_victoria_1885_Index_col1.md` (1,923 chars) |
| `fireinsurance_victoria_1885_Index_table_col1` | 2026-03-12 21:34 | `fireinsurance_victoria_1885_Index_col1.jpg` | 0:00:29 | This is a cropped scan of an Index from a Sanborn fire insurance map book from 1885. Export it as a table to m… | `fireinsurance_victoria_1885_Index_col1/fireinsurance_victoria_1885_Index_col1.md` (1,923 chars) |
| `fireinsurance_victoria_1885_Key` | — (no log; pre-`--prompt` CLI) | `fireinsurance_victoria_1885_Key` | — | ? (1074 tokens) | `fireinsurance_victoria_1885_Key.md` (2,683 chars) |
| `fireinsurance_victoria_1885_Key_description` | 2026-03-12 20:01 | `fireinsurance_victoria_1885_Key.jpg` | 0:00:28 | This is a cropped scan of an Key from a Sanborn fire insurance map book from 1885. Provide descriptions of eac… | `fireinsurance_victoria_1885_Key/fireinsurance_victoria_1885_Key.md` (2,157 chars) |
| `fireinsurance_victoria_1895_p01` | — (no log; pre-`--prompt` CLI) | `fireinsurance_victoria_1895_p01` | — | ? (1255 tokens) | `fireinsurance_victoria_1895_p01.md` (4,355 chars) |
| `fireinsurance_victoria_1895_p06b_rot000` | 2026-03-11 19:24 | `fireinsurance_victoria_1895_p06b_rot000.png` | 0:00:18 | This is a scan of a fire insurance map from 1895. Extract images for the north arrow, color control patch, sca… | `fireinsurance_victoria_1895_p06b_rot000.md` (1,808 chars) |
| `fireinsurance_victoria_1895_p06b_rot000` | 2026-03-11 19:25 | `fireinsurance_victoria_1895_p06b_rot000.png` | 0:00:15 | This is a scan of a fire insurance map from 1895. Extract pngs of the sections containing the north arrow, col… | `fireinsurance_victoria_1895_p06b_rot000.md` (1,808 chars) |
| `fireinsurance_victoria_1895_p06b_rot000` | 2026-03-11 19:40 | `fireinsurance_victoria_1895_p06b_rot000.png` | 0:00:13 | This is a scan of a fire insurance map from 1895. Provide the coordinates on the image for the following eleme… | `fireinsurance_victoria_1895_p06b_rot000.md` (1,808 chars) |
| `fireinsurance_victoria_1895_p06b_rot000` (nested `fireinsurance_victoria_1895_p06b_rot000/output`) | 2026-03-12 00:15 | `fireinsurance_victoria_1895_p06b_rot000.png` | 0:00:31 | This is a scan of a fire insurance map from 1895. Provide me with a list of cartographic and digitization feat… | `fireinsurance_victoria_1895_p06b_rot000.md` (1,808 chars) |
| `fireinsurance_victoria_1895_p25_rot000` | — (no log; pre-`--prompt` CLI) | `fireinsurance_victoria_1895_p25_rot000` | — | ? (12384 tokens) | `fireinsurance_victoria_1895_p25_rot000.md` (14,933 chars) |

### Notes

- `fireinsurance_victoria_1885_Index_table_col1` was run three times with progressively more explicit column definitions; only the last output survives (the CLI overwrites).
- `fireinsurance_victoria_1895_p06b_rot000` (Chandra) has nested output dirs from Chandra being pointed at its own output folder; the useful transcript is the top-level `.md`.
- `fireinsurance_victoria_1895_p25_rot000.md` (Chandra) degenerates into repeated `100' = N'` scale lines (runaway generation).
- Single-image HunyuanOCR runs of whole sheets either collapse or hit the cap; tiling (`fim_tile_ocr.py`) is the fix — see the tiled sections above.
- `single_page/overlays/` counts only overlays drawn with the current norm1000 tool (2026-09-10 on). Older ones normalised x by the max emitted coordinate (or 1500) and sit ~20% too far right; they are in `overlays/stale_old_tool/` (README there) and are not counted.
- `p06b_rot112` (1024×990, 2690 tok) is `ok` only in the sense that it terminated: 175 of its 190 elements are ruler-tick counting runs (1–20, 1–46, 15–123, the last wrapping past y=1000). `scripts/fim_tickfilter.py` strips them; 15 real labels remain.
