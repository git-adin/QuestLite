# Moonsilver Blade Paladin prerequisite corrections — 0.3.3

The installed Forever QuestieDB marks this chain with requiredClasses=2 (Paladin)
and requiredRaces=16 (Undead), but omits its prerequisite links. Correct class/race
flags alone therefore advertised future steps as available to an Undead Paladin.

The local strict pickup policy now requires each preceding quest turned in:

| Order | Quest | ID | Required predecessor |
| --- | --- | ---: | ---: |
| 1 | Diplomatic Incident | 91858 | Existing provider requirements only |
| 2 | A Curious Pair | 91859 | 91858 |
| 3 | A Grim Fate | 91860 | 91859 |
| 4 | Into Fenris Keep | 91861 | 91860 |
| 5 | Lumina Windsinger | 91862 | 91861 |
| 6 | The Windshaper's Wrath | 96204 | 91862 |
| 7 | The Debt | 95034 | 96204 |
| 8 | A Moon-Kissed Blade | 95036 | 95034 |
| 9 | An Underrated Talent | 95111 | 95036 |
| 10 | Ott's Masterwork | 95125 | 95111 |
| 11 | The Moonsilver Blade | 95126 | 95125 |
| 12 | Old Fire-Eye | 95140 | 95126 |

These are pickup restrictions shared by world map and minimap. Accepting a
predecessor or completing its objectives is insufficient until its turn-in is
recorded. Confirmed-offer observations cannot bypass the chain. Ready turn-ins
and unrelated quests remain visible. The broad/unfiltered view deliberately
continues to permit browsing future steps; its race/class checks still apply.
No item granted by one of these quests is treated as a pre-acceptance requirement.
Provider data and native class/race masks are not modified.

Evidence:

- [The Debt's full quest series](https://www.wowhead.com/forever/quest=95034/the-debt)
  lists steps 1–11 in order.
- [Ott's Masterwork](https://www.wowhead.com/forever/quest=95125/otts-masterwork)
  independently lists the same sequence and describes the forging step.
- [The Moonsilver Blade](https://www.wowhead.com/forever/quest=95126/the-moonsilver-blade)
  lists the sequence and its completion directs the player to Lumina for the last
  step. Its firsthand comments explicitly identify Old Fire-Eye as the next quest.
- [Old Fire-Eye](https://www.wowhead.com/forever/quest=95140/old-fire-eye)
  requires the finished blade and its description acknowledges that the player
  already has the weapon.

Validation walks every transition on both maps before acceptance, at objective
completion, and after turn-in. The real provider's eleven relationships are also
tested for the Undead Paladin profile and checked for race/class preservation.
