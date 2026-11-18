-- Data: ForeverDB.net (https://foreverdb.net), build 1.60.1.70862. Reuse requires this credit: see NOTICE.txt (GPL-3.0 section 7(b)).
-- Copyright (C) 2026 ForeverDB.net. GPL-3.0 with section 7(b) attribution term.
-- Selected observed fixed-level and location corrections from ForeverDB 0.57.16.
-- Additional level rows: ForeverDB 0.58.2, build 1.60.1.70888, snapshot 2026-11-12.cc0c2a5c.
-- Additional level row: ForeverDB 0.64.1, build 1.60.1.70938, snapshot 2026-11-18.17caad86.
-- See FOREVERDB_LICENSE.txt and ForeverDBAudit.md. No runtime ForeverDB dependency.
local _, ns = ...
ns.questFieldOverrides = {
    [472] = {questLevel = {was = 25, value = 30}}, -- Fall of Dun Modr; 2 observers.
    [556] = {questLevel = {was = 32, value = 33}}, -- Stone Tokens; 2 observers.
    [1484] = {questLevel = {was = 35, value = 33}}, -- The Corrupter; 3 observers (0.64.1).
    [79363] = {questLevel = {was = 27, value = 26}}, -- Silvia's Sword; 5 observers (0.58.2).
    [86757] = {questLevel = {was = 30, value = 32}}, -- Slowing the Orc Advance; 2 observers.
    [88756] = {questLevel = {was = 32, value = 31}}, -- Bring Back a Bang; 3 observers.
    [91723] = {questLevel = {was = 8, value = 10}}, -- Delicate Instruments; 6 observers.
    [91732] = {questLevel = {was = 7, value = 10}}, -- Good Steel; 6 observers.
    [91751] = {questLevel = {was = 8, value = 7}}, -- Rough Wolf Pelts; 2 observers.
    [96137] = {questLevel = {was = 25, value = 24}}, -- Ira's Dagger; 3 observers.
    [96138] = {questLevel = {was = 30, value = 28}}, -- Merrick's Bow; 2 observers.
    [96139] = {questLevel = {was = 23, value = 22}}, -- The Valor Family; 7 observers.
    [97253] = {questLevel = {was = 15, value = 14}}, -- Parts and Pieces; 13 observers.
    [98027] = {questLevel = {was = 26, value = 29}}, -- Gleaming Crescent Necklace; 2 observers.
    [98251] = {questLevel = {was = 23, value = 22}}, -- Never Coming Back; 2 observers (0.58.2).
    [98252] = {questLevel = {was = 23, value = 22}}, -- A Void Path; 2 observers (0.58.2).
    [98417] = {questLevel = {was = 28, value = 30}}, -- Vengeful Trail; 4 observers (0.58.2).
    [99048] = {questLevel = {was = 9, value = 11}}, -- A Missing Hand; 6 observers.
    [99080] = {questLevel = {was = 11, value = 9}}, -- Drive Them Out; 2 observers.
}
-- Player-observed location, corroborated by the Field to Clear quest report.
-- Used only while QuestieDB has no spawn coordinates for this NPC.
ns.npcLocationFallbacks = {
    [14242] = {map = 1413, x = 48.0, y = 77.5}, -- Sulhasa, southern Barrens.
}
