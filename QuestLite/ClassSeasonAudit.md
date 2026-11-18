# Screenshot quest classification â€” 0.3.2

| Quest | Correct classification | Pickup handling |
| --- | --- | --- |
| Dragonslayer's Helm (78132) | Season of Discovery, Warrior rune chain | Hidden in the strict Forever view. Wrong-class characters cannot see it even in broad mode. A Warrior browsing broad candidates sees the explicit season/class label. |
| Dragonslayer's Shield (78133) | Same | Same |
| Dragonslayer's Lance (78134) | Same | Same |
| Never Coming Back (98251) | Forever, Horde; no recorded class restriction | Retains the provider's Horde race mask, level and ordinary requirements. Not hidden merely because its giver is a Warlock. |
| A Void Path (98252) | Forever, Horde; follows Never Coming Back | Requires 98251 turned in in strict mode. Accepting or finishing the objectives of 98251 does not unlock it. |

The installed QuestieDB 1.0.13 reports requiredClasses=0 for all five entries and
omits the 98251 -> 98252 prerequisite. Consumer-side corrections do not mutate it.
No blanket high-ID range blacklist or guessed Warlock restriction is applied.
Mandatory provider race/class masks are checked before the confirmed-offer shortcut,
so confirmation cannot bypass faction or class eligibility. Broad mode also keeps
these masks. The mask for both Va'xug quests includes Horde races 2, 5, 6, 8 and 34;
Alliance race 1 is rejected. Arithmetic bit checks preserve the high race-ID bits.
Active quest turn-ins are unaffected by these pickup-only rules. Existing live
NPC offer-list filtering still applies to Never Coming Back when a giver is checked.

Evidence:

