# QuestLite and the add-on workspace

- QuestLite is the Git repository at this path. For the location of another add-on's checkout, use [ADDONS.md](ADDONS.md). Start new Forever add-ons with the `wow-addon-scaffold` skill and default to `checkouts/<AddonName>/` for their independent repositories.
- Keep QuestLite's installable files under `QuestLite/`. Use its private add-on namespace and initialize per-character settings on QuestLite's `ADDON_LOADED`. Preserve existing saved variable names and migration behavior.
- Run `python tests/test_addon.py` and `python tests/test_package.py`. Run `tests/check_installed_database.py` against installed QuestieDB when a change affects the database integration.
- Build with `python tools/package.py`. Keep runtime files, required assets, player documentation, and license notices in the ZIP. Keep internal audits in the checkout. Record a Forever client smoke test for changes to map integration, tooltip hooks, or protected UI behavior.
