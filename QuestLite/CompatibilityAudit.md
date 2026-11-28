# Updated reference addon verification - 0.2.13

## Current review: 2026-11-19 / QuestLite 0.4.22

### Follow-up at 14:12 client load failure

ForeverDB is now 0.67.1, snapshot 2026-11-19.24a7fd5e, with Helper 1.7.4.
Questie 12.11.1, QuestieDB Forever 1.1.3 / contract 4, QuestieTrace 1.13.0 and
Loot Sparkles 2.0.0 are unchanged. The full comparison still has the same review
candidate counts; observed/client rows increased to 2834 and quest locations to
2796. No new correction or dependency migration is justified for QuestLite.

FrameXML.log records at 14:12:56 that QuestieDB failed to load as missing and
QuestLite was then blocked by its required dependency. The installed QuestieDB
folder contains the correct Interface 16001 Forever TOC; all 51 referenced files
exist and the provider loads under the offline harness. The TOC was created at
12:00:58, after the client log's 09:02 startup. A stale client addon discovery list
is a plausible explanation, not a confirmed diagnosis. Full client restart and
live dependency recognition remain pending; no replacement TOC, third-party Lua
patch, dependency removal or warning suppression was applied.

| Installed reference | Version | Result |
| --- | --- | --- |
| Questie | 12.11.1 | Regenerated policy: eight additional hidden IDs (1374, 1380, 1381, 78150, 78917, 79536, 82208, 93862). Three were already covered by collection policy. Total 628 hidden IDs, 1164 tag corrections, including 238 PvP tags. |
| QuestieDB | 1.1.3 | Contract 4 unchanged. All 5982 native quests read successfully. Native field/location updates retain precedence over guarded fallbacks. |
| QuestieTrace | 1.13.0 | Recording, privacy and UI code is independent of QuestLite. No recorder API or saved-variable dependency to migrate. |
| ForeverDB | 0.67.0 | Snapshot 2026-11-19.da52610c, build 1.60.1.70959. Full comparison completed; existing data schema supported. No new dependency or speculative gates. |
| ForeverDB_Helper | 1.7.3 | Unchanged; no dependency. |
| Forever Loot Sparkles | 2.0.0 | Unchanged. Native sparkles and retired soft-target cleanup retained. |

