# Retiring custom soft-target sparkles — 0.4.0

The installed Forever Loot Sparkles 2.0.0 removes its custom herb, ore, corpse and
quest-object glints. Its changelog reports interference with untargeted friendly
spells, empty corpse nameplates and unwanted interaction icons. QuestLite's
custom engine was adapted from its 1.3.1 code and used the same mechanism.

QuestLite now removes the custom engine and flare texture rather than attempting
to work around spell targeting. Built-in quest loot sparkles, maps, drop chances
and the blocked-action recorder remain. No soft-interaction or nameplate event
handlers, unit polling, custom sparkle animation or sparkle-category options
remain loaded. This does not establish the cause of earlier blocked-action counts.

## Saved settings

`SoftTargetCleanup.lua` reads only QuestLite's own saved originals, including
settings imported from ForeverGuide. It restores these known managed CVars:

- `SoftTargetInteract` (formerly set to 3)
- `SoftTargetNameplateInteract` (formerly toggled between 0 and 1)
- `SoftTargetInteractRange` (60)
- `SoftTargetInteractArc` (2)
- `SoftTargetInteractOnlyInRange` (0)
- `SoftTargetIconGameObject` (1)
- Legacy `SoftTargetIconInteract` and `SoftTargetLowPriorityIcons` (1)

Restoration is skipped if the current value differs from what QuestLite used to
write, preserving detectable player changes. Only finite numeric originals are
written; unrelated saved keys are never applied. With no saved original, nothing
is guessed or reset. Cleanup runs at login and once after five seconds to catch
late account synchronization, even with quest-loot sparkles disabled. Combat
defers restoration until `PLAYER_REGEN_ENABLED`. Successful final cleanup clears
the old originals; failed writes keep them for a later login instead of polling.

Limits: a player-selected value identical to QuestLite's old value cannot be
distinguished from an addon-written value. The old nameplate setting only used
0/1, so its saved baseline is restored. Changes by other addons after cleanup or
sync arriving beyond the migration window are outside this migration's control.
No other addon's saved variables are read or changed.

## Validation

Offline tests check fresh installs make no soft-target writes or unit probes,
the old sparkle options are absent, existing saves are cleaned, late sync is
restored, detectable player edits survive, malformed/unknown values are skipped,
failed writes retain originals, and combat deferral works with loot sparkles off.
Built-in sparkle reapplication after graphics changes and combat shutdown remain
covered. In-game verification after reload is still required.