- [Wowhead's SoD Warrior Raging Blow guide](https://www.wowhead.com/classic/guide/season-of-discovery/classes/warrior/raging-blow-rune)
  identifies the three Dragonslayer turn-ins and Alonso's rune chain.
- [Alonso the Dragonslayer](https://www.wowhead.com/classic/quest=78144/alonso-the-dragonslayer)
  is explicitly Warrior and added in Season of Discovery. The final quest is not
  advertised by Alonso in this installed Forever dataset; only the three listed
  turn-ins were corrected.
- [Never Coming Back's Forever quest series](https://www.wowhead.com/forever/quest=98251/never-coming-back)
  lists A Void Path as its follow-up. The provider's race/class fields were checked
  independently so an NPC's class is not mistaken for a player-class requirement.

Regression checks cover the screenshots on world map and minimap, Warrior versus
Paladin filtering, explicit offer observations, broad-mode classification labels,
and the prerequisite transition through acceptance, completion and turn-in.

## Goblin Lockpicks at Veenix (0.4.4)

Quest 78270 has requiredClasses=0 in QuestieDB 1.0.13, advertising it to Hunters.
[Wowhead's Forever Rogue class list](https://www.wowhead.com/forever/quests/classes/rogue)
identifies it as Rogue-only. A local requiredClasses=8 correction applies before
confirmed-offer and broad-view shortcuts. Eligible Rogue pickups remain visible;
no race, mandatory prior quest or unsupported-season restriction is invented.
The quest has Season of Discovery origins, but it is also listed as a Rogue
quest in Forever alongside The Horn of Xelthos. Numeric IDs/origins alone do not
justify hiding it for Rogues. Provider data is unchanged. Regression coverage
checks both maps, confirmed observations, broad mode and both factions.

## Questie 12.8.0 additions (0.4.7)

Repelling Invaders (79090) and Clear the Forest! (79098) are explicitly excluded
from Forever by the upstream non-SoD policy. QuestLite labels both as Season of
Discovery and blocks them in strict mode even with stale offer observations,
matching its existing Dragonslayer policy. No class restriction is inferred for
these PvP quests. Native race masks still apply in broad mode.

## Character mask audit (0.4.8, 2026-11-13)

Reviewed all 5,893 installed QuestieDB 1.1.0 quest records. The character-mask
checks already run before confirmed-offer and broad-mode shortcuts. The reported
false pickup and missing quest were missing/stale provider masks, not reversed
class bits or a general faction-mask calculation failure.

| Quest | ID | Old provider value | Guarded correction |
| --- | ---: | --- | --- |
| Call of Air, Alaana Stormwalker | 96136 | requiredClasses=0 | Shaman (64) |
| Boughs in the Wind | 93797 | requiredClasses=0 | Mage (128) |
| The Great Windborne Cat Spirit | 98341 | requiredClasses=0 | Druid (1024) |
| The Great Windborne Cat Spirit | 98404 | requiredClasses=0 | Druid (1024) |
| Blessings of the Great Windborne Cat Spirit | 98738 | requiredClasses=0 | Druid (1024) |
| Compendium of the Fallen | 1049 | requiredRaces=162 | 8589934754: adds only Horde Skyborne |

The class records are corroborated by their native class categories and quest
content. [Call of Air](https://www.wowhead.com/forever/quest=96136/call-of-air)
awards the air totem. [Boughs in the Wind](https://www.wowhead.com/forever/quest=93797/boughs-in-the-wind)
describes the Mage spell-focus training, while the
[Windborne Cat Spirit](https://www.wowhead.com/forever/quest=98341/the-great-windborne-cat-spirit)
and [blessing](https://www.wowhead.com/forever/quest=98738/blessings-of-the-great-windborne-cat-spirit)
are the Druid cat-form chain. Only class masks are repaired; native faction/race,
level and prerequisite requirements remain in force. No new chain link is inferred.

[Compendium of the Fallen](https://www.wowhead.com/forever/quest=1049/compendium-of-the-fallen)
has a firsthand Forever report of successful Skyborne completion and a missing
Questie marker. It also documents the Forsaken exclusion. The old mask already
permits Orc, Tauren and Troll; the correction adds race ID 96's mapped bit without
adding Forsaken (5) or Alliance Skyborne (95). The actual Thunder Bluff pickup
at Sage Truthseeker, 34.4,46.87, now emits for an eligible Horde Skyborne Hunter.
The native minimum level 28 is preserved. Ready turn-ins remain independent of
pickup filtering.

All six field corrections apply only while the raw native field equals the
recorded old value. New provider values take precedence, even if they differ
from our correction. Shared QuestieDB tables and caches are not modified.

### Exceptions and limits

The six zero-class-mask entries in known class categories include Junkboxes
Needed (8249), a general Ravenholdt turn-in, which remains open to other classes.
A Scribbled Letter (92479) has a Warrior category but an explicit native Hunter
mask; its native restriction is preserved. These cases rule out blindly deriving
a class restriction from every category, quest name or trainer NPC.

Eight records have the old non-Forsaken Horde mask 162. Only Compendium has the
corroborated Skyborne correction. Stalk With The Earthmother includes a firsthand
[report of no Skyborne offer](https://www.wowhead.com/forever/quest=76156/stalk-with-the-earthmother),
so that mask is not globally expanded. Other restricted Shaman-chain masks are
retained pending specific evidence; faction subsets are not automatically treated
as incomplete faction-wide masks.

Validation: 95 offline regressions plus both real-provider profiles. The full
provider sweep performs 59,254 wrong-class/race rejection checks across nine
class IDs and ten race IDs, with strict/broad modes and confirmed offers. Positive
cases cover the screenshot pickups, intended classes, low-level behavior, both
maps, ready turn-ins, and future native-mask precedence. These are offline checks,
not a claim that every server-only condition can be known before visiting an NPC.

## Rekindle (0.4.12)

Questie 12.9.0 explicitly excludes Rekindle (80001) outside Season of Discovery.
The regenerated policy includes the ID, and the explicit season restriction
prevents a stale confirmed offer from restoring it in strict mode. Broad mode
retains the Season of Discovery label. Its missing native class mask is not
filled by guessing a class from the title; existing native race requirements
remain in force. The season regression now covers this record as well.
