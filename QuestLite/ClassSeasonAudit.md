# Screenshot quest classification — 0.3.2

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
