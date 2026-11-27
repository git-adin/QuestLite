# QuestLite 0.4.37

**Skipped breadcrumb warnings:** when you accept a destination quest, QuestLite
warns in chat about known breadcrumb introductions you have not accepted or
completed, with their giver and pickup location. Enabled by default; toggle
under `/ql` -> **Filters** -> **Warn about skipped breadcrumbs**. Wrong-race,
wrong-class, unsupported-season and already-handled alternative introductions
are excluded. Warnings use recorded database links, so missing links cannot
be detected. At most five references are shown, once per destination per
session within a bounded recent-history cache. QuestLite does not abandon quests.

**Remote Contact:** all three referrals (Andron Gant, Jes'rimon and Magatha)
require a current offer from their own giver in available-only mode. Guide
notes identify each giver and the Jediga / Stealing Knowledge route. Accepted
referrals and ready turn-ins remain visible. Broad browsing can inspect them.

**Xylem's Potion of Demonslaying order:** you can accept this quest directly
from Archmage Xylem without owning the writ. You still need the writ and
requested potion to complete it. QuestLite now shows an ordinary NPC pickup,
independent of the item-started location toggle. The quest guide explains this
distinction. Other writ orders retain their current checks.

**Betrayed in Azshara:** the old tome pickup and finale are legacy entries.
Available-only mode requires a real server offer for them. The guide follows
Seals of the Sin'dorei -> An Explosive Gambit -> Revenge Exacted, with the
separate Sin'dorei Tome of Summoning branch. Active legacy turn-ins remain
visible, and direct inspection explains the revised route.

**Kurll / Deadliest Catch:** learn Fishing (skill 1 is enough), turn in
Home on the Range, then turn in Winter Frontier Fishery. The squid can be
bought from other players. Available-only mode checks Fishing and the missing
shark-quest prerequisite; the quest guide includes the route.

**Timbermaw reputation:** pickup markers for the 18 documented Azshara and
Blackmaw quests require **Neutral with Timbermaw Hold** in available-only mode.
The quest guide explains the reputation requirement. The Legashi Threat and
Legashi Horns remain available for building reputation. Gaining reputation
refreshes both maps; other quest prerequisites may still apply.

**State Secrets:** all three deliveries require a Document Box in your bags.
Buy one from another player, or obtain it through More Valuable Than Gold
(the Alcaz Prison rescue chain, then Westfall 43.4, 67.8). The guide explains
this item requirement; completing the rescue chain yourself is optional.

**Oasis / Tooga:** during Tooga's Quest, lead him to the oasis in Tanaris at
**41, 54** and wait for him to drink, then talk to him. Strict mode shows Oasis
only after a current NPC offer confirms it. Its recorded pickup/turn-in stop
uses the oasis coordinates, not Tooga's normal spawn. The quest guide includes
the instructions and lists Oasis under **During escort** in Tooga's next-chain
view. This is a conditional stop, not a prerequisite requiring the escort to be
turned in. Broad browsing still shows the recorded stop beforehand.

## Quest item cleanup notes

Hover a quest item in your bags or an item link to check its known quest uses
for this character. **Quest item cleanup notes** is enabled by default under
`/ql` -> **Map**.

- **Keep**: an active quest, unfinished future quest, repeatable/daily turn-in,
  or unresolved quest information still needs consideration. Finishing objectives
  does not count as turning the quest in.
- **Quest leftover: safe to discard for known quests**: every known applicable
  use is completed and no repeatable use remains. This applies to quest-class
  items, including leftovers originally supplied by quests.
- **Quest use finished; this item may have other uses**: a provided item is not
  strictly a quest item, or teaches a spell. Quest completion alone does not
  establish that it has no other value.

Ordinary quest reward gear gets no deletion recommendation. Unknown items without
enough quest-use evidence are left unmarked. These notes describe QuestieDB's
known uses, not a guarantee about unrecorded server quests, collections or other
uses. Items are never deleted automatically. Known container/conversion links
are followed; incomplete conversion chains stay conservative. Character
class/race and unsupported-season identities are respected.

The check runs on demand in small background batches, caching at most 64 item
results. Quest-state changes invalidate old advice, and visible notes update
without adding duplicate lines. There is no permanent second full quest index.

**Only available quests** excludes known Season of Discovery quests in Forever,
including Nightmare Incursion missions. Explicit unsupported-season exclusions
stay hidden even after an NPC offer observation. Broad browsing keeps their
**Season of Discovery** label; actual ready turn-ins remain visible. These rules
use verified IDs, not title matching or blanket exclusion of reused quest IDs.

Other known Craftsman's Writs require their starter item in your bags in **Only available
quests** mode, unless a current NPC offer confirms availability. Their delivery
NPCs are not advertised as ordinary pickups: unaccepted writs use a **Use writ**
reference, reminding you to use the item first. Bag changes refresh both maps.
The item-started quest toggle controls these references; ready turn-ins remain
visible. Broad browsing can show unowned writ references, with the same item
requirement reminder. Generic item drops and quest-provided items are unchanged.

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
`/ql taint` prints a read-only ownership snapshot of action-bar functions and
references, without reading cooldown values or changing Blizzard handlers.
`/ql status` includes the loaded addon version. See the [taint audit](https://github.com/git-adin/QuestLite/blob/main/QuestLite/TaintAudit.md).
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
5. Use `/ql` or either QuestLite map button to open the Map / Filters / Quest chain window.

The guide and expanded marker details show quest level separately from minimum
pickup level. A red quest level describes difficulty, not necessarily its pickup
requirement. Unknown minimums are labelled unknown. Betrayed (3504) has a listed
minimum of 44 and quest level 53, but its Forever availability is unverified;
strict mode requires a current NPC offer for that pickup. Broad browsing still
shows the candidate, and ready turn-ins remain visible.

A gold **!** button around the minimap also opens options. Drag it around the
edge to reposition it; its position is saved per character. **Show QuestLite
minimap button** in `/ql` hides it independently of quest markers.
The main world map has its own gold **!** options button at the upper left,
joining the shared map-button stack when Questie/RareScanner provides it.
It remains accessible when quest markers or the minimap button are disabled.

Map and sparkle features start enabled; Show low level quests starts off.
Preferences are saved per character.

### Availability filter

The normal pickup cutoff defaults to 5 levels below your character. At level 22
this includes quest levels 17 and above, subject to pickup requirements. There is
no extra upper-level cutoff. Adjust **Normal level limit (levels below mine)**
in `/ql`. Turn **Show all low-level quests** on to show all available low-level
quests, bypassing that cutoff; it defaults to off.
This applies to continent, zone and minimap pickups. Ready turn-ins remain visible
at any level. Quests with unknown or scaling levels remain visible. Leveling up
automatically refreshes the threshold. `/ql status` reports the minimum level.

In `/ql`, **Only available quests** is on by default. It applies known
level, chain, class/race, profession rank/specialization, reputation, spell and required-item
restrictions, removes obsolete breadcrumbs and auto-reward entries, and skips
wrong-faction NPC givers. Quest item drops from hostile creatures remain valid
sources.
Race checks use QuestieDB's race-ID mapping, including Skyborne IDs 95/96, rather
than assuming a race ID is its position in the database mask.

It also applies a compact Forever-compatible display policy for hidden,
unobtainable and conditional quests, including the library catalog, Scourge
Invasion, and AQ War Effort supply/commendation quests. Explicit NPC offers can restore these entries. See
[the availability audit](https://github.com/git-adin/QuestLite/blob/main/QuestLite/AvailabilityAudit.md) for the audit, provenance and limits.
The event-specific sweep is recorded in the [event coverage notes](https://github.com/git-adin/QuestLite/blob/main/QuestLite/EventCoverage.md).
Known Season of Discovery leftovers are excluded in the normal Forever view and
carry season/class labels for eligible characters browsing unfiltered candidates.
Race/class masks still apply to confirmed NPC offers and broad mode. See
[the class and season audit](https://github.com/git-adin/QuestLite/blob/main/QuestLite/ClassSeasonAudit.md) for the screenshot-specific corrections.
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
Breadcrumb filtering follows explicit database relationships. Elayaa's Skyborne
Hunter quest remains available after taming training: live-server testing confirmed
that the introductory text does not imply a breadcrumb availability restriction.
Local corrections fill verified missing database links for Mankrik, the Titan
Relic follow-ups, and the Dalaran chains. They do not alter QuestieDB's shared
data. The [item gate audit](https://github.com/git-adin/QuestLite/blob/main/QuestLite/ItemGateAudit.md) records the item-related review and
distinguishes native provider requirements from our corrections.

Verified class/race data gaps are corrected locally while their old provider
values remain unchanged: Alaana's Call of Air is Shaman-only, four Mage/Druid
training records retain their class limits, and Compendium of the Fallen includes
Horde Skyborne while excluding Forsaken and Alliance. New native masks take
precedence. See the [class and season audit](https://github.com/git-adin/QuestLite/blob/main/QuestLite/ClassSeasonAudit.md).

Turn the checkbox off to also see locked or higher-level database candidates.
Completed, active, wrong-race and wrong-class quests remain hidden. Turn-in
markers and sparkles are unaffected. Changing the checkbox refreshes the map.

The filter estimates distant quest availability from known data; it cannot
guarantee server-only conditions before you visit the giver. Conditional holiday
and event pickups require an NPC offer in strict mode; use the broader view to
browse them before visiting. Calendar activation is not implemented.

## QuestLite window

Open `/ql` or click either QuestLite map button. The window has three tabs:

- **Map:** world-map/minimap icons, pickups, turn-ins, loot sparkles and tooltips.
- **Filters:** availability, PvP, cloth donations, item-drop sources and the lower-level cutoff.
- **Quest chain:** search part of a quest name, paste a quest link, or open a quest directly from a marker. Switch between **Prerequisites** and **Next in chain**.

Left-click a marker to open its quest guide. Grouped markers let you choose
one quest. The guide shows missing steps and known pickup/return locations.
**Next in chain** lists direct follow-ups with their pickup locations and current
accepted/completed status. Click a row to inspect that quest's chain. Markers
start with prerequisites when steps are missing, otherwise with follow-ups;
both modes remain available. A missing database link is shown explicitly, not
inferred from the quest title. Follow-ups can have other unmet requirements.
When alternatives are shown, choose one branch; they are not cumulative tasks.
Accepted quests point to their turn-in location. Visible guidance refreshes after
quest-log changes or turn-ins. Hidden quests remain searchable.

Right-click still selects a pickup to hide; Shift-left-click keeps the quick-hide
shortcut. Use **Hidden quests** in the window to restore pickups. The draggable
window reuses its controls and offers paged search results/routes. No command or
quest ID is required for the normal search workflow. Existing settings are kept.

## Find missing quest prerequisites

Use `/ql prereq <quest ID or exact quest name>` to see known missing quest turn-ins
and where to pick up or return them. For example:

```
/ql prereq Smuggler's Paradise
/ql prereq 95288
```

Shift-hover details show the same information for locked pickups when browsing
with availability filtering off. Guidance follows your class/race branch, lists
earlier missing steps first, and uses known giver coordinates. An accepted quest
points to its turn-in NPC instead. Completed introductions stop appearing.

Smuggler's Paradise now requires The Goblin Trader (Horde) **or** A Few Furs for
Friz (Alliance) turned in. Their verified preceding steps and Smuggler's Special's
link are also supplied when missing from the provider. Native requirements take
precedence as usual. These are turn-in links, not inferred breadcrumb gates.

Guidance is limited to four links and ten quest rows, with cycle protection and
an omission notice. It describes known turn-in prerequisites rather than every
possible server condition, skill requirement or event state. Unknown locations
stay unknown. Name lookup uses current localized names and reports at most three
exact matches; an ID avoids ambiguity. No full quest graph or name index is kept.

## Hide cloth donation pickups

Enable **Hide cloth donation pickups** in `/ql`, or use `/ql cloth` to toggle it.
It covers the capital reputation donations of wool, silk, mageweave and runecloth,
including repeatable Additional Runecloth and both Skyborne factions. It affects
pickup markers on both maps, with ready turn-ins preserved. Other crafting or
story quests involving cloth are unaffected. The per-character setting starts off
to preserve your display; it applies in broad browsing and to confirmed offers.

## Hide PvP quest pickups

Enable **Hide PvP quest pickups** in `/ql`, or use `/ql pvp` to toggle it.
The per-character setting hides PvP pickup markers on the world map and minimap,
including broad browsing and confirmed offers. It starts off to preserve your
existing display. Ready turn-ins remain visible, matching Questie's available
PvP quest option. Individual hidden quests and other pickup filters still apply.

Classification uses verified local PvP IDs and Questie's applicable tag corrections, then the game's
PvP tag (41), without a Questie runtime dependency. Non-PvP corrections also take
precedence to avoid false exclusions. Unknown or secret tags stay unclassified;
new quest-data results refresh the filter when enabled. Darkspear Islands mark
turn-ins and battleground-victory quests have explicit corrections for missing
tags, covering both factions and all eighteen known variants. Quest names, enemy-faction
NPCs and PvP-zone locations alone are not treated as proof of a PvP quest.

## Hide individual quest pickups

Right-click a QuestLite marker on either map and choose the quest to hide. A
grouped marker lists each pickup separately; it never hides the entire group.
Shift-left-click hides a single pickup immediately, or opens the list for a group.
This hides that quest's pickup markers at every location, saved per character.
Ready turn-ins remain visible. Hiding works even with availability filtering off.

Use `/ql hidden` to open the restore list and click a quest to restore it.
`/ql unhide <quest ID>` restores one by ID; `/ql unhide all` restores every manually
hidden pickup. The drop-source toggle below is independent: a restored quest's
item-drop locations still follow that option.

## Quest-starting item drop locations

In `/ql`, turn **Show item-started quests** off to hide markers for quests
started by dropped items. `/ql drops` toggles the same per-character option.
It starts enabled to preserve existing settings. The option affects both the
world map and minimap, including container-based starters. It hides all item-start
markers, including the destination references described below. Direct NPC and
object pickups, ready turn-ins, quest-item drop-rate tooltips and loot sparkles
are unaffected. Mixed-source quests keep their ordinary giver markers.

The three **Find OOX** beacon quests and **Crystal in the Mountains** (Pendant
of Myzrael) show their known turn-in NPC/object instead of scattered drop-source
areas on both maps. These are reference destinations, labelled **Item quest
destination**: obtain the dropped starter first. They do not mean that the NPC
offers a pickup or that the quest is complete. The normal eligibility, low-level,
item-start and per-quest hiding settings still apply. Accepted quests use normal
ready turn-in markers. Other item starters retain their source locations; missing
finisher data falls back to those sources.

## Included

- Quest pickup markers, including low level quests; known level, race, class,
  prerequisite, exclusive quest, parent quest, basic skill, learned spell and
  reputation restrictions are checked against the character.
- Objective markers are left to Blizzard's built-in map display.
- Completed quest turn-in locations.
- Nearby minimap pickup and turn-in icons, with quest-giver hover lists and Shift
  details. **Minimap icons** in `/ql` switches these on/off independently
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
- One-time restoration of interaction settings changed by older custom-sparkle
  versions. QuestLite no longer enables soft targeting or custom glints.

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
server rates can differ. When no NPC rate is known, the item's native tooltip
is left unchanged, without an empty heading or unknown-data message. This also
applies to object-looted and combined quest items. Restricted instance creature tooltips
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

World-map pin updates are deferred during combat because native MapCanvas pin
acquisition configures protected mouse-button passthrough. Existing QuestLite
world pins hide during combat and rebuild afterward. Minimap markers continue.

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

QuestLite keeps only the client's built-in quest loot sparkle. The custom
soft-target/nameplate sparkle engine was removed in 0.4.0 following the same
change in Forever Loot Sparkles 2.0.0: it could affect untargeted friendly spells,
leave empty corpse nameplates and show unwanted interaction icons. There is no
custom sparkle animation or interaction-target polling.

On login, old saved interaction settings are restored outside combat, with a
second pass after five seconds for late account synchronization. Restoration
only touches the known settings previously managed by QuestLite, skips malformed
values, and preserves current values that differ from those it used to set.
Failed restores retain the saved originals for another login. See
[the sparkle migration notes](https://github.com/git-adin/QuestLite/blob/main/QuestLite/SparkleMigration.md) for the migration and its limits.

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
- Built-in sparkles are selected by the game. QuestLite does not add custom
  highlights to herbs, ore, corpses, chests or other interaction targets.
- Quest-loot sparkle CVar changes and legacy interaction-setting restoration wait
  until combat ends.

## Commands and turning off

- `/ql`: options.
- `/ql status`: last scan status and client-reported memory for guide/database.
- `/ql taint`: read-only action-bar taint ownership snapshot for troubleshooting.
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
during event bursts, frame limits with all quests represented, graphics resets, saved settings,
legacy CVar migration and combat restoration.
An integration harness loads the installed QuestieDB's baked data, support tables
and corrections read-only and exercises nine maps plus active quests, checking that no objective markers are added.

These checks do not emulate the actual renderer, protected execution or taint.
Before treating this as a stable release:

1. Enable script errors with `/console scriptErrors 1` and restart or reload.
2. Check pickup and turn-in markers in a familiar zone. Hover and hold Shift over
   grouped markers; pan, zoom, close, reopen, and switch maps.
3. Accept, progress, abandon and turn in a quest. Check that markers update.
4. Verify that untargeted friendly spells, corpse nameplates and interaction
   icons behave as configured after the migration. QuestLite adds no custom glints.
5. Change a graphics preset; verify quest sparkles return. Use `/ql off` during
   combat and verify restoration after the fight. Restart to check persistence.
6. Use `/ql status` after several zone changes to measure guide and database
   memory separately. Compare against Questie with the same character/addons.

## Credits and license

Data from ForeverDB.net (https://foreverdb.net). The local fixed-level and NPC
location corrections were introduced and reviewed across several snapshots. See
[the ForeverDB audit](https://github.com/git-adin/QuestLite/blob/main/QuestLite/ForeverDBAudit.md) and [FOREVERDB_LICENSE.txt](FOREVERDB_LICENSE.txt).
These compact corrections are included locally; ForeverDB is not a dependency.

GPL-3.0-or-later; see `LICENSE`. `LootSparkles.lua` and the legacy-setting
cleanup are adapted from **Forever Loot Sparkles v1.3.1 / v2.0.0** by
Ashtar Senior (svengabr): <https://github.com/svengabr/ForeverLootSparkles>.
Changes include shared guide options, validated migration of legacy settings,
combat deferral and slash-command shutdown. Existing attribution is preserved.

Questie and QuestieDB were consulted as references. QuestieDB remains a separately
installed dependency; its data and code are not redistributed in this package.
Forever's map canvas and quest API behavior was checked against the client UI
source mirror: <https://github.com/Gethe/wow-ui-source/tree/forever>.
