# QuestLite 0.4.23

The install ZIP includes the game files, player documentation, and required notices. The development audits are available in the source repository.

Download **QuestLite.zip** below and extract it into your WoW Forever
`_forever_/Interface/AddOns/` folder. The result should be
`AddOns/QuestLite/QuestLite.toc`.

Fixed in 0.4.23: item tooltips no longer add an empty drop-chance heading and
unknown-data message when there is no usable NPC drop estimate. Known source
rates and inline creature percentages are preserved.
The bundled policy was also refreshed against QuestieDB Forever 1.1.5.

Updated in 0.4.22: refreshed availability data against Questie 12.11.1 and
QuestieDB 1.1.3: eight additional hidden/conditional IDs and 22 PvP tag corrections,
including the newly supplied Darkspear variants. Native reputation, race,
prerequisite and location fixes are consumed automatically. Verified the Neutral
Buying Friendship threshold, Raene's Cleansing chain and Tauren-only Earthmother
quests. Reviewed ForeverDB 0.67.0; no speculative prerequisites or level gates added.

Also in 0.4.22: Step One: Rock now waits for Might Makes Right to be turned
in, rather than appearing immediately after Land of Giants. The prerequisite
guide follows both steps and shows Clugfist's pickup/return location. Native
provider prerequisites retain precedence; ready turn-ins and broad browsing
keep their existing behavior.

New in 0.4.20: the three Find OOX beacon quests and Pendant of Myzrael show
their turn-in destination on both maps instead of scattered drop-source areas.
Tooltips explain that the dropped item is required first. These remain item-quest
references, with normal eligibility and hiding filters; accepted, ready quests
still use normal turn-in markers. The existing item-drop setting is now labelled
**Show item-started quests** and also controls these destination references.

Fixed in 0.4.19: Betrayed (3504) no longer advertises a pickup in strict mode
without a current NPC offer. Its listed minimum remains 44 and its quest level
remains 53; the actual missing availability condition on Forever is unverified.
The quest guide and expanded details now distinguish those two levels. Broad
browsing and ready turn-ins remain available.

New in 0.4.18: a dedicated QuestLite window with **Map**, **Filters** and
**Prerequisites** tabs. Open it with `/ql` or either map button. Search part of a
quest name or paste a link; click a map marker to open its prerequisite guide.
Grouped markers let you choose a quest. Missing steps show known pickup/return
locations and can be clicked for more details. Right-click hide and Shift-click
quick hide remain available, and existing settings are preserved.

Fixed in 0.4.17: Step One: Rock pickups at Hamur and Gorgegut now wait for
Land of Giants to be turned in. `/ql prereq Step One: Rock` shows the known route
and pickup/return locations. No invented reputation or profession gate is added.
Reviewed ForeverDB 0.64.1 and corrected The Corrupter's observed quest level to 33,
with newer provider values retaining precedence.

New in 0.4.16: `/ql prereq <quest ID or exact name>` and Shift details show known
missing quest turn-ins, with pickup/return NPC locations and faction-appropriate
branches. Smuggler's Paradise now waits for either faction introduction to be
turned in; verified introduction links and Smuggler's Special are also corrected
when absent from native data. No NPC coordinates are moved.

Fixed in 0.4.15: **Hide PvP quest pickups** now also catches all eighteen known
Darkspear Islands mark-turn-in and battleground-victory variants, including the
Horde Warbringer's Conflict at Darkspear Islands quests and Alliance counterparts.
These records were missing PvP tags. Ready turn-ins remain visible.

New in 0.4.14: **Hide cloth donation pickups** in `/ql`, or `/ql cloth` as a quick
toggle. Covers wool, silk, mageweave and runecloth reputation donations, including
repeatable runecloth and Skyborne donations. Hides pickups on both maps while
preserving ready turn-ins. Saved per character; starts off.

New in 0.4.14: **Hide cloth donation pickups** in `/ql`, with `/ql cloth` as a
quick toggle. Covers wool, silk, mageweave and runecloth reputation donations,
including repeatable runecloth and both Skyborne factions. Saved per character,
starts off, and affects both maps. Ready turn-ins and other cloth quests remain.

Updated for Questie 12.10.0 and QuestieDB 1.1.2 in 0.4.13:
- Added exclusions for the removed Hearts of the Lost chain (three quests).
- Verified native Sulhasa coordinates replace the older fallback automatically.
- Rechecked ForeverDB 0.62.1 and existing character/PvP/hide filters.

Updated for Questie 12.9.0 and QuestieDB 1.1.1 in 0.4.12:
- Added Rekindle to the SoD exclusions, including stale-offer protection.
- Refreshed availability policy and verified PvP tag corrections.
- Rechecked ForeverDB 0.60.5; newer native levels retain precedence over older fixes.
- Verified class/race corrections, quest hiding, drop-source toggles and turn-ins.

New in 0.4.11: **Hide PvP quest pickups** in `/ql`, with `/ql pvp` as a quick
toggle. Uses the game's PvP tag and applicable Questie tag corrections on both
maps. Ready turn-ins remain visible. Saved per character and starts off.

New in 0.4.10: right-click a marker to hide an individual quest pickup on both
maps. Grouped markers list each pickup separately. Shift-left-click quickly hides
a single pickup. The list is saved per character; turn-ins remain visible.
Use `/ql hidden` to restore individual quests, or `/ql unhide all` to reset the
list. The existing item-drop location toggle remains independent.

