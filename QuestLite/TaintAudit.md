# Combat map pins and cooldown diagnostics — 0.4.3

## Confirmed QuestLite issue

Saved QuestLite blocked-action histories inspected on 2026-11-09 repeatedly show
`ADDON_ACTION_BLOCKED: Frame:SetPassThroughButtons()` in combat. Their stacks
reach `MapCanvasPinMixin:CheckMouseButtonPassthrough` through
`WorldMapFrame:AcquirePin`, called by QuestLite's map publication path. This is
direct evidence of a QuestLite combat-publishing bug.

The [client UI source](https://github.com/Gethe/wow-ui-source/blob/forever/Interface/AddOns/Blizzard_MapCanvas/MapCanvas_DataProviderBase.lua)
configures mouse passthrough whenever a native MapCanvas pin is acquired.
QuestLite now cancels pending/running world-map publication in combat, hides
existing owned world pins and coalesces refreshes until `PLAYER_REGEN_ENABLED`.
Acquisition, release, clearing and cached publication wait until combat ends.
Minimap frames use no MapCanvas mouse-passthrough calls and continue updating.

## Separate reported cooldown error

The user's repeated `ActionButton.lua` error occurs at `SetCooldown` with secret
start, duration and modifier values while an action-bar ability is used. That
stack contains Blizzard's cooldown handler and event dispatcher, but does not
identify the addon or reference that introduced taint. It does not prove the
combat map issue caused the cooldown error. There is no local taint log proving
that connection. No root cause is claimed yet.

QuestLite does not hook action-bar/cooldown functions, write action-button fields
or replace Blizzard's cooldown handling. The installed Leatrix Plus code has an
action-button post-hook, but its presence alone is not evidence that it caused
this error. No other addon was modified or disabled.

`/ql taint` reads `issecurevariable` for the two cooldown functions, shared
action-bar event frames and the reported bottom-right button's references. It
reports the recorded owner of tainted references without reading cooldown
values, adding action-bar hooks or writing those references. A secure snapshot
does not rule out other tainted execution paths. `/ql errors` retains the
bounded blocked-action history; `/ql status` now prints the loaded version.

## Validation and live follow-up

Offline regressions reject any map acquisition/release/clear during combat,
exercise cold maps, cached reopening, zone changes, a scan interrupted by combat
and a map closed before combat ends. They verify automatic post-combat recovery
and continuing minimap markers. Diagnostic tests verify read-only operation and
API-unavailable handling. These checks cannot emulate the game's taint engine.

Reload to clear the previous UI session, reproduce the action-bar use, then run
`/ql taint` and `/ql errors` if the cooldown error returns. Use the resulting
ownership evidence before changing more behavior. Old saved history entries
are preserved and may describe the pre-fix session.
