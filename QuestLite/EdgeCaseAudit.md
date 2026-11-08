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
