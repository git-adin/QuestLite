# Availability policy audit - 0.3.2

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
