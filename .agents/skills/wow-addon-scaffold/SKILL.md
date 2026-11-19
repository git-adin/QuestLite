---
name: wow-addon-scaffold
description: Scaffold a new World of Warcraft addon as a standalone project with a matching TOC, Lua starter, tests, and release workflow. Use for new WoW Forever addons and other new WoW addons with a specified target client.
---

# Scaffold a World of Warcraft addon

Use the requested add-on name and target client. Keep the install folder and TOC basename identical. If the display name contains spaces or punctuation, pass a filesystem-safe identifier as the add-on name and retain the requested name with `--title`.

Verify the TOC interface value for the target client. In game, run `/dump select(4, GetBuildInfo())`. The scaffold defaults to `16001`, the current workspace baseline for Forever. Use `--interface` when the verified value differs. Use `--client` for the client label and `--client-folder` for its install-folder segment when targeting a different client.

Run this helper from the selected project parent, using the script path relative to this skill:

```text
python scripts/scaffold.py AddonName --destination <new-project-directory>
```

The helper creates a new directory and copies the packaged template into it. If the requested directory already exists, inspect it and adapt the files needed for the task. Use the repo's generated `AGENTS.md` when implementing the requested features. The sample slash command provides a quick smoke test and can be replaced by the add-on's actual entry point.

Initialize a standalone local Git repository if creating a new checkout. Run the generated offline Lua and package checks with the README commands. Review the ZIP layout and verify any requested game-facing behavior in the target client when a live check is available.
