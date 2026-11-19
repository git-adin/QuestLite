# QuestLite

Quest pickup locations, turn-in markers, quest tooltips and loot sparkles for
**World of Warcraft: Forever**. Leaves quest objective markers to Blizzard.

Version 0.4.0 keeps built-in quest-loot sparkles and removes custom soft-target
sparkles that could interfere with spell targeting, nameplates and interact icons.
It restores the interaction settings saved by older QuestLite versions.

## Download and install

**[Download QuestLite.zip](https://github.com/git-adin/QuestLite/releases/latest/download/QuestLite.zip)**
Â· [All releases](https://github.com/git-adin/QuestLite/releases)

1. Close WoW. Download **QuestLite.zip** using the link above.
2. Extract the ZIP into your WoW installation's `_forever_/Interface/AddOns/`
   folder. You should have `AddOns/QuestLite/QuestLite.toc` directly inside it.
3. Install the **Forever** build of
   **[QuestieDB](https://www.curseforge.com/wow/addons/questiedb/files/all)** in
   the same AddOns folder. QuestieDB is required and downloaded separately.
4. Start WoW and enable **QuestLite** and **QuestieDB** in the character selection
   AddOns list. Disable Questie and Forever Loot Sparkles to avoid duplicate
   markers and competing sparkle settings.
5. Open `/ql` or click a QuestLite map button for the tabbed options window. Left-click quest markers for prerequisites, or search part of a quest name in the Prerequisites tab.

Download the addon ZIP from **Releases**. GitHub's green **Code > Download ZIP**
button downloads the development repository, which has an extra folder layer.
No Python or developer tools are needed to play.

To update, close WoW and replace just the `QuestLite` folder with the new release.
Your settings live separately in `WTF` and are preserved. If migrating from
ForeverGuide, see the [migration instructions](QuestLite/README.md#install-and-use).

[Features, settings and known limitations](QuestLite/README.md).

## Development

Development checks (Python 3, `lupa`, and `cbor2` for the database integration):

```powershell
python -m pip install --target .tools -r tests/requirements.txt
python tests/test_addon.py
python tests/test_package.py
python tests/check_installed_database.py 'F:/World of Warcraft/_forever_/Interface/AddOns/QuestieDB'
python tools/package.py
```

No Python dependencies are needed by the addon or included in its ZIP.

## Publishing a release

Update `## Version:` in `QuestLite/QuestLite.toc`, the addon README heading, and
`.github/RELEASE_NOTES.md`. Commit and push the changes, then tag that commit:

```powershell
git tag v0.3.3
git push origin v0.3.3
```

Use the new version's tag for subsequent releases. Pull requests and pushes to
`main` run the offline behavior and package checks. A version tag adds a TOC
version check and publishes an installable
ZIP, a versioned copy and SHA-256 checksums. It publishes only after all assets
have uploaded. The download link above always points to the latest release.
The installed-database integration check remains a local check requiring QuestieDB.
