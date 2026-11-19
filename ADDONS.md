# WoW Forever add-on workspace

Run development and release commands from the add-on's own checkout. The table paths are relative to this Windows workspace.

| Add-on | Checkout | Baseline checks | Upstream |
| --- | --- | --- | --- |
| QuestLite | `.` | `python tests/test_addon.py` and `python tests/test_package.py` | [QuestLite](https://github.com/git-adin/QuestLite) |
| HunterLens | `HunterLens/` | `python tests/test_addon.py` and `python tests/test_package.py` | [HunterLens](https://github.com/git-adin/HunterLens) |
| ItemFarmingTool | `ItemFarmingTool/` | `python tests/test_addon.py` and `python tests/test_package.py` | [ItemFarmingTool](https://github.com/git-adin/ItemFarmingTool) |
| ProfessionGuide | `ProfessionGuide/` | `python tests/test_addon.py` and `python tests/test_package.py` | [ProfessionGuide](https://github.com/git-adin/ProfessionGuide) |
| AuctionPriceLite | `checkouts/AuctionPriceLite/` | `python tests/test_addon.py` and `python tests/test_package.py` | [AuctionPriceLite](https://github.com/git-adin/AuctionPriceLite) |
| WritCrateLite | `checkouts/WritCrateLite/` | `python tests/test_writ_crate.py` and `python tests/test_package.py` | [WritCrateLite](https://github.com/git-adin/WritCrateLite) |

The loose `AuctionPriceLite/` and `WritCrateLite/` folders at the workspace root are snapshots. Make edits and build from the matching `checkouts/` repository.

From any checkout, run `python -m pip install --target .tools -r tests/requirements.txt` for offline Lua tests and `python tools/package.py` for a local build. For a release candidate use `python tools/package.py --tag vX.Y.Z`, replacing the tag with the version in the add-on's TOC. The checkout's own `dist/` contains its installable ZIPs and checksum manifest.

QuestLite can check installed QuestieDB data with `tests/check_installed_database.py`. From the WritCrateLite checkout, run `python tests/check_pricing_integration.py --auction-checkout ../AuctionPriceLite` to load the real pricing provider. The ProfessionGuide suite exercises the real ItemFarmingTool API when the sibling checkout is present.

## Starting another add-on

Start in this workspace and ask Codex to create a WoW Forever add-on, or explicitly invoke `$wow-addon-scaffold`. The [project skill](.agents/skills/wow-addon-scaffold/SKILL.md) includes the starter template. Put a new independent checkout under `checkouts/` by default. Open the generated repository for feature work so Codex reads its own `AGENTS.md`. Check the target client's TOC interface number and run the generated tests and packager before the first commit.

[Rollout plan](ADDON_ROLLOUT_PLAN.md)
