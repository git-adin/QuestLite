# Availability policy audit - 0.3.2

## Betrayed pickup review - 0.4.19

The level-45 Horde player confirmed that Belgrom Rockmaul does not offer
Betrayed (3504). QuestieDB 1.1.2 and ForeverDB Classic both list minimum 44,
quest level 53, with no prerequisite. The
[AllTheThings Forever Azshara data](https://github.com/DFortun81/AllTheThings/blob/master/.contrib/.db/forever/zones/kalimdor/azshara.lua)
also lists minimum 44 and giver 4485. A
[Forever player report](https://www.wowhead.com/forever/quest=3504/betrayed)
similarly says the giver does not offer it. The actual missing condition remains
unverified: no higher level, reputation or prerequisite is invented.

Quest 3504 is explicitly offer-only in strict mode, using the existing bounded
NPC offer observations. Broad browsing remains possible; actual offers restore
the pickup while respecting faction/class/chain checks. Ready turn-ins are
unaffected. The guide and expanded details distinguish difficulty from minimum
pickup level, and label missing minimum data as unknown. Offline tests cover both
maps, offer arrival/removal, broad mode, faction rejection and ready turn-ins.

Checked against the installed Forever Questie v12.6.4 and QuestieDB v1.0.13.
This is a consumer-policy comparison, not a live server availability scan.

## Missing policies corrected

| Area | Result |
| --- | --- |
| Hidden, obsolete, duplicate, conditional and holiday entries | Imported 574 applicable quest IDs, including 215 registered holiday IDs and 109 AQ entries, evaluated in Forever's Classic rules context and intersected with the installed Forever database. Three additional event-category entries were caught independently in database metadata. Questie 12.6.4 adds six NYI priest quest exclusions: 5691, 5692, 5693, 5704, 5705, 5706. |
| Event coverage sweep | All 12 holiday registration files, both separate AQ/invasion lists and 15 database event categories checked. New categorized quests are filtered at runtime; generation rejects unreviewed event tables or holiday enum categories. See EventCoverage.md. |
| AQ War Effort | Corrected a missed separate Questie category: supply donations, repeat turn-ins, and one/ten commendation signets are hidden unless a current NPC offer confirms availability. |
| NPC display exclusions | Imported 11 applicable giver exclusions. Loot-drop creatures are not treated as quest givers. |
| Library catalog | Added the 40 book entries and four collection milestones; their raw database minimum is often 1 and class mask 0. They should not advertise the entire library catalog as ordinary pickups. |
| Scourge Invasion | Added the 29 invasion quest IDs, including 9265 from Lieutenant Rukag. Explicit server offers can restore them. |
| Profession ranks | Check learned rank spells from 16 profession tables; positive ranks permit that rank or higher, negative ranks exclude the exact learned rank. |
| Profession specialization | Distinguish a required specialization spell from a profession ID meaning no specialization chosen. |
| Reputation | Unknown required reputation no longer passes the strict filter silently. |
| Race masks | Use numeric bit tests without 32-bit truncation; do not impose retail race/class combinations on Forever. |
| Confirmed-offer faction/class bypass | Mandatory race/class masks now run before the confirmed-NPC shortcut, so confirmed offers cannot bypass faction eligibility. Tested for Horde races 2, 5, 6, 8 and 34, and Alliance rejection, including broad mode. |
| NPC dialogs | Handle gossip, Forever's quest greeting ID tuple, and positive quest-detail offers. A single detail dialog never proves other quests absent. |
| Server authority | A current explicit offer can restore a filtered event/collection quest or repeatable, even when database/completion flags disagree. Known chain requirements still apply in strict mode. Other givers do not inherit that confirmation. |
| Chain override bypass | Corrected an early return that let NPC confirmation skip required predecessors, grouped prerequisites, active parents and active-or-complete unlocks. A new regression walks a three-step chain through acceptance, objective completion and turn-in on both maps. |
| Missing Mankrik chain data | The installed provider has no prerequisite or forward/backward link between 4921 and 95774. A local correction requires Lost in Battle to be turned in before Her Name Is Olgra appears; the provider remains untouched. |
| Missing relic and item-related chain links | Verified eight prerequisite links across Earthen Echo, Prehistoric Prism, the Offering Stone chain, and the Alliance/Horde Heart of Disruption chains. QuestieDB 1.0.13 supplies the two Offering Stone links; the other six need local corrections. The 0.2.12 Earthen Echo inventory workaround was replaced: its source item is provided on acceptance; completing Elder Knowledge is the actual gate. See ItemGateAudit.md. |
| Daily resets | The native daily-reset boundary participates in cache keys, so unchanged quest-log identity does not preserve yesterday's snapshot. |
| Tooltip claims | Only an explicit server offer is labeled Available. Predicted pickups say Pickup; the broad view says Unfiltered. |

Existing level, minimum/maximum level, class, race, prerequisite, exclusivity,
parent/child chain, breadcrumb, skill, signed learned-spell, required-item,
completion, and inventory/quest-state invalidation checks were reviewed.
Both maps use the same predicate and policy tables. Active turn-ins are not
hidden by pickup-only policy.

## Scope decisions and limits

- Do not import SoD, TBC, Wrath, Cataclysm, Mists, Hardcore or regional phase
  assumptions into Forever. The extraction uses the same base Classic expansion
  context as the installed Forever consumer. Real server offers override policy.
- The Wrath achievement examples in Questie's availability code are absent from
  the installed Forever database. They do not justify adding an achievement
  subsystem or its memory cost here.
- Automatic calendar-based activation and private realm phase detection are not
  implemented. **Conditional holiday/event entries require an NPC offer while
  the strict filter is on. This can hide an active holiday before you visit its
  giver.** Turn the filter off to browse all such candidates.
- Unknown custom server conditions and daily rotations still need an actual NPC
  interaction. These are not globally discoverable from the installed database.
- NPC observations are session-only and invalidated on relevant character
  changes; `/ql refresh` clears them. Invalid or unresolved dialog IDs do not
  establish absence.

## Regression evidence

The offline integration loads the installed database and its dynamic Horde
corrections as a level 22 undead paladin. In Undercity, the broad uncompleted
pickup list has 176 distinct quests; the filtered list has 9. The library IDs
and inactive investigation 9265 are absent; an explicit NPC offer restores 9265
with confirmed status. This simulation does not contain the user's actual quest
log or completion history, so 9 is not a prediction of the live character's count.

Tests cover the on/off cache boundary, both map consumers, confirmed offers,
gossip/greeting/detail paths, repeatables, rank/spec rules, reputation, wide
race masks, daily-reset invalidation, native-style hover registration and the
two screenshot examples. Renderer and live server behavior still require an
in-game check.

Additional Orgrimmar regression: the same character profile has 48 AQ pickup
candidates in the broad view, including Firebloom, Peacebloom and commendation
signets. All are absent in the filtered world-map and minimap paths. The AQ list
is extracted explicitly from `AQWarEffortQuests`, separately from holidays and
the ordinary blacklist; the earlier audit omitted this independent category.

## Rebuilding the policy snapshot

`tools/build_availability_policy.py QUESTIE_DIR QUESTIEDB_DIR` generates
`AvailabilityPolicyData.lua` from local reference data in a restricted offline
Lua environment. The generated file records source version and a content hash.
Only compact policy tables ship; Questie is not a runtime dependency. Review
the generated change and rerun tests when updating either reference addon.

Policy references: Questie's `QuestieQuestBlacklist.lua`, `QuestieNPCBlacklist.lua`,
holiday quest registrations and `QuestieProfessions.lua`. The addon retains its
GPL license and source attribution.

## Scout Support corrections (0.3.7)

QuestieDB 1.0.13 omits prerequisite fields on Scout Support (98094) and Valuable
Vantages (98095). Local strict-mode corrections require Battle of Hillsbrad
part II (528) turned in before 98094, then 98094 turned in before 98095.
[Scout Support's firsthand reports](https://www.wowhead.com/forever/quest=98094/scout-support)
identify part II (the peasants), and its quest series lists
[Valuable Vantages](https://www.wowhead.com/forever/quest=98095/valuable-vantages)
as the follow-up. Darthalia's Orders is provided on acceptance, not a bag gate.
Native minimum level, race/class restrictions and provider data are preserved.
Both maps are tested before acceptance, at objective completion and after turn-in;
confirmed offers cannot bypass the prerequisite. Broad view still permits browsing.

## Skyborne Hunter referral: live-server correction (0.3.12)

Elayaa Easewind's Taming the Beast (94007) remains available after the player
completes pet-training quests. The user's live-server check on 2026-11-09
confirmed acceptance while already having a trained pet. The provider has no
breadcrumb relationship to the first taming exercise (94978). This absence must
not be interpreted as missing data merely from the quest text or a series list.

The inferred 0.3.11 override was removed. Both quests retain their independent
native eligibility, and known database breadcrumb relationships keep their prior
behavior. Tests now verify that 94007 remains visible before acceptance on both
maps after pet training, including confirmed offers. Accepted quests still use
the normal active/ready-turn-in behavior. Provider data remains unchanged.

## Walton turn-in requirements (0.4.1)

The player's live report and firsthand reports on
[Unwelcome Guests](https://www.wowhead.com/forever/quest=95508/unwelcome-guests)
describe delivering The Hermit Tanner (95495), investigating for Trouble in the
Valley (95621), then defending Walton in Unwelcome Guests (95508). QuestieDB
omits prerequisites for both Walton pickups. Local corrections require 95495
turned in before 95621, then 95621 turned in before 95508. Active or merely
objective-complete predecessors are insufficient. Ready turn-ins are preserved.

No new requirement is placed on Vrang's earlier quests: sources disagree about
whether both of his gathering quests are required for The Hermit Tanner. A quest
series listing by itself does not justify inventing that restriction. Broad mode
still permits browsing; native faction/class masks and shared provider data are
preserved. Both maps and confirmed-offer handling have regression coverage.

## Horde Dalaran attunement lead-in (0.4.5; QuestieDB 1.0.14)

The updated provider still has no prerequisites for Blood in the Streets (92434).
Dalaran Patrols (545) records Prison Break In (544) but omits Key to the City
(93680). [The attunement guide](https://www.wowhead.com/forever/news/how-to-become-attuned-to-city-of-dalaran-dungeon-as-horde-in-wow-forever-383256)
and [firsthand quest reports](https://www.wowhead.com/forever/quest=92434/blood-in-the-streets)
identify Wordeen's prior work; a [Patrols report](https://www.wowhead.com/forever/quest=545/dalaran-patrols)
explicitly identifies Key to the City as a prerequisite.

A local additional requirement for 545 requires 93680 turned in, preserving the
native 544 requirement. 92434 requires both 545 and 93680 turned in. Acceptance
or objective completion does not suffice. Bel'varil's separate Stone Tokens and
Bracers of Binding are not required. No Grimy Key inventory gate is added: it is
provided by the quest. Existing downstream 92434 -> 96984 -> 97287 corrections
are preserved. Both maps, confirmed offers, broad mode and Horde race checks
are covered; provider-owned rows are unchanged.

## Native prerequisite precedence (0.4.7; QuestieDB 1.1.0)

The provider now encodes all 25 local correction records. Historical overrides
are fallbacks for empty native prerequisite fields, with the exact older Patrols
{544} expression retaining its supplemental key gate. Native AND/OR expressions
win as soon as they are supplied. This avoids applying an Alliance-only or
Horde-only historical predecessor on top of a newer list of alternatives.
The current native Patrols AND list covers Prison Break In and Key to the City;
Blood in the Streets requires completed Patrols. A completed predecessor is
sufficient without re-evaluating its own historical prerequisites. QuestLite does
not mutate shared rows or recursively invent additional restrictions.

## Powderfuse introductions and prerequisite guidance (0.4.16)

Smuggler's Paradise (95288) has no predecessor fields in the installed provider,
while both The Goblin Trader (93976, Horde) and A Few Furs for Friz (94928,
Alliance) have explicit forward links to it. The user's negative offer report
exposed this gap. The primary
[AllTheThings Riverglades data](https://github.com/DFortun81/AllTheThings/blob/master/.contrib/.db/forever/zones/eastern%20kingdoms/riverglades.lua)
explicitly lists both source quests and records their respective faction branches.
They are modeled as alternatives; requiring both would block both factions.

Added a missing-native-data OR fallback for 95288, requiring either introduction
turned in. Three explicit single-predecessor source links in that same primary
data are also filled only when native requirements are empty:
93976 <- 93788 (Borrowed Blades), 94928 <- 94925 (A Fur Trade), and
95293 (Smuggler's Special) <- 95288. No unrelated Riverglades sequence, reputation
threshold or item-inventory condition is inferred. Broad mode keeps browsing
behavior, while strict confirmed offers retain the verified mandatory checks.

The references agree on Powderfuse Port: provider coordinates 77.1,52.9 versus
primary-source 77.0,52.8. Coordinates are not moved. An entirely absent NPC is not
explained by these data alone; spawn/phasing would still need live confirmation.
The provider's missing minimum-level field is not silently replaced from a guide.

New `/ql prereq <ID or exact name>` and Shift details show known missing turn-in
steps, with faction/class filtering of alternative branches, pickup/return NPCs
and known locations. Shared prerequisite selection preserves native precedence
and OR versus AND semantics. Completed exclusive alternatives satisfy native
positive groups consistently. Output is bounded to four links and ten quest rows,
with visited-ID cycle protection; no graph/name index is retained. Parent-quest
activation, breadcrumbs, professions and other server conditions are not relabeled
as mandatory turn-ins. Lookup is on demand and names are read in the client locale.

Validation: 107 offline regressions plus both installed-provider profiles. Cases
cover both faction routes, acceptance versus turn-in, newer native AND lists,
map/minimap visibility, active turn-in guidance, completed-step suppression, exact
name lookup, cycles/depth bounds, and the actual Friz pickup at its native location.
The comparison audit now records fallback mode (all/any) explicitly.

## Step One: Rock / ogre introduction (0.4.17)

**Corrected in 0.4.21:** the introduction-only gate below was incomplete.
The user's Forever client screenshot shows Land of Giants turned in, Might Makes
Right (95424) and Unworthy Champion (95425) accepted, but Step One: Rock still
unavailable. A firsthand comment by BabyJ on the linked quest page explicitly
identifies completing Might Makes Right as the unlock. The missing-native fallback
is now 95183 <- 95424, with native 95424 <- 95420 retained. Guidance therefore
follows Land of Giants -> Might Makes Right -> Step One: Rock. Accepting the
combat quest or finishing its objectives is insufficient: wait for turn-in.
Unworthy Champion, reputation and higher level are not added as speculative gates.
Native prerequisite data still takes precedence when supplied.

Client smoke record, 2026-11-18: user screenshot on the Forever client confirms
the old false pickup after the introduction turn-in (level 45 Horde Skyborne
Hunter; Gorgegut marker 69.7,25.9). New-policy client retest is pending: reload
0.4.21 with Might Makes Right active, verify no pickup on either map, then turn
it in to Clugfist and check the actual offer at Hamur/Gorgegut. Offline regressions
cover both maps and those state transitions; they do not prove the live unlock.

Both screenshot markers are quest 95183 (Step One: Rock), recorded at Hamur
263440 and Gorgegut 259988. The provider has no predecessor or reputation gate
for it. A firsthand report on
[Step One: Rock](https://www.wowhead.com/forever/quest=95183/step-one-rock)
explicitly identifies Land of Giants (95420) as the ogre-quest introduction. The
user confirmed it had not been turned in. Added 95183 <- 95420 as a missing-native
fallback; acceptance or objective completion alone does not unlock the pickups.
The native prerequisite for Step Two: More Rock (96026 <- 95183) remains unchanged.

The gate is scoped to this verified pickup, not every ogre NPC or Bolder'ok quest.
No Friendly reputation, mining/blacksmithing requirement, Clugfist's Decree gate
or additional chain sequence is inferred. The recorded giver coordinates are not
moved or removed; neither giver was observed after the introduction. Genuine
server offers still use the established strict mandatory-chain rules.

`/ql prereq Step One: Rock` follows known missing prerequisites and shows pickup
locations; an accepted Land of Giants points to Clugfist for turn-in. The bounded
route uses the provider's existing earlier links. Native prerequisite data takes
precedence when added later. Broad browsing and ready turn-ins retain behavior.
Validation: 108 offline regressions plus both installed-provider profiles, covering
both source markers, before/after turn-in, active objective-complete introduction,
new native prerequisite precedence, ready turn-ins and actual prerequisite guidance.