New in 0.4.9: **Show quest item drop locations** controls possible drop sources
on both maps. Turn it off in `/ql`, or use `/ql drops`, to hide markers such as
Pendant of Myzrael. It starts enabled and is saved per character. NPC pickups,
ready turn-ins and drop-rate tooltips remain visible.

Character-filter fixes (0.4.8):
- Hide Alaana's Call of Air for non-Shamans.
- Restore Compendium of the Fallen for Horde Skyborne; keep Forsaken and Alliance
  excluded and preserve its level 28 minimum.
- Repair four additional missing class masks in Mage/Druid training quests.
- Corrections yield to newer native masks. Broad browsing and confirmed offers
  cannot bypass the repaired class/race restrictions.
- Reviewed ForeverDB 0.59.0 and added a full installed-data character-mask sweep.

Updated for Questie 12.8.0 and QuestieDB 1.1.0:
- Native prerequisite expressions take precedence over historical local patches,
  preserving the new Dalaran alternatives and complete AND requirements.
- Historical patches remain fallbacks for older database versions.
- Refreshed nine exclusion-table entries, including SoD PvP quests and two more
  Sealed Crate variants; added explicit SoD labels for the PvP pair.
- Verified new Paladin race masks and the hotfixed Herbalism turn-in location.

Updated for Questie 12.7.0, QuestieDB 1.0.15 and ForeverDB 0.58.2:
- Refreshed quest exclusions (26 additional hidden/conditional IDs).
- Missing minimum pickup levels now fall back to quest level, matching Questie;
  confirmed NPC offers still take precedence.
- Corrected the observed levels of Silvia's Sword, Never Coming Back, A Void Path
  and Vengeful Trail, with newer provider data retaining precedence.
- Updated the offline ForeverDB comparison for its new faction-hint field.

Blood in the Streets now waits for Dalaran Patrols and Key to the City turn-ins;
Patrols also requires the missing key-quest turn-in alongside its native Prison
Break In requirement. QuestieDB 1.0.14 compatibility and holiday policy refreshed.

Goblin Lockpicks at Veenix now respects its missing Rogue class restriction,
removing the false pickup marker for Hunters and other classes.

World-map pin creation and release now wait until combat ends, fixing the
recorded QuestLite `Frame:SetPassThroughButtons()` combat block. Minimap markers
continue. `/ql taint` provides a read-only action-bar ownership snapshot; no
Blizzard cooldown code is replaced or suppressed. The separate secret-value
`SetCooldown` error still needs live source attribution.

Compared ForeverDB 0.57.16 with QuestieDB: corrected 14 observed fixed quest levels,
restored Sulhasa's missing Field to Clear location, and routed Horde library
turn-ins to Owen Thadd. Native provider updates take precedence over stale fixes.
Data from ForeverDB.net (https://foreverdb.net); see the included audit and licence.

Walton's Trouble in the Valley waits for The Hermit Tanner turn-in, and Unwelcome
Guests waits for Trouble in the Valley. These correct missing prerequisite fields.

**0.4.0 removes the custom soft-target sparkles** for herbs, ore, corpses and
interactable objects. This follows Forever Loot Sparkles 2.0.0's removal of the
mechanism associated with redirected friendly spells, empty corpse nameplates
and interaction icons. Built-in quest-loot sparkles remain enabled.

On first login, QuestLite restores its saved legacy interaction settings outside
combat, preserving detectable later player changes. Reload after updating and
let the five-second migration finish; in combat it waits until combat ends.

Elayaa's Skyborne Hunter quest remains visible after taming training, matching
live-server availability. No breadcrumb restriction is inferred from its text.

Skyborne-restricted quests now use QuestieDB's actual race-ID mapping (95/96).
This restores missing Hunter trainer pickups and other eligible Skyborne quests,
while retaining class, faction, level and prerequisite checks.

Item-drop starters now use at most three representative world-map markers per
quest per zone, avoiding dense spawn-marker clutter. The minimap shows one nearby
source per drop quest, keeping its anchor while visible to avoid jitter. Tooltips
distinguish **Item drop** from a quest-giver pickup.

Also install the **Forever** version of
[QuestieDB](https://www.curseforge.com/wow/addons/questiedb/files/all), then restart
WoW and enable both QuestLite and QuestieDB in the AddOns list. Use `/ql` for options.
Disable Questie and Forever Loot Sparkles when using QuestLite to avoid duplicate
markers and competing sparkle settings.

For updates, replace the existing `QuestLite` folder; your character settings are
stored separately in `WTF` and are preserved. GitHub's **Source code** archives
are for development; use the attached addon ZIP for installation.

A draggable gold **!** minimap button opens QuestLite options. Its position is
saved per character, and it can be hidden independently of quest markers.
The main world map now also has a gold **!** options button at the upper left,
alongside other map controls.

Scout Support now waits for the Battle of Hillsbrad part II turn-in, and Valuable
Vantages waits for Scout Support. These fill missing database prerequisite links.

Repeatable quests use blue pickup and turn-in icons on both maps, with a
**Repeatable** tooltip label. Mixed groups keep a yellow icon when their displayed
quest type also includes regular quests. Quest titles retain level-based colours.

This release also includes the availability, class/faction and Paladin chain
corrections, plus a recorder for diagnosing blocked interface actions (`/ql errors`).
The protected-action warning remains under investigation. Offline Lua tests run
before packaging; they do not reproduce the game's protected execution or renderer.
