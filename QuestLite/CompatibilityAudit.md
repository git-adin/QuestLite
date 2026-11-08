# Updated reference addon verification — 0.2.13

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
