# Edge-case audit, 0.2.11

These bugs were reproduced in the offline Lua 5.1 harness before being fixed:

- Closing the world map cleared the shared tooltip even when a minimap icon
  owned it. World-map cleanup now clears only its own hover.
- A minimap icon crossing out of range and back between group updates could
  stay hidden at its original coordinates. The movement path restores visibility.
- A hovered quest changing from pickup to completed turn-in at the same giver
  kept its old tooltip because the quest ID had not changed. Refresh now checks
  the source records as well as quest IDs.
- NaN or infinite player coordinates, radii and map dimensions produced invalid
  marker positions. Non-finite geometry now hides markers and valid data restores
  them. Continent rectangle checks use the same validation.
- Damaged saved CVar values could be stringified and restored; unknown keys could
  change unrelated settings. Restoration now uses the managed-key list and only
  accepts finite numeric values or numeric strings. Legacy icon restoration remains.
- Item names were matched as substrings in native quest progress rows. Whole
  progress-item matching avoids adding Tooth's rate to Sharp Tooth or Tooth Fragment.
- Returning from zone A to B to cached A while B was still scanning allowed the
  obsolete scan to finish and replace the snapshot temporarily. Zone changes now
  cancel obsolete work before checking the cached snapshot and before resuming it.

Regression checks cover these cases alongside the existing availability, event,
quest-chain, tooltip, minimap, combat shutdown and settings tests. The installed
QuestieDB integration also compares source-specific drop rates and reads actual
quest data. All 60 regression tests passed, along with both installed-database
profiles and 19,516 drop-rate source/correction comparisons. A simulated provider
failure also verified that scans stop without repeated retries and recover on
explicit refresh after the provider is restored.

These are offline checks; native rendering and live server conditions
still require in-game validation.

## Item-start source visibility (0.4.9)

The per-character itemDropLocations option controls only item-source pickup
expansion in the shared map builder. Disabled sources are skipped before NPC,
object or nested-container traversal. Ordinary sources of mixed-start quests and
ready turn-ins remain intact. The option participates in the shared map state key,
so world snapshots, eligible-ID reuse and minimap workers update on either the
settings callback or `/ql drops`. Re-enabling restores the same compacted sources.
Existing settings default to enabled, and the separate dropChances option is
unchanged. The regression covers warm-cache toggles on both maps, nested starters,
ordinary/mixed givers, ready turn-ins and zero source traversal while hidden. The
real-provider check exercises Pendant of Myzrael (4614), Crystal in the Mountains
(635), on Arathi's world map and minimap. 96 offline regressions pass.

## Per-character manual pickup hiding (0.4.10)

Right-click opens an individual quest picker on world-map and minimap markers.
Shift-left-click hides a single pickup directly; grouped pickups use the picker.
Ready turn-ins are not selectable. Hidden quest IDs are validated and saved as
boolean entries, checked before confirmed-offer and broad-view shortcuts. The
revision participates in the map state key, invalidating both maps' snapshots.
Ready turn-ins are emitted independently, so accepting a quest does not suppress
its later turn-in. Source-location visibility remains an independent option.

The restore picker is available through `/ql hidden`, with `/ql unhide <ID>` and
`/ql unhide all` alternatives. One reusable window and twelve row buttons handle
any list through pagination, without per-frame polling or Blizzard dropdown hooks.
The window closes in combat; state changes through commands use the existing
combat-safe map deferral. Escape closes it through UISpecialFrames where present.

Validation: 99 Lua 5.1 regressions, including native-style mouse scripts on both
maps, grouped selection, pagination/frame reuse, persistence/sanitization,
strict/broad mode, ready turn-ins and hide/restore during combat. The installed
provider check also hides/restores the actual Pendant pickup on both maps. Live
client interaction and rendering still require in-game verification.

## PvP pickup visibility (0.4.11)

Questie 12.8.0's Available PvP Quests option uses IsPvPQuest -> GetQuestTagInfo,
with correction precedence and PvP tag 41. Only available icons are hidden;
ready turn-ins are preserved. QuestLite follows that behavior with a per-character
Hide PvP quest pickups checkbox and `/ql pvp` toggle, default off.

The offline generator now evaluates Questie's tag corrections in its restricted
Classic/Forever environment and retains only IDs present in the provider. The
compact static table contains 1,142 corrected tags, including 216 PvP tags. Other
corrected tags are retained too, so a native PvP tag corrected to Elite/Dungeon is
not falsely excluded. A source SHA256 is recorded. No Questie runtime is loaded.

Uncorrected IDs use C_QuestLog.GetQuestTagInfo, with the legacy GetQuestTagInfo
fallback only when the modern function is absent. Protected failures and secret
or unknown tag values are not guessed. Nil tags are not negatively cached.
QUEST_DATA_LOAD_RESULT invalidates map snapshots only while this filter is on.
No names, factions, objective text or general zone categories infer PvP status.

