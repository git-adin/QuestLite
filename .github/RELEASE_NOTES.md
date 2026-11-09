Download **QuestLite.zip** below and extract it into your WoW Forever
`_forever_/Interface/AddOns/` folder. The result should be
`AddOns/QuestLite/QuestLite.toc`.

Also install the **Forever** version of
[QuestieDB](https://www.curseforge.com/wow/addons/questiedb/files/all), then restart
WoW and enable both QuestLite and QuestieDB in the AddOns list. Use `/ql` for options.
Disable Questie and Forever Loot Sparkles when using QuestLite to avoid duplicate
markers and competing sparkle settings.

For updates, replace the existing `QuestLite` folder; your character settings are
stored separately in `WTF` and are preserved. GitHub's **Source code** archives
are for development; use the attached addon ZIP for installation.

A draggable gold **!** minimap button opens QuestLite options. Its position is
saved per character, and it can be hidden independently of quest markers.
The main world map now also has a gold **!** options button at the upper left,
alongside other map controls.

Scout Support now waits for the Battle of Hillsbrad part II turn-in, and Valuable
Vantages waits for Scout Support. These fill missing database prerequisite links.

Repeatable quests use blue pickup and turn-in icons on both maps, with a
**Repeatable** tooltip label. Mixed groups keep a yellow icon when their displayed
quest type also includes regular quests. Quest titles retain level-based colours.

This release also includes the availability, class/faction and Paladin chain
corrections, plus a recorder for diagnosing blocked interface actions (`/ql errors`).
The protected-action warning remains under investigation. Offline Lua tests run
before packaging; they do not reproduce the game's protected execution or renderer.
