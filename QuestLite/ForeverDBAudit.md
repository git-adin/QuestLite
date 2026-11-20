# ForeverDB comparison and corrections — QuestLite 0.4.2

## Refresh 2026-11-19 / 0.4.22

Compared installed ForeverDB 0.67.0, snapshot 2026-11-19.da52610c / build
1.60.1.70959, against QuestieDB 1.1.3. Counts: 5982 provider quests, 3544 Classic
rows, 2824 observed/client rows, 4514 guides, 1110 NPC spots, 2786 quest-location
records and 22 POI entries. Existing eleven-field records still parse.

Report: eight missing IDs, 52 sequence candidates, 68 giver differences, 22 level
differences, ten NPC-location candidates and 164 Classic prerequisite-expression
differences. Thirteen fixed-level differences are already resolved by guarded
corrections. No additional fixed-level correction is justified. Unknown/scaling
levels and five minimum-level differences remain unmodified. Completion sightings
do not establish pickup thresholds; previous-quest observations do not establish
mandatory gates. All eight missing quests are unplaced PvP Season Journey parts
3-10 with zero witnesses, so no speculative markers are added. Existing native
locations and alternatives are preserved. The report is in ignored dist/.

Data from ForeverDB.net (https://foreverdb.net). Copyright (C) 2026 ForeverDB.net;
selected data reused under its GPL-3.0 section 7(b) attribution terms. See
[FOREVERDB_LICENSE.txt](FOREVERDB_LICENSE.txt).

## Inputs and scope

Compared installed ForeverDB **0.57.16**, build **1.60.1.70862**, data snapshot
**2026-11-09.c00a7b34**, against QuestieDB **1.0.13** and QuestLite's
23 local chain corrections. ForeverDB_Helper **1.6.5** has no additional quest
prerequisite dataset; its gear, professions and planning features are outside
QuestLite's map/tooltip scope. No new runtime dependency is introduced.

| Dataset | Records |
| --- | ---: |
| QuestieDB quests | 5233 |
| ForeverDB Classic quest rows | 3491 |
| Forever client/player quest rows | 1472 |
| ForeverDB guide rows (mixed sources) | 3971 |
| Observed NPC location records | 613 |
| Observed quest-location records | 1377 |
| Client quest-map location records | 22 |

## Applied corrections

### Fixed quest levels

Fourteen observed fixed levels differ from the provider. Each has at least two
player records. Corrected values are used by level filtering and tooltip colours
on both maps. A correction applies only if the raw provider value still equals
the recorded old value, so later provider changes take precedence. Scaling levels
remain scaling; minimum pickup levels, class/race and prerequisites are untouched.

| Quest | ID | QuestieDB level | Observed level | Player records |
| --- | ---: | ---: | ---: | ---: |
| Fall of Dun Modr | 472 | 25 | 30 | 2 |
| Stone Tokens | 556 | 32 | 33 | 2 |
| Slowing the Orc Advance | 86757 | 30 | 32 | 2 |
| Bring Back a Bang | 88756 | 32 | 31 | 3 |
| Delicate Instruments | 91723 | 8 | 10 | 6 |
| Good Steel | 91732 | 7 | 10 | 6 |
| Rough Wolf Pelts | 91751 | 8 | 7 | 2 |
| Ira's Dagger | 96137 | 25 | 24 | 3 |
| Merrick's Bow | 96138 | 30 | 28 | 2 |
| The Valor Family | 96139 | 23 | 22 | 7 |
| Parts and Pieces | 97253 | 15 | 14 | 13 |
| Gleaming Crescent Necklace | 98027 | 26 | 29 | 2 |
| A Missing Hand | 99048 | 9 | 11 | 6 |
| Drive Them Out | 99080 | 11 | 9 | 2 |

### Missing Sulhasa location

QuestieDB has no Sulhasa (14242) spawn, hiding Field to Clear (98093). The local
fallback is Barrens map 1413 at **48.0, 77.5**, a player-observed position close to
the NPC. A firsthand [quest report](https://www.wowhead.com/forever/quest=98093/field-to-clear)
independently places her in the tree at 47.9,77.6. The fallback supplies pickups
and ready turn-ins on zone, continent and minimap views, and is ignored once
the provider has spawn data. It does not add objective markers.

### Horde library turn-ins

The observed Dalaran Digest turn-in is Owen Thadd (211022, Undercity), while
the provider lists only Garion Wendell (211033, Stormwind). The
[library collection report](https://www.wowhead.com/forever/quest=78127/the-dalaran-digest)
confirms the faction-specific librarians. QuestLite routes ready Horde turn-ins
for known collection records from Garion to Owen; Alliance retains Garion. This
covers 36 currently Garion-only collection/reward records. It changes neither
pickup eligibility nor shared provider data. Hidden collection pickups stay hidden.

## Differences deliberately not converted into restrictions

| Comparison | Differences | Disposition |
| --- | ---: | --- |
| Quest IDs absent from QuestieDB | 11 | All have zero observed players and no giver/ender; do not invent locations |
| Observed previous-quest links | 150 | Review sequence evidence; not proof of a mandatory gate |
| Giver/ender lists | 32 | 31 are observed subsets; preserve valid alternate givers. Library case corrected above |
| Quest levels | 21 | 14 corrected; three scaling values and four single-observer differences retained |
| NPC locations | 3 | Sulhasa filled; Gordo/Warcaller Gorlach positions left for roaming/alternate-location review |
| Classic prerequisite expressions | 152 | Mixed Classic/Forever semantics; retain provider and verified local rules |

ForeverDB's capture records a previous quest when a new dialog opens within its
short chain window after a turn-in at the same NPC. It is sequence evidence, not
a negative test that the quest was unavailable beforehand. Automatically importing
those links could repeat the disproven Skyborne Hunter breadcrumb restriction.
The provider's greater quest coverage and known alternate givers are retained.

The 11 unlocated records are To Have Loved and Lost (part 1), plus PvP Season
Journey parts 1–10. No evidence here establishes their current availability.

ForeverDB's loot browser combines Classic rates and player samples for dungeon
and raid loot. These are not a replacement for the source-specific active quest
item-rate dataset used by QuestLite, so no generic quest drop percentages were
overwritten. Gear, professions, routes, automation and other broad ForeverDB
features were not added to this focused addon.

## Reproduce and review

Run the following from the repository (offline Python/Lua tooling only):

```powershell
python tools/compare_foreverdb.py 'F:/World of Warcraft/_forever_/Interface/AddOns/QuestieDB' 'F:/World of Warcraft/_forever_/Interface/AddOns/ForeverDB'
```

The generated `dist/foreverdb-comparison.json` contains every difference, its
source classification, all 23 local chain comparisons and input SHA-256 hashes.
The report preserves native AND/OR prerequisite distinctions and normalizes
equivalent single-predecessor expressions. This snapshot is a review artifact;
it is never loaded into the game.

## Validation

Offline tests cover corrected level thresholds on both maps, scaling/new-provider
guards, missing NPC fallback precedence, ready turn-ins, Horde/Alliance librarian
selection, hidden collection pickups and provider immutability. Actual installed
provider data verifies all 14 levels, Sulhasa's location and both faction capitals.
These tests do not substitute for in-game verification.

## Refresh for ForeverDB 0.58.2 / QuestieDB 1.0.15 (0.4.6)

Data from ForeverDB.net (https://foreverdb.net), build 1.60.1.70888,
snapshot 2026-11-12.cc0c2a5c. The report now compares 5,768 provider quests with
1,742 observed/client quest rows, 3,516 Classic rows, 4,078 guide rows, 721 NPC
location records and 1,685 observed quest-location records.

The new eleventh quest field is an inferred faction hint, derived from NPCs and
quest sequences. The audit tool accepts the old ten-field and new eleven-field
formats, rejects unknown shapes and records the hint without turning it into
an eligibility restriction. Native race masks remain authoritative.

Four additional fixed-level corrections use the same guarded precedence:

| Quest | ID | Provider | Observed | Player records |
| --- | ---: | ---: | ---: | ---: |
| Silvia's Sword | 79363 | 27 | 26 | 5 |
| Never Coming Back | 98251 | 23 | 22 | 2 |
| A Void Path | 98252 | 23 | 22 | 2 |
| Vengeful Trail | 98417 | 28 | 30 | 4 |

There are now 18 stored level corrections; 15 still apply to current provider
differences. New provider values supersede the other three automatically.
Two differing minimum pickup levels (631 and 99052) remain review candidates;
observed completion levels alone do not establish a pickup threshold. Three
scaling-level differences remain scaling. Of 59 giver differences, 51 are
observed subsets, seven are covered by the existing Horde library correction,
and Ripped Missive's observed NPC versus native starter item is not converted
into a direct NPC pickup. It may represent the dropped item's source.

The same eleven missing IDs have no observed players or giver/ender data, so no
locations are invented. The 176 sequence candidates and 154 Classic requirement
differences are not imported as mandatory gates. Six NPC-location differences
include Sulhasa's existing fallback; the others are continent-only, special
summon, roaming or alternate-location candidates requiring corroboration.

## QuestieDB 1.1.0 recheck (0.4.7)

The ForeverDB input is unchanged. The provider grows to 5,893 quests and now
contains PvP Season Journey part 1 (96912), leaving ten unobserved IDs without
reliable map data. The report records 154 unmatched sequence candidates, 58 giver
rows, 20 level differences, six NPC locations and 162 Classic prerequisite
expression differences. All 25 historical chain corrections now have native
expressions and none is active as a fallback. The audit records native expressions
and fallback activity separately; it no longer treats retired local requirements
as active gates. No new inferred quest links are imported.

Camping 101: Herbalism (97968) is a known fresh turn-in change in the provider:
NPC 257021 replaces the older observed NPC 254345 after the November 10 hotfix.
Retain the newer provider data. Ripped Missive remains a starter-item-versus-NPC
observation candidate; seven librarian differences are already handled by the
existing faction-specific turn-in correction. The guarded level and Sulhasa
corrections continue to pass integration checks.

## ForeverDB 0.59.0 refresh (0.4.8)

Data from ForeverDB.net (https://foreverdb.net), build 1.60.1.70938, snapshot
2026-11-13.570e397b. Compared with the same QuestieDB 1.1.0 provider: 3,523
Classic rows, 1,877 observed/client quest rows, 4,110 guide rows, 773 NPC-location
records and 1,837 observed quest-location records. Ten IDs remain absent from
the provider; 161 sequence candidates, 61 giver rows, 20 level differences,
eight NPC-location candidates and 164 Classic expression differences are logged.

The fifteen currently applicable level corrections remain supported. The two
minimum-level review candidates, roaming/alternate NPC coordinates, stale
Herbalism turn-in observations and starter-item-versus-NPC differences are not
converted into new availability rules. No new class or race restriction is
inferred from this dataset's faction hints or completion observations.

## ForeverDB 0.60.5 / QuestieDB 1.1.1 (0.4.12)

Data from ForeverDB.net (https://foreverdb.net), build 1.60.1.70938, snapshot
2026-11-14.852e11f0. The installed TOC says 0.60.5 while this snapshot's metadata
says addon 0.60.4. The read-only audit records the actual data metadata and hashes.
Its eleven-field quest schema is unchanged.

Compared 5,914 provider quests with 3,529 Classic rows, 1,964 observed/client
rows, 4,142 guide rows, 812 NPC-location records and 1,923 observed quest-location
records. Nine IDs lack provider records. There are 169 unmatched sequence
candidates, 46 giver differences, 21 level differences, eight NPC-location
candidates and 164 Classic requirement-expression differences. Fourteen observed
fixed-level differences are currently resolved by existing guarded corrections.

Bring Back a Bang (88756) is now level 31 natively; its old 32-to-31 local
correction no longer applies. Three minimum-level differences (631, 91723,
99052) remain candidates; completion observations do not establish a pickup
threshold. Ripped Missive's starter item, the provider's newer Herbalism turn-in,
and roaming/alternate locations remain unchanged. No observed sequence is
converted automatically into a mandatory prerequisite.

## ForeverDB 0.62.1 / QuestieDB 1.1.2 (0.4.13)

Data from ForeverDB.net (https://foreverdb.net), build 1.60.1.70938, snapshot
2026-11-16.ed74a169. Compared 5,922 provider quests with 3,530 Classic rows,
2,312 observed/client quest rows, 4,312 guide rows, 940 NPC-location records and
2,272 observed quest-location records. The eleven-field schema remains compatible.

Nine IDs lack provider records. The report logs 195 unmatched sequence candidates,
55 giver differences, 21 level differences, seven NPC-location candidates and
165 Classic prerequisite expression differences. Fourteen fixed-level differences
remain handled by existing guarded corrections. No new mandatory chain, minimum
pickup level or roaming-location correction is justified by these observations.

Sulhasa is no longer a missing-location difference: native 47.93,77.62 is close
to the observed position and takes precedence automatically. The fallback stays
available for older providers. Newer native Herbalism turn-in data, the Ripped
Missive starter item and all existing class/race corrections retain precedence
and behavior. All 25 historical chain fixes remain inactive fallbacks with this
provider's native prerequisite expressions.

## ForeverDB 0.64.1 (0.4.17)

Data from ForeverDB.net (https://foreverdb.net), build 1.60.1.70938, snapshot
2026-11-18.17caad86. Compared with QuestieDB 1.1.2: 3,536 Classic rows, 2,585
observed/client quest rows, 4,397 guide rows, 1,042 NPC-location records and 2,547
observed quest-location records. The provider has 5,922 quests; nine missing IDs
remain without invented locations.

The Corrupter (1484) has observed fixed quest level 33 from three players versus
native 35. Added a guarded 35-to-33 correction; newer native values win. There
are now nineteen stored fixed-level corrections, fifteen applicable to current
observed differences. Four other level differences concern minimum pickup levels
(631, 632, 91723, 99052) and remain unmodified; scaling values remain scaling.

The refreshed report records 218 unmatched sequence candidates, 61 giver rows,
23 level differences, nine NPC-location candidates and 168 Classic requirement
expression differences. Sequence candidates do not prove mandatory gates. New
roaming/alternate locations and Ripped Missive's item-versus-NPC observation remain
unmodified. The verified Step One: Rock introduction is a separate local policy
correction backed by player evidence; this snapshot has no direct observed
95183 predecessor record to import automatically.