The visibility bit participates in the common state key and is checked before
confirmed-offer/broad-mode shortcuts. Already-ready turn-ins bypass pickup
eligibility as before. 101 regressions cover both maps, native/corrected tags,
non-PvP correction precedence, unknown-to-PvP data updates, legacy/secret/error
paths, warm-cache toggles and preserved turn-ins. Both installed-data profiles
check all 216 PvP corrections. Unknown/misclassified server content still depends
on the available tag data or can be hidden individually by the user.

## Cloth donation pickup visibility (0.4.14)

Hide cloth donation pickups is a per-character checkbox with `/ql cloth` toggle,
default off. Fifty explicit provider-verified IDs cover capital reputation wool,
silk, mageweave, runecloth and additional runecloth donations, including ten
Skyborne faction quests. Runtime classification uses the compact ID set rather
than translated titles, generic cloth objectives or all repeatable quests.

Pickup eligibility checks the setting before broad-mode and offer shortcuts;
ready turn-ins remain independent. The state bit participates in both maps' cache
keys. The regression covers warm-cache hiding/restoring, ordinary cloth crafting
pickups, ready turn-ins and Skyborne/repeatable donations. The real-provider audit
cross-checks the ID set against the five enUS donation titles offline, detecting
new unreviewed donations or unrelated included IDs. No title matching runs in game.
Validation: 102 offline regressions and both installed-data profiles.

## Darkspear Islands missing PvP tags (0.4.15)

The screenshot's Horde Warbringer pickups are 98887/98888 (level 39) and
98889/98890 (level 49). These and the other Darkspear battleground variants have
no Questie tag correction and cannot reliably be classified by the native tag.
Records 98890 and 98898 also lack the battleground category. Added a compact
explicit ID set, evaluated before tag corrections/API results:

- Horde mark turn-ins: 98887, 98888, 98889, 98890, 98891, 98893.
- Alliance mark turn-ins: 98895, 98896, 98897, 98898, 98899, 98901.
- Victory quests for both factions: 98903, 98904, 98905, 98906, 98907, 98908.

The provider's objective data and the firsthand quest text establish the PvP
requirements: [Horde marks](https://www.wowhead.com/forever/quest=98887/conflict-at-darkspear-islands),
[Alliance marks](https://www.wowhead.com/forever/quest=98895/darkspear-islands-clash),
and [battleground victory](https://www.wowhead.com/forever/quest=98906/the-battle-for-darkspear-islands).
Runtime uses IDs, not translated text, an entire ID range or a quest-giver rule.

The battleground category and both Warbringer/Brigadier giver lists were reviewed.
Unplaced care-package records 98910/98913 have no objectives or givers; they are
not assigned requirements or invented pickup locations from category alone. Other
classic battleground quests keep their existing tag classification.

The existing saved PvP toggle now hides these pickups on both maps, including
broad mode and confirmed offers; turning it off restores eligible pickups.
Ready turn-ins remain visible. Validation: 103 offline regressions and both real
provider profiles. Tests cover all eighteen records, missing/zero tags, zone-less
variants, unrelated quests from the same NPC, actual Orgrimmar Warbringer markers,
warm-cache toggles and preserved turn-ins. No shared provider data is changed.

## Clickable guide and dedicated options window (0.4.18)

The QuestLite buttons and empty `/ql` command now open a dedicated Map / Filters /
Prerequisites window. Existing Blizzard settings remain compatible with the same
saved data. Controls change only their own feature, including the existing
combat-safe sparkle apply path. Filter callbacks refresh both map snapshots.

Plain left-click opens a single marker's prerequisite guide; groups use the
existing fixed-size picker in View mode. Right-click hide, Shift-click quick hide
and the restore picker retain their semantics. A View selection never changes
hiddenQuests. The normal tooltip hint is shortened.

Search is explicit (button/Enter), accepts a partial localized name or quest link,
and does not depend on the availability filter. Text results are limited to the
character's race/class, while explicit IDs/links support direct inspection.
Twenty matches and four visible rows bound the UI. Exact-name matches take
priority. No persistent name index or graph is created. Search does not run on
every keystroke. Four rows are reused for route steps; earlier depth/row bounds
remain, and multi-choice alternatives are not expanded into cumulative routes.
Clicking an alternative drills into that branch separately.

Structured route steps share the same prerequisite selection as chat/Shift hints.
The root location is shown even when no prerequisites are missing. The window
refreshes a visible selected guide only on meaningful log-state changes or a
turn-in event, without OnUpdate polling. The former direct command remains.

Validation: 111 offline regressions, including both entry buttons, grouped/single
marker clicks on both maps, partial/link search, native data search, tab/control
state, bounds/pagination/frame reuse, step drilldown, turn-in refresh and alternatives.
Both real-provider profiles pass. This is offline functional coverage; the actual
client layout still needs a visual check after reload.
