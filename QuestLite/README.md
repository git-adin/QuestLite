# QuestLite 0.3.9

A focused quest map and loot visibility addon for World of Warcraft: Forever
(Interface 16001). Requires **QuestieDB**. Questie and QuestieTrace are optional.

## Install and use

Download **[QuestLite.zip](https://github.com/git-adin/QuestLite/releases/latest/download/QuestLite.zip)**
and extract it into `_forever_/Interface/AddOns/`. Install the **Forever** build of
**[QuestieDB](https://www.curseforge.com/wow/addons/questiedb/files/all)** separately.
The installed file should be `AddOns/QuestLite/QuestLite.toc`. Use the release ZIP,
not GitHub's source-code archive. Updates replace only the `QuestLite` folder;
settings in `WTF` are preserved.

Previously named ForeverGuide. The addon folder is now `QuestLite`, and the
primary commands are `/ql` and `/questlite`. `/fg` and `/foreverguide` remain
aliases. Keep only QuestLite enabled to avoid running both versions.

To migrate existing settings manually, close WoW and copy each character's
`WTF/Account/<account>/<realm>/<character>/SavedVariables/ForeverGuide.lua` to
`QuestLite.lua` in the same directory before first launching QuestLite. Preserve
an existing QuestLite.lua instead of overwriting it. QuestLite imports the legacy
settings once, including saved original sparkle CVars, and subsequently saves
them as QuestLiteDB. Keep the original files as backups.

If the AddOn List reports interface actions failing because of QuestLite, use
`/ql errors` after the warning occurs. The addon records the last ten blocked or
forbidden function names, combat state, a bounded stack, and any synchronous
QuestLite CVar call. Records persist across reloads. `/ql errors clear` clears
only this diagnostic history; it does not hide or reset Blizzard's warnings.
The recorder is event-driven and adds no polling or full error-handler hooks.
These records identify the blocked action and context, not necessarily the
original source of taint. This diagnostic update does not claim to fix an
unidentified protected-action failure.

1. Place the `QuestLite` folder in `_forever_/Interface/AddOns/`.
2. Keep QuestieDB enabled. Disable Questie and ForeverLootSparkles on the character
   using QuestLite, to avoid duplicate markers and competing sparkle settings.
3. Restart the client if this is a newly added folder. Enable QuestLite in the
   character selection AddOns list.
4. Open a **continent or zone map**, then hover a marker to see nearby quests
   grouped by quest giver. Continent tooltips also show the source zone. Hold Shift for
   objective text and coordinates; the tooltip opens at the cursor.
5. Use `/ql` or Esc > Options > AddOns > QuestLite for options.

A gold **!** button around the minimap also opens options. Drag it around the
edge to reposition it; its position is saved per character. **Show QuestLite
minimap button** in `/ql` hides it independently of quest markers.
The main world map has its own gold **!** options button at the upper left,
joining the shared map-button stack when Questie/RareScanner provides it.
It remains accessible when quest markers or the minimap button are disabled.

Map and sparkle features start enabled; Show low level quests starts off.
Preferences and original soft-target CVar values are
saved per character.

### Availability filter

The normal pickup cutoff defaults to 5 levels below your character. At level 22
this includes quest levels 17 and above, subject to pickup requirements. There is
no extra upper-level cutoff. Adjust **Normal level limit (levels below mine)**
in `/ql`. Turn **Show low level quests** on to show all available low-level
quests, bypassing that cutoff; it defaults to off.
This applies to continent, zone and minimap pickups. Ready turn-ins remain visible
at any level. Quests with unknown or scaling levels remain visible. Leveling up
automatically refreshes the threshold. `/ql status` reports the minimum level.

In `/ql`, **Hide unavailable quest pickups** is on by default. It applies known
level, chain, class/race, profession rank/specialization, reputation, spell and required-item
restrictions, removes obsolete breadcrumbs and auto-reward entries, and skips
wrong-faction NPC givers. Quest item drops from hostile creatures remain valid
sources.

It also applies a compact Forever-compatible display policy for hidden,
unobtainable and conditional quests, including the library catalog, Scourge
Invasion, and AQ War Effort supply/commendation quests. Explicit NPC offers can restore these entries. See
[AvailabilityAudit.md](AvailabilityAudit.md) for the audit, provenance and limits.
The event-specific sweep is recorded in [EventCoverage.md](EventCoverage.md).
Known Season of Discovery leftovers are excluded in the normal Forever view and
carry season/class labels for eligible characters browsing unfiltered candidates.
Race/class masks still apply to confirmed NPC offers and broad mode. See
[ClassSeasonAudit.md](ClassSeasonAudit.md) for the screenshot-specific corrections.
Known event categories are checked at runtime as well as by imported quest IDs.

After you talk to an NPC using a gossip or quest-greeting list, the filter also hides quests
absent from that NPC's server-provided list. These observations are kept only for
the session, for at most 64 NPCs, and apply only to that giver. Character changes
invalidate them; `/ql refresh` clears them. A single quest-detail dialog is not
treated as a complete offer list.

Tooltips label database predictions **Pickup**, the broad view **Unfiltered**,
and only server-confirmed offers **Available**.
Known chain prerequisites are checked even for confirmed NPC offers. Accepting a
prerequisite or finishing its objectives does not count as turning it in. Parent
quests and explicit active-or-complete unlock conditions keep their documented
semantics. Both maps refresh when the chain advances.
Local corrections fill verified missing database links for Mankrik, the Titan
Relic follow-ups, and the Dalaran chains. They do not alter QuestieDB's shared
data. [ItemGateAudit.md](ItemGateAudit.md) records the item-related review and
distinguishes native provider requirements from our corrections.

Turn the checkbox off to also see locked or higher-level database candidates.
Completed, active, wrong-race and wrong-class quests remain hidden. Turn-in
markers and sparkles are unaffected. Changing the checkbox refreshes the map.

The filter estimates distant quest availability from known data; it cannot
guarantee server-only conditions before you visit the giver. Conditional holiday
and event pickups require an NPC offer in strict mode; use the broader view to
browse them before visiting. Calendar activation is not implemented.

## Included

- Quest pickup markers, including low level quests; known level, race, class,
  prerequisite, exclusive quest, parent quest, basic skill, learned spell and
  reputation restrictions are checked against the character.
- Objective markers are left to Blizzard's built-in map display.
- Completed quest turn-in locations.
- Nearby minimap pickup and turn-in icons, with quest-giver hover lists and Shift
  details. **Show minimap quest icons** in `/ql` switches these on/off independently
  of the world map. The availability and pickup/turn-in settings apply to both.
- Dungeon entrance markers on outdoor maps, labeled as entrances, for locations
  inside known instances. Valid local coordinates can also appear on their
  database-mapped dungeon map.
- Compact, unboxed quest pickup and turn-in icons. A count identifies markers
  containing several quests.
- Item-drop starters use at most three representative source-area markers per
  quest per zone on the world map, instead of marking every possible creature
  spawn. Hover labels them **Item drop**; Shift explains the starter requirement.
  The minimap shows one in-range source per item-drop quest and retains that
  anchor while it remains visible, reducing clutter and movement jitter. Ordinary givers and turn-ins keep
  their normal locations. Representative markers use real source coordinates;
  they do not show every possible place the starter can drop.
- Repeatable quests use blue pickup/turn-in icons and a **Repeatable** tooltip
  label. Quest titles keep their level-based colours. Mixed groups stay yellow
  when their displayed pickup/turn-in type also contains a regular quest.
- Hover details: title, quest level, required level, objective text or
  current progress, target name, and a source coordinate. This is objective
  information, not the full narrative/reward text of the quest dialog.
- The client's quest loot sparkle setting is maintained across graphics changes.
- Extra glints for nearby quest objects, herbs, ore, lootable corpses, and other
  objects identified by the interaction cursor, such as chests or doors.

There is no replacement tracker, journey history, communications, routing system,
or bundled copy of the quest database. Objective markers remain Blizzard's.

## Performance design

### Quest item drop chances

**Show quest item drop chances** is enabled by default in `/ql`. Hover a creature
to see known drop percentages beside item names in native quest progress rows,
for example `5/5 Plainstrider Kidney (40%)`. Each party member's matching progress
row is annotated; no separate section is added to creature tooltips. Hover
one of those items in a bag or item link tooltip to see rates by NPC source (up to
eight displayed sources). Required source items are included. Quest acceptance,
abandonment and turn-in update the list; no objective markers are added.

Rates use QuestieDB's Classic support data: manual Era corrections first, then
quest-only private-server data, then crowdsourced data, including correction
references to a specific source. These are **database estimates**; actual Forever
server rates can differ. Missing data is shown as unknown, including items that
come from objects when no NPC rate is known. Restricted instance creature tooltips
are left to the client.

The addon indexes item-row offsets in existing support strings on first use,
retains at most one row string per source and caches at most 128 item/NPC results.
It neither executes the serialized strings nor expands a full second drop table.

### Map performance

World-map work runs only while a continent or zone map is open. The four most recently used map
snapshots are cached in memory for immediate reopening while character state is
unchanged. A single compact list of eligible quest IDs is reused between zones;
only relevant character changes invalidate it. Objective counter updates do not
trigger a database scan. `/ql refresh` forces a new scan. Native quest events are coalesced;
a running scan finishes before a follow-up scan. Database traversal cooperatively
yields on an approximately 4 ms time budget, with a 2,048-checkpoint safety cap. An individual native decode can
exceed that budget. Work cancels when the map closes or changes zones.

Locations within about one percent of the displayed map share a marker so their hover targets do not pile up. Hover shows
all nearby quests grouped by giver and sorted by level/title, with Shift for
more detail. Same-zone
refreshes reuse marker frames until the new snapshot is ready. The map uses at most 750 pooled
marker frames; additional locations join the nearest marker, with coordinates
and quest details retained. Grouped tooltips identify nearby locations. This bounds frame
growth without discarding quests. A grouped quest shows one source coordinate;
it does not enumerate every spawn of that quest.

Continent views apply the same availability rules in one database pass. Zone
positions are projected with the native `C_Map.GetMapRectOnMap` API after checking
their map ancestry. Unmapped positions are skipped. Hover shows the source zone;
Shift coordinates remain local to that zone. Dungeon quests use outdoor entrances.
The top-level world map remains unsupported.

Database rows read during a scan are individually released through QuestieDB's
public cache API. The bounded map snapshots and eligible-ID list are temporary,
not saved to disk. The addon does not copy the database, build a full spawn index,
flush the entire shared cache, or force garbage collection. QuestieDB itself
still has a substantial baseline memory cost. No memory savings are claimed
until measured in the client with the same addon set and character.

The minimap retains locations for the player's current zone and shares the
eligible-quest list. It rebuilds locations on zone or relevant character changes,
not on movement. Range/group checks run about eight times per second; existing
visible markers move each frame while the player moves or turns, without database
scans or grouping allocations. Stationary markers skip redraws. At most 64 marker
frames are pooled. Zone-anchored cells keep group identity stable through movement,
rotation and zoom. Overflow quest details remain in a visible group. Same-zone
refreshes retain the previous snapshot until the next scan publishes.
No new mapping library is bundled.

Quest markers use the client's `QuestNormal` and `QuestTurnin` map atlases when
available, with gossip-texture fallbacks for clients without those atlases.
Hover does not resize the marker or its mouse target.

Minimap icons appear inside the visible range; distant quests do not accumulate
around the edge. Round and square minimaps are supported; other custom shapes
use conservative round clipping. Only current-zone coordinates are loaded, so a
quest across a zone border may appear after you cross it. If the client withholds
player coordinates, icons hide until coordinates are available again.

The sparkle effect reuses one frame and seven textures. Target checks run about
eight times per second while enabled and out of combat. Animation runs only
while an effect is visible. There is no unrestricted world object scan.

## Client and data limits

- Pickup markers are **database candidates**, not server-confirmed offers.
  Seasonal, phase, custom profession rules, unavailable content,
  and other server-only conditions can produce extra markers. Missing or stale
  database locations can still omit quests. Collapsed skill headers remain
  unknown; unmet or unknown required reputation is excluded in strict mode.
- Pickup markers for already completed repeatable quests depend on what
  completion state the server exposes.
- Map coordinates use the installed Forever database and its zone mapping
  overrides directly. No extra Era conversion is applied. Unknown coordinates
  and unsupported instance locations are skipped. Continent/world projection is
  not implemented.
- Custom glints follow **one** soft interaction target, usually within about
  15 yards on Forever. They cannot highlight every nearby object simultaneously,
  extend the game's effective range, or determine unopened corpse loot contents.
- Soft targeting and object interaction icons are enabled on first use. Objects
  may show the game's own interaction icon or nameplate. If you turn those client
  options off yourself, extra glints can stop until you enable a sparkle option
  again. The addon respects those later choices.
- Custom glints pause during combat. CVar writes are deferred until combat ends.
  The built-in quest loot effect may still be visible.
- Other objects means objects the client exposes as interactable; it does not
  guarantee all objects in the world will sparkle.

## Commands and turning off

- `/ql`: options.
- `/ql status`: last scan status and client-reported memory for guide/database.
- `/ql refresh`: refresh the visible map.
- `/ql off`: disable all features and restore saved soft-target CVars. When used
  in combat, restoration waits until combat ends.

Turn the features off **before** disabling/removing the addon. WoW persists CVars
even when an addon is disabled. Turning off the quest loot option sets
`outlineModeShowLootEffectWhenDisabled` to `0`, but removing an effect already
shown requires a full game restart; `/reload` is insufficient. Your outline
mode is left as configured.

If the addon was removed before turning it off, restore your desired Interact Key
and Interact Key Icons settings in the client, and use
`/console outlineModeShowLootEffectWhenDisabled 0` followed by a client restart.

## Validation and first in-game check

Offline Lua 5.1 tests cover filtering, source lookup, map changes, scan completion
during event bursts, frame limits with all quests represented, sparkle target
classification/animation, graphics resets, saved settings and combat restoration.
An integration harness loads the installed QuestieDB's baked data, support tables
and corrections read-only and exercises nine maps plus active quests, checking that no objective markers are added.

These checks do not emulate the actual renderer, protected execution or taint.
Before treating this as a stable release:

1. Enable script errors with `/console scriptErrors 1` and restart or reload.
2. Check pickup and turn-in markers in a familiar zone. Hover and hold Shift over
   grouped markers; pan, zoom, close, reopen, and switch maps.
3. Accept, progress, abandon and turn in a quest. Check that markers update.
4. Approach a herb, vein, quest object, chest and lootable corpse. Enter/leave
   combat and confirm glints resume without errors.
5. Change a graphics preset; verify quest sparkles return. Use `/ql off` during
   combat and verify restoration after the fight. Restart to check persistence.
6. Use `/ql status` after several zone changes to measure guide and database
   memory separately. Compare against Questie with the same character/addons.

## Credits and license

GPL-3.0-or-later; see `LICENSE`. `SoftTarget.lua`, `LootSparkles.lua`, and
`Textures/flare.tga` are adapted/copied from **Forever Loot Sparkles v1.3.1** by
Ashtar Senior (svengabr): <https://github.com/svengabr/ForeverLootSparkles>.
Changes include shared guide options, other interactables, explicit combat
suspension and slash-command shutdown. Existing attribution in the source is
preserved.

Questie and QuestieDB were consulted as references. QuestieDB remains a separately
installed dependency; its data and code are not redistributed in this package.
Forever's map canvas and quest API behavior was checked against the client UI
source mirror: <https://github.com/Gethe/wow-ui-source/tree/forever>.
