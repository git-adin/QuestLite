# Event coverage audit - 0.3.0

Checked against the installed Questie v12.6.4 and QuestieDB Forever v1.0.13.
Counts overlap across lists and database categories; they are not additive.

## Separate event lists

| Group | IDs present in Forever |
| --- | ---: |
| AQ War Effort / commendations | 109 |
| Scourge Invasion list | 29 |

## All holiday registration files

| Registration file | IDs present in Forever |
| --- | ---: |
| Brewfest | 0 |
| ChildrensWeek | 14 |
| DarkmoonFaire | 46 |
| DayOfTheDead | 0 |
| HallowsEnd | 15 |
| HarvestFestival | 2 |
| LoveIsInTheAir | 21 |
| LunarFestival | 70 |
| Midsummer | 16 |
| Noblegarden | 0 |
| PilgrimsBounty | 0 |
| WinterVeil | 31 |

## Database categories checked independently

| Category | Tagged quests | Uncovered after generation |
| --- | ---: | ---: |
| WINTER_VEIL | 0 | 0 |
| HARVEST_FESTIVAL | 0 | 0 |
| CHILDRENS_WEEK | 0 | 0 |
| LOVE_IS_IN_THE_AIR | 0 | 0 |
| PILGRIMS_BOUNTY | 0 | 0 |
| NOBLEGARDEN | 0 | 0 |
| BREWFEST | 0 | 0 |
| MIDSUMMER | 16 | 0 |
| LUNAR_FESTIVAL | 72 | 0 |
| DARKMOON_FAIRE | 44 | 0 |
| DAY_OF_THE_DEAD | 0 | 0 |
| SEASONAL | 69 | 0 |
| HALLOWS_END | 0 | 0 |
| INVASION | 31 | 0 |
| AHN_QIRAJ_WAR | 76 | 0 |

## Previously missed category entries

The database-category pass additionally found IDs: 98471, 98977, 98983.
The composed-database check identifies 98977 (Mossheart the Elder),
98983 (Frostleaf the Elder), and 98471 (Message from the Supreme Magister).

## Ongoing safeguards and limits

- Generation fails if Questie adds an unreviewed separate event Quests table, or QuestieDB adds a holiday category in its holiday enum section.
- Holiday files are discovered automatically, including files whose quests are absent from Forever.
- Runtime filtering checks the composed quest category too, covering new quests in reviewed event categories after a DB update.
- Persistent battlegrounds, class/profession sorts, raid zones, and ordinary campaigns are not treated as temporary holidays.
- Anniversary and Pirates Day appear in reference comments, but have no separate registered quest list in this installed version. Categorized seasonal entries remain covered.
- No SoD-only Blackrock Eruption or Nightmare Incursion quest categories occur in the installed Forever data; their realm-specific phase assumptions are not imported.
- This verifies all event groups found in these local references and metadata, not unknown server-only events with no IDs or event tags.
- Strict mode still requires a current NPC offer for event pickups. Automatic calendar/realm activation is not implemented; use the broad view to browse events beforehand.
