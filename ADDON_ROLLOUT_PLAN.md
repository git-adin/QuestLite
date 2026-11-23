# WoW Forever add-on rollout plan

## 1. Establish the release source for each add-on

- Use the existing Git checkout for each add-on as the source for releases. Record checkout locations and configured upstream repositories in the [workspace index](ADDONS.md). Give AuctionPriceLite and WritCrateLite durable checkout locations outside `dist/` so build cleanup cannot remove a checkout.
- Compare the loose AuctionPriceLite and WritCrateLite copies with their checkouts and inspect working-tree status. Preserve any local-only changes. Move the combined pricing integration test out of the QuestLite workspace root into the WritCrateLite checkout, with an explicit path to the AuctionPriceLite checkout for the paired run. Keep WritCrateLite's standalone tests runnable without AuctionPriceLite installed.
- Rebuild the local WritCrateLite stable ZIP from the chosen checkout. Its current workspace copy contains AuctionPriceLite and older WritCrateLite code. Use the matching versioned ZIP as a baseline and keep the previous bundle identifiable until the replacement passes package checks.

**Done when** each add-on has a documented checkout and build command, both pricing test modes pass, and the replacement WritCrateLite ZIP contains only the intended version of WritCrateLite. This phase concerns local artifacts and does not require publishing a release.

## 2. Standardize package checks and CI

- Pilot on WritCrateLite using the ItemFarmingTool tests and HunterLens validation workflow as references. Build from a clean checkout. Include TOC entries, files referenced by XML, explicitly listed runtime assets, player-facing documentation, and required licenses or attribution. Keep development audits and tooling outside the install ZIP.
- Add package checks for one top-level `<AddonName>/` folder, a matching `<AddonName>.toc`, all required files, and the expected contents. Verify that a mismatched release tag fails. Build the versioned ZIP once, copy it to the stable asset name, and generate matching checksums.
- Run offline behavior and package checks on pull requests. Use the same checks for tagged releases. Validate the package before creating a draft release and publish only after all expected assets upload.
- Roll out to AuctionPriceLite next, adding focused scan and cache tests alongside its packaging checks. Give QuestLite pull-request checks and narrow its ZIP contents. Add CI, tag validation, and package tests to ProfessionGuide. Align HunterLens and ItemFarmingTool where their existing checks differ from the agreed contract.

**Done when** every checkout passes its local build and CI checks, and each verified ZIP extracts directly into `Interface/AddOns/<AddonName>/`. Record a live Forever smoke test for changes involving game APIs, tooltips, combat restrictions, or addon load order.

**Live Forever smoke tests, November 23, 2026.** The player confirmed all five checks for the installed builds.

| Add-on | Verified in game |
| --- | --- |
| QuestLite 0.4.23 | Known quest-item drop rates, clean tooltips when no rate is available, and the quest guide opening from a world-map marker. See the [compatibility audit](QuestLite/CompatibilityAudit.md). |
| AuctionPriceLite 0.3.2 | Full Auction House scan, fresh scan status, item and stack estimates, and expanded tooltip details. |
| WritCrateLite 0.2.2 | Writ and crate pricing through AuctionPriceLite after the same scan. |
| ProfessionGuide 0.5.2 | Blacksmithing finishing routes and shopping-list updates when switching alternatives. |
| HunterLens 0.1.10 | Known beast teaching rank, expanded Shift tooltip, and a clean `/hl debug` check. |

## 3. Fix ProfessionGuide's farming-goal export

1. Add and document a small public ItemFarmingTool API for reading tracked goals and applying a batch of minimum goals. Validate the whole batch inside ItemFarmingTool before modifying state. Return success or a reason for failure. Preserve unrelated entries and existing higher goals.
2. Ship the provider API first. Update ProfessionGuide to detect the API, call it only on explicit export, and update export history only after success. With ItemFarmingTool absent or older than the API, keep profession planning available and show a clear export status.
3. Run the existing paired integration test against both proposed changes. Verify repeat exports, invalid input, capacity rejection with zero partial writes, preserved higher goals, and the absent or older provider cases. Smoke-test an export with both add-ons enabled in Forever.

**Done when** the integration uses the public API for reads and writes and the slash commands still work for players.

**Live Forever smoke test, November 18, 2026.** The player confirmed that exporting a ProfessionGuide route preserved existing ItemFarmingTool goals and added the new goals. Exporting the same route again added no duplicates. This covers the paired export with both add-ons enabled.

## 4. Carry the defaults into new repositories

- Create one starter template with an installable `<AddonName>/` directory, a minimal Lua entry point, `tests/`, `tools/`, CI, and a root `AGENTS.md`. Let the next new add-on pilot it. Keep existing repository layouts until moving files solves a concrete problem.
- Put durable conventions in each repo's `AGENTS.md`. Include the target client, local check commands, release contract, and Lua conventions. Use the add-on namespace for private code, initialize SavedVariables after the add-on's `ADDON_LOADED` event, and add a module when a distinct responsibility warrants it. Verify the target client's TOC interface value for new projects. [Codex project instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- Create one `wow-addon-scaffold` skill that uses the starter template. Start in the add-on workspace. If new add-ons are regularly initiated from unrelated directories or fresh repos, make the scaffold skill user-scoped so Codex can discover it there. A repo-scoped skill is discovered within its repository path. Codex can select a skill when its description matches the task, and explicit invocation is available when needed. Add a separate release skill only if a recurring release workflow benefits from one. [Codex skills and discovery](https://learn.chatgpt.com/docs/build-skills)
- Test the setup in a fresh Codex session from the add-on workspace and from the generated repository. Verify that a plain request to create a WoW Forever add-on can select the skill, that the new repo reads its own guidance, and that CI rejects a deliberately malformed package.

**Done when** a new add-on starts with working checks and project guidance on its first commit. CI enforces the package contract even if skill selection varies.
