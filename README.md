# QuestLite

This repository contains **[QuestLite](QuestLite/README.md)**, a focused
quest map and loot sparkle addon for World of Warcraft: Forever. Source and
installable addon files are in `QuestLite/`.

The package requires the separately installed QuestieDB addon. Disable Questie
and ForeverLootSparkles when using this replacement.

Development checks (Python 3, `lupa`, and `cbor2` for the database integration):

```powershell
python -m pip install --target .tools -r tests/requirements.txt
python tests/test_addon.py
python tests/check_installed_database.py 'F:/World of Warcraft/_forever_/Interface/AddOns/QuestieDB'
python tools/package.py
```

No Python dependencies are needed by the addon or included in its ZIP.
