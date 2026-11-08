# Item-related pickup audit — 0.2.13

Searched all 5,233 quests in the installed Forever QuestieDB, including 1,184
quests with a nonzero sourceItemId. The reproducible search is
`tools/audit_item_gates.py PATH_TO_QUESTIEDB` in the development workspace; its
full review data is written to `dist/item-gate-audit.json`. The search also reads
every item's startQuest relation and checks NPC/object quests lacking explicit
requiredSourceItems. Candidate matches are leads, not automatic requirements.

## Verified prerequisites

The table verifies eight links. After the user's update to QuestieDB 1.0.13,
The Tortured Soul and The Offering of Blood have native preQuestSingle links,
so no local overrides are retained for those two. The other six still have no
native prerequisite entry and use local corrections.

| Follow-up | Required quest turned in | Evidence |
| --- | --- | --- |
| Earthen Echo (98823) | Elder Knowledge (95664) | [Quest series and firsthand reports](https://www.wowhead.com/forever/quest=98823/earthen-echo) |
| Prehistoric Prism (98824) | Lost Relic Carry (95810) | [Quest series and firsthand reports](https://www.wowhead.com/forever/quest=98824/prehistoric-prism) |
| The Tortured Soul (95883) | The Offering Stone (95884) | [Quest series](https://www.wowhead.com/forever/quest=95883/the-tortured-soul) |
| The Offering of Blood (95885) | The Tortured Soul (95883) | [Quest series](https://www.wowhead.com/forever/quest=95885/the-offering-of-blood) |
| Heart of Disruption, Alliance (92458) | An Alarming Request (92432) | [Quest series and firsthand access report](https://www.wowhead.com/forever/quest=92458/heart-of-disruption) |
| Friend of the Kirin Tor (92459) | Heart of Disruption (92458) | [Quest series](https://www.wowhead.com/forever/quest=92459/friend-of-the-kirin-tor) |
| Heart of Disruption, Horde (96984) | Blood in the Streets (92434) | [Quest series](https://www.wowhead.com/forever/quest=96984/heart-of-disruption) |
| Shrewd Negotiations (97287) | Heart of Disruption (96984) | [Quest series](https://www.wowhead.com/forever/quest=97287/shrewd-negotiations) |

These native requirements and local corrections apply to the shared strict availability predicate used
by world-map and minimap pickups. Objective completion or a predicted NPC offer
does not substitute for prerequisite turn-in. The broad/unfiltered option remains
available. Active turn-ins remain independent of pickup eligibility. The provider
is not modified and no new full database index is loaded by the addon.

## Correction to the previous Earthen Echo workaround

Version 0.2.12 required Titan Relic 287958 in the bags. Further verification showed
that this is the copy provided when Earthen Echo is accepted, not its dropped
starter. Titan Relic 270866 starts Elder Knowledge; the Alliance item 270865 starts
Lost Relic Carry. Both first steps must be turned in before their follow-ups.
Requiring the provided copies would wrongly hide unlocked follow-ups. Version
0.2.13 removes that inventory gate and tests unlocking with no provided relic held.

## Candidates deliberately not converted into inventory gates

The local data contains six mixed starter cases: Warlord's Command (4903), The
Ancient Leaf (7632), Azuregos's Magical Ledger (8575), Grant's Shield (79362),
Silvia's Sword (79363), and Ira's Dagger (96137). Their item records can start a
quest, but this alone does not prove the NPC alternative unavailable. For example,
[firsthand Ira's Dagger reports](https://www.wowhead.com/forever/quest=96137/iras-dagger)
describe both a dropped dagger and a beta NPC offering the quest. No blanket
inventory restriction was added to these cases. Existing actual-NPC offer-list
filtering remains available.

Most source items are ordinary provided tools or delivery packages. Examples
include Field Testing Kit, Snufflenose Command Stick, and the Arcane Mote supplied
for Friend of the Kirin Tor. A drop source or a "bring this item" objective does
not, by itself, prove that the item is needed before accepting a quest.

## Validation

Regression checks exercise all eight corrected links before acceptance, after
objective completion but before turn-in, and after turn-in. Confirmed offers
cannot skip those prerequisites. The real installed metadata is checked for all
eight relationships, and Earthen Echo is exercised through actual giver locations
without requiring its provided relic. No universal claim is made for unrecorded
server-only conditions; remaining ambiguous candidates require further evidence.
