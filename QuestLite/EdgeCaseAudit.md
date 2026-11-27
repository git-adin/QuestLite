# Edge-case audit, 0.2.11

## Oasis escort stop - 0.4.29 (2026-11-25)

The user reports Oasis (97540) appears only after escorting Tooga to Tanaris
41,54 and letting him drink. Firsthand comments on
[Tooga's Quest](https://www.wowhead.com/forever/quest=1560/toogas-quest)
corroborate the stop (some give 41.5,54.5). The provider has no parent, starting
condition or prerequisite for Oasis and attaches both pickup/turn-in to moving
NPC 5955's normal spawn. Main escort 1560 ends at Torta 6015.

Strict mode now requires an actual Oasis NPC offer, rather than assuming that
accepting or turning in the main escort is sufficient. This also allows real
late offers, reported by one player after reaching Torta. The recorded quest-only
stop is 41,54 for both pickup and ready turn-in; it is a known event location,
not live tracking of Tooga as he moves. No global NPC coordinates or native
prerequisite fields are changed. Broad browsing keeps the reference marker.

Guide locations and context text explain the drinking trigger; the next-chain
view adds a During escort relation to 1560 without inventing a turn-in gate.
Conditional instructions remain visible when drilling into the next-chain view.

Validation: 131 Lua regressions, two package tests and both installed-provider
profiles. Both maps, premature suppression, confirmed offer restoration, ready
turn-ins, normal Tooga spawn retention and immutable provider requirements are
covered. Client smoke record: user screenshot/report establishes pre-fix false
pickup; post-fix pending. Reload 0.4.29, start Tooga's Quest, take him to 41,54,
wait for drinking and open his quest dialog; verify Oasis at the recorded stop
and its guide instructions. No live escort run was performed by the agent.

## Quest item cleanup notes - 0.4.28 (2026-11-24)

New optional item-tooltip consumer, initialized after database startup. On-demand
coroutine scans inspect quest objectives, provided items, required source items,
item starters and inverse related-quest metadata. Known item-container conversion
links are followed up to four levels; unresolved deeper conversion data prevents
discard advice. Relations for other classes/races and verified unsupported
seasons do not block this character's result. A separate permanent reverse quest
graph is not allocated: 64 cached item results, 128 temporary conversion entries,
one worker and the two native tooltip request slots are bounded.

All known relevant uses must be turned in before a quest-class item gets the
qualified safe-to-discard note. Active ready quests, unfinished future uses,
unknown completion and repeatable/daily quests remain Keep. A provided non-quest
item or spell-teaching item only receives a qualified finished-use note. Ordinary
reward gear and unidentified items with no use evidence get no recommendation.
This cannot certify unknown server data or non-quest uses and does not delete
items. Both modern tooltip callbacks and guarded legacy script hooks are used;
no global handlers or protected inventory actions are replaced.

Quest events invalidate results and immediately remove stale green advice while
checking again. Native font-string ownership is checked before changing an old
line; tooltip reuse or restricted identifiers cannot receive a previous item's
result. Unknown/failed analysis never becomes a positive discard recommendation.

Validation: 130 Lua regressions, two package tests and both installed-provider
profiles. Coverage includes active/ready/future states, repeatables, missing IDs/data,
conversion links, utility items, ordinary rewards, race/season scope, cache
bounds, item hover changes, native callback reuse, and real item 745 / quest 54
(Marshal McBride's Documents / Report to Goldshire) in both provider profiles.
Client smoke record: post-install check pending. Reload 0.4.28, hover a finished
quest-class leftover and an item for a current quest; verify the green versus
Keep notes, a normal reward weapon, the option toggle and quest turn-in refresh.
Offline emulation does not verify live tooltip layout or undiscovered item uses.

## SoD incursion mission sweep - 0.4.27

The screenshot's eighteen Feralas mission pickups were absent from the bundled
exclusions. Installed Questie 12.13.0 adds the full daily mission blacklist, while
the bundled policy had been generated with 12.12.0. Refreshed all policy data
against QuestieDB 1.1.5 (6083 quest IDs). The provider's raw and public quest-ID
inventories were compared and match; this is not a raw/composed ID discrepancy.

The generator now extracts every explicit `not Questie.IsSoD` exclusion as a
separate unsupported-season set: 68 current IDs, including all 54 Duskwood,
Hinterlands and Feralas missions. It verifies that these were evaluated as hidden
and rejects unreviewed condition syntax. Runtime rejects them before confirmed
offer restoration. Broad view uses a Season of Discovery label, and active ready
turn-ins are preserved. Existing conditional event/library restoration still
works. Wild Leather duplicate rules remain separate.

This is not a blanket import of SoD rune/phase membership: Forever reuses some
quest identities, including the Earthmother quests. No title or ID-range filter
is used at runtime. The full generated policy now covers 671 hidden/conditional
IDs, 1412 tag corrections and the existing 238 PvP tags. Regenerate and validate
this policy when upstream reference files change; unknown future SoD records
without authoritative exclusions still require review.

Validation: 124 offline Lua tests, two package tests and both installed-provider
profiles. All eighteen screenshot missions are tested on both maps, with normal
quest retention, broad labels, positive NPC observations and ready turn-ins. All
54 native mission records and preserved reused identities are audited. Client
smoke record: supplied screenshot shows the pre-fix leak; post-fix pending.
Reload 0.4.27 with Only available quests enabled and check Field Captain Arunnel
and the corresponding Hinterlands/Duskwood markers. No renderer/protected hook
changes or live client success are claimed.

## Wild Leather Vest duplicate - 0.4.26

User confirmed Jangdor was present, the character has Leatherworking, and the
displayed quest was not offered. Screenshot has a blank first item objective.
Provider records 82656/82657 are ungated Wild Leather Vest variants; 82656 requires
item 217268, whose name is absent in the Forever view. Installed Questie's
Database/Corrections/ContentPhases/SeasonOfDiscovery.lua explicitly documents
2856 -> 82656 and 2849 -> 82657 replacements in its SoD phase table. The screenshot
is consistent with the Horde duplicate; no live marker quest-ID capture is claimed.

Classified these exact two IDs as Season of Discovery. Strict mode rejects them
even after a stale/incorrect offer observation. Broad browsing keeps their season
label and native faction mask; active ready turn-ins remain visible. Normal quest
2856 requires 2854 (Wild Leather Armor) and Leatherworking 165/225; Alliance 2849
requires 2847 and the same skill. Native gates and provider data are preserved.
No extra skill requirement, reputation gate or replacement of the normal chain
is inferred from the character simply having Leatherworking.

Validation: 122 offline Lua regressions, both installed-provider profiles and two
package tests. Both maps, prerequisite/skill boundaries, wrong-faction rejection,
broad labels and ready turn-ins covered. Forever client smoke: supplied screenshot
reproduces pre-fix state; post-fix pending. Reload 0.4.26 and verify the duplicate
is absent in strict mode; the normal quest should appear only after its native
requirements are met. No map renderer or tooltip hook is changed.

## Craftsman's Writ false NPC pickups - 0.4.25

The user screenshot shows quest 94316 at Archmage Xylem without the writ/quest.
QuestieDB 1.1.5 records both NPC 8379 and item 264116 as starters, and the same
NPC as finisher. This mixed-source record bypassed ordinary item-source handling.
The quest text requires the writ itself for delivery. Explicitly classified all
150 known English-provider Craftsman's Writ IDs offline; runtime uses IDs and
the provider's starter item IDs, not localized names or a guessed ID interval.

Strict mode now requires an owned bag starter; unknown inventory does not count
as ownership. Current server offers retain the existing shortcut. Broad mode
retains browsable references. Available writs emit labelled delivery references
with Use writ wording instead of NPC pickups/source swarms. Item-start toggle
and hidden-quest settings apply; active ready turn-ins remain independent.
No sourceItemId/provided-item rules or unrelated mixed-source quests are changed.
Existing BAG_UPDATE_DELAYED invalidation updates both maps and eligibility cache.

Validation: 121 offline regressions, two package tests and both installed-provider
profiles; all 150 IDs, actual Xylem records, item gain/loss, absent NPC offer,
unknown inventory, broad view and ready turn-ins covered. Provider rows unchanged.
Client smoke record: supplied screenshot demonstrates the pre-fix false pickup.
On November 23, the player verified in Forever 0.4.25 that Xylem's writ was
absent in strict mode without the item. Live checks for the owned-writ **Use
writ** marker and the ready turn-in remain pending.

## Next-in-chain navigation - 0.4.24 (2026-11-23)

The quest window has two modes: missing prerequisites and direct follow-ups.
Next-chain lookup merges the explicit nextQuestInChain field with reverse native
prerequisite links, using the same native/fallback precedence as eligibility.
It filters wrong race/class branches, deduplicates explicit/reverse links, avoids
self links and does not recursively expand cycles. Completed and active quests
are labelled; unrelated availability gates are not presented as already satisfied.

Only explicit guide access scans the provider. The panel retains one result of
at most twenty quests, refreshed on quest-state changes and turn-ins; four reused
UI rows page through it. No global reverse graph, map polling or eligibility
mutation is introduced. Native provider rows are released after inspection.
Unknown finisher/pickup data retains the existing unknown-location wording.

119 offline Lua tests and both installed QuestieDB 1.1.5 profiles pass, including
the actual 351 -> 648 OOX link. Quest 470, Digging Through the Ooze, has no
recorded direct follow-up. Unit coverage includes branches, local fallback/native
precedence, unrelated grandchild exclusion, status refresh, row reuse, pagination,
terminal quests and navigation between modes.

Forever client smoke record: the user's screenshot confirms the existing marker
opens the guide, with an empty prerequisite list for quest 470. On November 23,
the player confirmed that **Next in chain** opened correctly in 0.4.25. The
specific 470 and OOX cases, paging, and window bounds were covered offline.

## Empty item drop-rate section - 0.4.23 (2026-11-22)

ItemTooltip previously added its heading before finding a usable rate, then
displayed an unknown-data placeholder. It now starts the section only when a
known NPC rate exists. Items with unknown rates or no NPC sources receive no
lines, display call or duplicate-token mutation. Known rates, including zero,
source limits, duplicate protection and inline creature annotations are retained.
The existing regression now checks that the native name/Soulbound/Unique lines
remain unchanged across repeated unknown/object-only item callbacks. All 117 Lua
tests and two packaging tests pass.

Forever client smoke record: the user's 2026-11-22 screenshot reproduces the old
two-line empty section on Shredder Operating Manual - Chapter 3. Post-fix client
verification is pending: reload 0.4.23, hover that item and verify only the native
lines remain; hover a quest item with a known rate and verify its estimate still
appears. Tooltip hook registration and protected UI behavior are unchanged.

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


## State Secrets item gate (0.4.30)

User reports Nazgrel has no pickup despite marker. Installed QuestieDB lacks
requiredSourceItems and prerequisites for 96376, 96377 and 96379. Wowhead
quest progress text requires Document Box 274041; firsthand Alliance and item
comments confirm possession and that boxes are tradeable. Do not invent a
mandatory 96337 completion gate: another character may buy the box.

Explicit consumer fallback requires a finite positive bag count, preserving
native nonempty requiredSourceItems, actual confirmed offers, faction/class
checks, broad browsing and active ready turn-ins. Guide note explains the box
and its source. Provider rows remain unchanged. Inventory events refresh both
maps using existing invalidation.

Sources: https://www.wowhead.com/forever/quest=96376/state-secrets ;
https://www.wowhead.com/forever/quest=96377/state-secrets#comments ;
https://www.wowhead.com/forever/item=274041/document-box ;
https://www.wowhead.com/forever/quest=96337/more-valuable-than-gold .

Forever smoke test: user screenshot is the false-pickup baseline. Post-fix
client check pending: reload without box, verify no Nazgrel pickup on either
map; acquire a box and verify delivery appears, then remove it and verify
refresh. Inspect guide note layout and a genuine ready turn-in.


## Timbermaw reputation (0.4.31)

User screenshot shows five unavailable pickups from Bramblesnap, Rageroar and
Nok. All five lack native requiredMinRep. The November 22 Timbermaw guide
explicitly requires Neutral for the Azshara quest list except The Legashi
Threat and Legashi Horns, and for The Twin Bears and Blackmaw Reclamation.
Added 18 explicit missing-field fallbacks to faction 576 standing 0. Nonempty
native requirements supersede the fallback without mutating provider rows.
No chain dependencies are inferred from series display. Guide notes state
that other turn-ins may still apply. Broad mode, confirmed offers and active
ready turn-ins retain existing behavior. Unknown/nonfinite reputation fails
closed. Existing UPDATE_FACTION invalidation refreshes both maps.

Source: https://www.wowhead.com/forever/guide/reputation/timbermaw-hold-quests-quartermaster-rewards
Firsthand confirmation of Neutral plus separate chain dependencies:
https://www.wowhead.com/forever/quest=86777/master-feardred#comments

Validation: offline boundary tests -1/0/3000 and unknown/NaN; native threshold
precedence, legacy API, all 18 IDs, both map refreshes, broad browsing, guide
note and active ready turn-in. Real-provider checks cover all five screenshot
quests. Forever client smoke: screenshot is baseline; post-fix reload below
Neutral, reputation gain refresh and actual NPC offers still need game testing.


## Kurll fishing chain (0.4.32)

User reports 91611 Deadliest Catch unavailable. Native 91611 lacks all
prerequisites; native 91610 Winter Frontier Fishery already requires either
faction Home on the Range (89001/91488). Firsthand Horde reports identify
Fishing 1 and Home -> Winter -> Deadliest. Add missing-field prerequisite
fallback 91611 <- 91610. Do not require an accepted or objective-complete
Winter quest; require its turn-in. Do not add the obtained shark meat as a
pickup gate. No new level requirement.

Fishing skill 356/1 fallback applies to 91610, 91611 and Alliance Winter
89228 (explicit firsthand confirmation on Alliance Deadliest comments).
Leave Alliance shark 89015 native prerequisites unchanged; reports on its
direct Fishing gate differ. Home on the Range is not gated on Fishing.
Native skill/prerequisite requirements supersede fallbacks. For these explicit
profession gates, unknown or collapsed skills without a positive Fishing rank
do not advertise a pickup. Genuine server offers retain existing behavior.

Sources:
https://www.wowhead.com/forever/quest=91611/deadliest-catch#comments
https://www.wowhead.com/forever/quest=91610/winter-frontier-fishery#comments
https://www.wowhead.com/forever/quest=89015/deadliest-catch#comments

Offline validation covers both map refreshes after skill gain/loss and turn-in,
active-but-ready prerequisite, unknown skill data, native precedence, broad
browsing, ready turn-ins and guide note. Real-provider Horde chain checked.
Forever client smoke: user screenshot is baseline; post-fix reload, guide
layout, actual Kurll offers after both turn-ins plus Fishing 1 remain pending.


## Betrayed legacy tail (0.4.33)

User screenshot confirms old 3506 not offered at the tome, while actual chat
shows 91500 An Explosive Gambit and 91538 Sindorei Tome of Summoning accepted.
Native 3505 already points to 91497 Seals of the Sindorei; 91497 leads to
91500 -> 91531 Revenge Exacted and branches to 91538 -> 91547 -> 91548.
But native 3506 still requires 3505, and 3507 still requires 3506, creating
a second stale tail. Questie blacklist only marks those IDs removed in Cata;
this is a Forever-specific consumer correction, not a provider mutation.

Require actual offers for 3506/3507 in strict mode, preserve broad browsing
and active ready turn-ins. Direct guide notes explain the revised route.
GetNextChainSteps excludes the two unaccepted/uncompleted legacy entries
from reverse links; active or completed legacy history remains inspectable.
Do not alter 3504/3505 or falsely link the Tome branch to Gambit completion.

Sources: user observed quest offers/chat plus native chain fields;
https://www.wowhead.com/forever/quest=91497/seals-of-the-sindorei
https://www.wowhead.com/forever/quest=91538/sindorei-tome-of-summoning
https://www.wowhead.com/forever/quest=91547/sindorei-tome-of-summoning .

Offline checks cover both maps, real-offer restoration, legacy finale, broad
browsing, ready turn-in, guide note and revised next-chain branches; provider
rows remain unchanged. Forever smoke: screenshot is baseline; after reload,
verify old pickup hidden at 59.5,31.3 and real Gambit/Tome turn-ins plus chain
guide preserved. Post-fix client check pending.


## Xylem writ pickup correction (0.4.34)

User screenshot shows actual Accept/Decline for 94316 from Archmage Xylem.
User explicitly confirms no writ in bags or bank, and that accepting it still
requires the writ for completion. This supersedes the earlier inferred owned-
starter pickup requirement for this exact order. No blanket inference for
the remaining 149 orders.

Explicit NPC pickup rule 94316 -> 8379 bypasses only the local writ ownership
gate. Normal faction/class/level and actual negative NPC offer observations
still apply. Render only Xylem as an ordinary pickup, not item-source areas
or a Use writ reference; item-started toggle does not hide it. Guide note
distinguishes accepting from completion. Native objectives and starter item
264116 are untouched. Active ready turn-ins remain independent.

Source: user screenshot and explicit in-game inventory/acceptance report,
November 27, 2026. Offline checks cover both maps, no-writ inventory, guide
note, positive/negative offers, item-start toggle and ready turn-ins, plus
the remaining 149 ownership gates. Real QuestieDB profile checks cover actual
Xylem pickup. Client smoke baseline: actual offer confirmed by user; post-fix
reload/marker and guide layout check pending.


## Magatha Remote Contact (0.4.35)

User confirms 91737 not offered and already accepted/completed Stealing
Knowledge or Delivery to Magatha. This is consistent with an obsolete
referral, but does not establish the exact server closure condition. Native
91734/91735/91737 are mutually exclusive; all have breadcrumbForQuestId=0,
no prerequisites and no availableUntilCompleted flag. Wowhead presents the
referrals before Stealing Knowledge. Do not infer a mandatory prerequisite
or manufacture a confirmed breadcrumb flag from that series display alone.

Conservative exact-ID offer-only policy for 91737, with a guide note naming
Jediga and Stealing Knowledge. An actual positive server offer restores it
even after downstream completion; a negative list hides it. Other two
referrals and native exclusivity remain unchanged. Broad browsing and ready
turn-ins retained. Source: user screenshot and reply; quest text/series at
https://www.wowhead.com/forever/quest=91737/remote-contact and
https://www.wowhead.com/forever/quest=3517/stealing-knowledge .

Offline regression: both map pickups, positive/negative offer observations,
downstream completion with true offer, guide note, broad mode, ready return
and unchanged provider fields. Real-provider offer-only behavior checked.
Forever smoke baseline: user confirms unavailable after chain progress;
post-fix reload at Magatha and guide layout remain pending.


## Skipped breadcrumb acceptance warnings (0.4.36)

QUEST_ACCEPTED handler initialized only after successful database init. Uses
recorded destination breadcrumbs lists, matching Questie source semantics;
no series/title guesses or full graph scans on acceptance. Standard Forever
event index/ID supported; omitted ID resolves C_QuestLog.GetInfo(index).
Secret/invalid IDs ignored. Native unknown links yield no warning.

Exclude completed/active breadcrumbs, wrong race/class and unsupported season
via shared applicability helper, active/completed exclusives, and completed
availableUntilCompleted. Ordinary level/map pickup visibility does not erase
a useful referral warning. Locations use the existing provider-backed route
formatter, including item starters and unknown-location fallback.

Default per-character breadcrumbWarnings boolean plus custom Filters and
native settings checkboxes. No quest log writes or protected UI interaction.
Event-driven only; up to five rows plus omission note, 128 source-reference
scan cap, at most 64 recent destination IDs suppress repeat-event spam. No
login replay. Native changes to quests and provider tables are never made.

Validation: acceptance/event-ID fallback, race/class/alternative filters,
active/completed exclusion, note content/location, toggle, missing data,
bounded messages/history and provider integration. Forever smoke test
pending: accept a quest with a recorded uncompleted referral, verify one chat
warning and its giver/location, then disable the checkbox and verify silence.


## All Remote Contact referrals (0.4.37)

User reports Andron Gant false pickup and requests all versions fixed. Apply
existing conservative offer-only policy to 91734 (Andron 6522), 91735
(Jesrimon 8659) and 91737 (Magatha 4046). No new inferred breadcrumb or
reputation gate. Individual guide notes identify the correct giver.

Regression iterates all three givers on both maps: initially hidden, only
that giver restored by actual offer, negative list hides it, ready turn-in
remains, broad browsing shows all. Real-provider scan asserts all quests
named Remote Contact are covered (three currently), plus actual offers and
unchanged native data. Forever smoke: Andron screenshot is baseline; reload
and check Undercity/Orgrimmar/Thunder Bluff pickups and guide notes pending.