The [published Questie changelog](https://www.curseforge.com/wow/addons/questie/files/9701389)
and installed QuestieDB changelog identify the upstream changes. All 22 Darkspear
quest variants now appear in the provider. Their upstream PvP tags cover 98892,
98894, 98900 and 98902, absent from the older eighteen-ID manual supplement.

Targeted installed-data regressions verify all four Buying Friendship quests at
reputation -1 versus Neutral 0, the Raene's Cleansing chain, Tauren-only Earthmother
masks, and newly Horde-wide masks on Paladin quests 91862/96204. Older mask and
inventory assertions were updated; wrong-class/race rejection still covers every
record. Modera's coordinate correction comes from the provider, requiring no local
override. XP and translation changes require no migration. Questie's recolor fix
belongs to its renderer: QuestLite's icon reuse, hover, edge-exit and motion tests
pass. Questie tracker modifier shortcuts are not an integration surface here.

Validation: 117 Lua regressions, two packaging tests, both installed-provider
profiles and full ForeverDB comparison. Only generated reference data changes;
protected UI, tooltip hooks and map rendering are unchanged. Client smoke status:
not performed for 0.4.22; after reload, check PvP-filtered Darkspear pickups and
ordinary pickup/ready turn-in markers. No live-client success is claimed.

Verified against the installed packages on 2026-11-08:

| Package | Installed version | QuestLite impact |
| --- | --- | --- |
| Questie | 12.6.4 | Rebuilt the reference availability policy. Six new NYI quest exclusions were imported: 5691, 5692, 5693, 5704, 5705, 5706. Total hidden/conditional entries: 574. |
| QuestieDB | 1.0.13 | Contract remains 4, with minimum supported contract 1. No API migration is needed. Entity reads, support tables, map mappings, metadata decoding and drop-rate data passed the offline integration. |
| QuestieTrace | 1.9.2 | The Interface 16001 package is QuestieTrace-Camelot.toc. QuestLite does not call its APIs or depend on it; no integration change is needed. |

QuestieDB 1.0.13's packaged changelog lists Sleeping Bag chain fixes, a Forever
objective-location fix for The Sleeper Has Awakened, and additional quest XP.
QuestLite uses the provider's current data directly and adds no objective pins.

The item-related review confirmed that The Tortured Soul (95883) and The Offering
of Blood (95885) have native preQuestSingle links in the updated provider. Their
redundant local overrides were removed. The six relic/Dalaran links documented in
ItemGateAudit.md remain absent from native requirements and retain local overrides.

The availability generator now records the actual installed package versions in
its generated data and event report instead of leaving a stale report version.
The AQ/holiday audit still covers all twelve holiday files, both separate event
lists, fifteen event categories and all 308 event-tagged composed quests. No new
event category or unreviewed separate quest table was found.

Validation: 62 offline Lua 5.1 regressions; both real-data integration profiles;
19,516 source/correction drop-rate comparisons; native-style map/minimap hover;
prerequisite turn-in checks and provider-data immutability. These checks do not
replace a live client rendering or server-availability check.

## Skyborne race encoding (0.3.10)

The provider's public `Enum.raceMaskById` maps actual race IDs to single-bit
quest masks. Forever's Skyborne IDs are 95 (Alliance) and 96 (Horde), encoded
as 4294967296 and 8589934592. They are not race IDs 33/34. Computing
`2^(raceID-1)` incorrectly rejected their restricted quests, including Taming
the Beast (94978) from Quel'ana Quickgale.

Race eligibility now uses the provider mapping, with arithmetic membership to
preserve bits above 32. Class masks keep their separate handling. Unknown race
IDs do not match a restricted quest; legacy low race IDs retain a fallback only
when the provider has no race mapping table. No provider data is mutated.

Offline regressions cover actual race IDs 95/96 on both maps, opposing factions,
wrong classes, confirmed offers, broad mode and invalid IDs. The installed-data
check emits quest 94978 at 59.56,72.63 for both Skyborne Hunter profiles at level
10, verifies its later native prerequisites, and rejects level 9 and other races
or classes. These checks emulate the client and require in-game verification.

## QuestieDB 1.0.14 review (0.4.5)

Rechecked the updated baked provider. It now has the native Rogue mask (8) for
Goblin Lockpicks; the local class fallback remains compatible with 1.0.13, while
integration tests accept and preserve either native value. The Horde Dalaran
entry gaps remain and are corrected as documented in AvailabilityAudit.md.

Regenerated the event policy against the installed Questie reference and updated
provider: 581 hidden/conditional IDs, including 220 holiday IDs. All 12 holiday
registrations and 15 reviewed event categories were checked. Runtime category
filtering already covers new tagged entries; the compact static list now agrees
with the updated provider too. The existing race-ID mapping and level-correction
precedence remain unchanged.

## Reference updates reviewed 2026-11-12 (0.4.6)

| Package | Installed version | Result |
| --- | --- | --- |
| Questie | 12.7.0 | Reviewed upstream 12.6.4-to-12.7.0 comparison and current availability code. Imported updated exclusions and the zero-minimum-level fallback. Tracker, party objective, XP, townsfolk and announcement changes are outside this addon's scope. |
| QuestieDB | 1.0.15 | Public API remains contract 4, minimum supported 1. Full baked-provider integration passes. New data is consumed directly. |
| QuestieTrace | 1.10.0 | Independent collector; QuestLite neither calls nor loads its API. No runtime integration change. |
| ForeverDB | 0.58.2 | Read-only data comparison refreshed for build 1.60.1.70888, snapshot 2026-11-12.cc0c2a5c. Four additional observed fixed levels corrected; see ForeverDBAudit.md. |
| ForeverDB_Helper | 1.7.2 | Independent companion with no QuestLite API dependency. No additional runtime dependency introduced. |
| Forever Loot Sparkles | 2.0.0 | Unchanged from the previous review; built-in loot effects and legacy cleanup already match its safety direction. |

The generated policy now contains 607 hidden/conditional quest IDs, up from 581
in our previous local build. Holiday coverage remains 220 IDs; 109 AQ entries,
12 holiday registrations, 15 event categories and 11 hidden givers are checked.
All 313 event-tagged provider quests are covered. Explicit valid NPC offers can
still restore conditional entries; class/chain rules retain precedence.

Questie's minimum-level fix treats requiredLevel=0 as missing data and falls back
to a positive questLevel. QuestLite now does the same in strict mode and detailed
tooltips. Known positive minimums, scaling levels, confirmed offers and the broad
browse mode retain their behavior. Show low-level quests does not bypass this
pickup minimum. There are 84 fixed-level rows with a zero minimum in this provider.

QuestieDB now supplies Trouble in the Valley's Hermit Tanner predecessor. The
existing local requirement remains for older installations. Integration captures
the native predecessor values before evaluation and verifies they are unchanged,
instead of requiring the field to remain absent. Three Paladin chain steps
(91860, 95125, 95126) now have the provider's Horde-wide race mask; QuestLite honors
it while retaining Paladin, faction and prerequisite restrictions. No manual
Undead-only restriction was added.

Validation: 90 offline Lua 5.1 regressions; both installed-provider profiles;
19,518 drop-rate pairs; world-map/minimap hover and source clustering; race,
class, prerequisite, provider immutability and guarded correction precedence.
These checks do not establish live server availability or resolve the separately
reported Blizzard action-bar secret-value error.

Sources: [Questie comparison](https://github.com/Questie/Questie/compare/v12.6.4...v12.7.0),
[QuestieDB changes](https://github.com/Questie/QuestieDB/compare/v1.0.14...v1.0.15),
and the installed packages' generated data and changelogs.

## Questie 12.8.0 / QuestieDB 1.1.0 (0.4.7)

Compared the installed updates and upstream changes since 12.7.0 and 1.0.15.
QuestieTrace 1.10.0, Forever Loot Sparkles 2.0.0, ForeverDB 0.58.2 (same data
snapshot) and ForeverDB_Helper 1.7.2 are unchanged from the previous audit.

QuestieDB still supports public contract 4. Its updated native data now includes
all 25 historical local chain corrections. Local requirements now apply only
when native prerequisite fields are empty. The older Dalaran Patrols shape
(preQuestSingle={544}, no group) retains its missing Key to the City fallback;
its new native AND list {544,93680} takes precedence. Other native AND/OR lists
are evaluated directly. This preserves native alternatives for Friend of the
Kirin Tor and Shrewd Negotiations instead of narrowing them with stale patches.
Fallback records remain available for older QuestieDB installations.

The Paladin chain now also broadens A Curious Pair (91859) and An Underrated
Talent (95111) to the native Horde race mask. Class and prerequisite checks remain
in force. The independently available Skyborne Hunter referral (94007) still has
no invented breadcrumb or mandatory taming link.

The regenerated exclusion table grows from 607 to 616 IDs: 7790, 8152, 78132,
78133, 78134, 79090, 79098, 91902 and 91907. The Dragonslayer trio was already
season-restricted locally. Repelling Invaders and Clear the Forest! now also
carry explicit SoD labels and remain hidden in strict mode, including stale offer
observations. Broad browsing can show them with the label. Two new Sealed Crate
variants follow the existing conditional collection policy. Holiday coverage
remains 220 IDs, with all 313 event-tagged quests covered.

Questie's HereBeDragons isolation and manual-icon changes do not require a port:
QuestLite uses its own MapCanvas template and minimap frames and does not consume
Questie's HereBeDragons libraries. Automatic quest acceptance, tracker, target
frame and settings-builder changes are outside its scope. Questie's new Darkmoon
Faire activation is not imported as an assumed global event state; QuestLite's
existing event policy still requires a current server offer in strict mode.

The updated provider supplies Camping 101: Herbalism's hotfixed turn-in NPC
257021. Older ForeverDB observations still point to 254345; no fallback overwrites
the newer provider. Lady Dena Kennedy's new spawn data and other entity, XP and
translation updates are consumed through the provider where applicable; objective
locations remain Blizzard's responsibility.

Validation: 92 offline regressions, both real QuestieDB 1.1.0 profiles, 19,518
source/correction drop-rate pairs, native Dalaran OR alternatives, native AND
requirements, historical fallback behavior, Paladin race masks, hover and source
clustering. Provider requirement snapshots are checked for immutability instead
of asserting that newly fixed fields remain missing. No live-client validation
or action-bar taint attribution is claimed.

Sources: [Questie 12.8.0 comparison](https://github.com/Questie/Questie/compare/v12.7.0...v12.8.0),
[QuestieDB 1.1.0 comparison](https://github.com/Questie/QuestieDB/compare/v1.0.15...v1.1.0).

## Reference refresh and character filters (0.4.8, 2026-11-13)

Installed Questie 12.8.0, QuestieDB 1.1.0, QuestieTrace 1.10.0, Forever Loot
Sparkles 2.0.0 and ForeverDB_Helper 1.7.2 are unchanged from the previous audit.
ForeverDB is now 0.59.0, build 1.60.1.70938, snapshot 2026-11-13.570e397b.
Its eleven-field quest schema still parses; no new runtime API dependency is used.
The comparison finds no additional supported level or location correction to
apply. Guarded fixes and newer provider turn-in data retain precedence.

Fixed five missing class masks and Compendium of the Fallen's omitted Horde
Skyborne race bit. See ClassSeasonAudit.md for evidence, exact masks, exceptions
and the 59,254-case installed-data rejection sweep. All 95 offline regressions
and both installed-provider profiles pass, including map/minimap rendering,
correct-class positive cases and provider data immutability. The low-level
checkbox continues to affect only the display cutoff, never class/race eligibility.

## Reference refresh 2026-11-14 (0.4.12)

| Package | Installed version | QuestLite result |
| --- | --- | --- |
| Questie | 12.9.0 | Imported Rekindle (80001), the new Forever non-SoD exclusion; added its explicit SoD label/strict block. QuestieTrace bundling, DBM HUD and localization changes need no port. |
| QuestieDB | 1.1.1 | API remains contract 4, minimum supported 1. Updated entity, translation and XP records are consumed directly where used. Bring Back a Bang now has native level 31; the guarded local level correction automatically yields. |
| QuestieTrace | 1.11.0 | Independent recorder, now bundled upstream with Questie. No QuestLite API calls or new dependency. |
| ForeverDB | 0.60.5 | Rechecked generated data snapshot 2026-11-14.852e11f0, whose Meta.lua identifies addon 0.60.4, build 1.60.1.70938. This distinction is retained rather than assuming a different dataset. |
| ForeverDB_Helper | 1.7.3 | Independent companion UI/planner. No QuestLite integration change required. |
| Forever Loot Sparkles | 2.0.0 | Unchanged; no custom interaction sparkles are restored. |

The hidden/conditional policy grows from 616 to 617 IDs, adding only 80001.
Holiday/event coverage remains 220 holiday IDs, 109 AQ entries, twelve holiday
registrations, fifteen event categories and all 313 tagged provider quests.
The same 1,142 applicable Questie tag corrections include 216 PvP corrections;
the PvP option, per-quest hidden list and item-drop source toggle remain intact.

The character-mask review still finds the same five missing class masks plus
the known Junkboxes Needed category exception. Call of Air remains missing its
Shaman mask and Compendium of the Fallen still excludes Horde Skyborne in raw
data, so all six guarded character-field corrections remain necessary. No new
race/category restriction was inferred. Native prerequisites retain precedence.

ForeverDB's new observations do not justify new mandatory links, minimum pickup
levels or roaming-location replacements. See ForeverDBAudit.md for candidate
counts. The current provider still supersedes older Herbalism turn-in reports.

Validation: 101 offline regressions and both installed-provider profiles; 58,868
wrong-class/race rejection checks, actual Compendium/Call of Air pickups, Skyborne
Hunter referral behavior, native Dalaran AND/OR lists, 19,518 drop-rate pairs,
all 216 PvP corrections, map/minimap hover and source/hide-restore behavior.
These checks emulate the client; no live availability or action-bar taint claim.

Sources: [Questie comparison](https://github.com/Questie/Questie/compare/v12.8.0...v12.9.0),
[QuestieDB comparison](https://github.com/Questie/QuestieDB/compare/v1.1.0...v1.1.1),
and the installed artifacts' changelogs, metadata and generated data.

## Reference refresh 2026-11-17 (0.4.13)

| Package | Installed version | QuestLite result |
| --- | --- | --- |
| Questie | 12.10.0 | Imported the three removed Hearts of the Lost chain exclusions. The new disabledByQuest behavior already matches QuestLite: only an active disabling quest blocks, not a previously completed one. Tracker, sharing, QBF/QBZ next-chain, escort auto-accept and DBM changes are outside scope. |
| QuestieDB | 1.1.2 | Contract remains 4, minimum supported 1. Updated entities/XP/translations are consumed directly where used; Powderfuse enum additions need no local copy. Native Sulhasa coordinates now supersede the older fallback. |
| ForeverDB | 0.62.1 | Snapshot 2026-11-16.ed74a169, build 1.60.1.70938. Read-only comparison still parses; no additional verified runtime correction is needed. |
| QuestieTrace | 1.11.0 | Unchanged from the previous audit; independent recorder. |
| ForeverDB_Helper | 1.7.3 | Unchanged; no QuestLite API dependency. |
| Forever Loot Sparkles | 2.0.0 | Unchanged; custom interaction sparkles remain retired. |

The generated hidden/conditional table grows from 617 to 620 IDs, adding only
87318 (Hearts of the Lost), 88757 (Accessories of the Lost), and 88758 (Sentiments
of the Lost). Questie's source marks the chain as absent on Forever. Ordinary
strict-mode pickups are excluded; broad browsing and explicit current NPC offers
retain their established behavior. No new speculative prerequisite is added.

All 313 event-tagged quests remain covered; holiday/AQ/giver counts and the 1,142
Questie tag corrections (216 PvP) are unchanged. The same six class/race field
fallbacks are still needed, including Alaana's Shaman restriction and Compendium's
Horde Skyborne bit. Native prerequisite expressions continue to supersede all
25 older local chain fixes.

Sulhasa (14242) now has native Barrens coordinates 47.93,77.62. The runtime already
prefers native spawns over the 48.0,77.5 fallback. Updated the integration fixture
to compare against current native data, falling back only when native coordinates
are absent; it also fingerprints the provider's spawn rows to verify immutability.
No forced replacement of newer coordinates is introduced.

Validation: 101 offline regressions; both installed-provider profiles; 58,894
wrong-class/race rejection checks; 19,518 drop-rate pairs; all 216 PvP corrections;
actual screenshot quests, map/minimap hover, source toggles and per-quest hide/
restore. Offline checks do not establish live server-only availability or resolve
the separate action-bar secret-value error.

Sources: [Questie comparison](https://github.com/Questie/Questie/compare/v12.9.0...v12.10.0),
[QuestieDB comparison](https://github.com/Questie/QuestieDB/compare/v1.1.1...v1.1.2),
and installed generated artifacts/changelogs.

## Reference refresh 2026-11-18 (0.4.17)

Installed versions: Questie 12.10.0, QuestieDB 1.1.2, QuestieTrace 1.12.0,
Forever Loot Sparkles 2.0.0, ForeverDB 0.64.1, ForeverDB_Helper 1.7.3.
Only ForeverDB changed since the previous inventory. QuestieTrace's 1.12.0 was
already installed during the previous check; the older 1.11.0 audit row was stale.
QuestLite still has no runtime dependency on its recorder/UI APIs.

Compared ForeverDB's 2026-11-18.17caad86 snapshot, build 1.60.1.70938. Its existing
eleven-field schema parses. Added one guarded fixed-level correction: The Corrupter
(1484), 35 -> 33, supported by three player records. Four minimum pickup-level
differences remain review candidates; completion observations are not treated as
pickup thresholds. No new source-item or faction rule is inferred from the data.

Added the verified Land of Giants prerequisite for Step One: Rock as documented
in AvailabilityAudit.md. The two map markers refer to one quest. Native data and
all existing class/race, event/PvP, cloth and user-hidden filters retain precedence.
The generated exclusion and tag policy is refreshed against the same installed
Questie/QuestieDB references; no additional upstream policy change was found.

Validation: 108 offline regressions, both installed-provider profiles, the full
ForeverDB comparison, guarded level/native location precedence, real Hamur and
Gorgegut source markers, prerequisite guidance and existing hide/restore controls.
These checks emulate the client; live server availability after turning in the
introduction still needs an in-game check.

## Betrayed review - 0.4.19

Kept QuestieDB 1.1.2's minimum pickup level 44 and quest level 53 for quest 3504.
The user confirmed Belgrom does not offer it; the missing server condition is
unknown. Strict mode now requires a current offer for this specific pickup,
without changing provider data or inventing prerequisites. The quest guide and
expanded details show minimum pickup level separately from quest difficulty.
Validation: 113 offline regressions and both installed QuestieDB profiles passed,
including actual quest metadata, offer/faction precedence and both map paths.
No live client test was performed.

## Zone-wide dropped starters - 0.4.20

Reviewed installed Questie 12.10.0 AvailableQuests.DrawAvailableQuest: it expands
item starters through NPC/object drop sources with icon limits, not a general
finisher substitution. QuestLite deliberately uses delivery destinations for
explicitly reviewed zone-wide starters 351, 485, 635 and 2766 instead. QuestieDB
1.1.2 identifies the three OOX robot finishers and Myzrael's crystal object; no
provider records are changed. The destination flag retains pickup eligibility
and hiding controls without labelling an unaccepted quest complete. A missing
finisher list falls back to ordinary sources. NPC offer-list absence is irrelevant
to these reference destinations. All other item starters keep existing behavior.

Validation: 116 offline regressions and both installed-provider profiles passed,
covering actual destination coordinates, both maps, tooltip wording, hide/restore,
item-start toggle, active/ready states, ordinary starters and absent finisher data.
Movement and forced-refresh checks keep the destination fixed, and hide its
minimap marker when the player leaves range rather than selecting a nearby drop.
Live client appearance has not been tested.

## Reference refresh 2026-11-21

Regenerated the display policy from the installed Questie 12.12.0 and QuestieDB
Forever 1.1.4 (contract 4). There are now 633 hidden or conditional quest IDs
and 1,411 tag corrections, including 238 PvP overrides. The event-category
coverage remains 313 quests, with 220 in the holiday list and 109 in the AQ War
Effort list. The lists overlap. See [event coverage](EventCoverage.md).

QuestieDB now marks Quel'ana Quickgale's four taming and training quests as
Alliance Skyborne only. Elayaa's referral still permits both Skyborne races.
The provider also widens Diplomatic Incident's Paladin race mask and records
Modera at 68.62, 45.13. The integration checks confirm QuestLite respects these
native records and preserves them across map scans.

All 117 offline behavior tests, both installed-provider profiles and package
checks passed. Live Forever map rendering remains pending.

[Questie 12.12.0 bundle](https://github.com/Questie/Questie/releases/tag/bundle/v12.12.0%2Bv1.1.4)
and [QuestieDB 1.1.4](https://github.com/Questie/QuestieDB/releases/tag/v1.1.4).

## Reference refresh 2026-11-23

Regenerated the bundled policy with Questie 12.12.0 and QuestieDB Forever
1.1.5. The refresh adds one tag override for quest 97413. The 633
hidden or conditional quests and 238 PvP overrides remain at the previous counts.
Both offline installed-provider profiles passed with QuestieDB 1.1.5. The
installed build matched the package on disk. The player confirmed the live
Forever smoke test on November 23: `/ql status` showed 0.4.23, known quest-item
drops displayed NPC rates, an item without a known NPC rate showed no empty
section, and a world-map marker opened its quest guide.

## Questie 12.15.0 and QuestieDB 1.1.6 (0.4.38)

Regenerated the bundled policy against the installed Forever sources. The
new policy adds seven exclusions, eight Season of Discovery classifications,
and one quest-tag correction. The standalone ForeverDB 0.77.3 comparison was
also run. Its additional level, giver, location and sequence differences
remain review candidates. Live verification of the updated exclusion list is
pending.
