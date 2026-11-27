-- SPDX-License-Identifier: GPL-3.0-or-later
local addon, ns = ...
ns.name = addon
ns.defaults = { map = true, minimap = true, available = true, turnins = true, filterAvailable = true, showLowLevel = false, hidePvPQuests = false, hideClothQuests = false,
    minimapButton = true, itemDropLocations = true, dropChances = true, questItemSafety = true, breadcrumbWarnings = true, enabled = true }

function ns.Print(message)
    print("|cff80dfffQuestLite:|r " .. tostring(message))
end

function ns.IsSecret(value)
    return issecretvalue and issecretvalue(value)
end

function ns.IsFiniteNumber(value)
    return not ns.IsSecret(value) and type(value) == "number" and value == value
        and value > -math.huge and value < math.huge
end

function ns.Safe(func, ...)
    if type(func) ~= "function" then return nil end
    local ok, value = pcall(func, ...)
    if ok and not ns.IsSecret(value) then return value end
end

function ns.LoadSettings()
    if ns.db then return end
    if type(QuestLiteDB) ~= "table" then
        QuestLiteDB = type(ForeverGuideDB) == "table" and ForeverGuideDB or {}
    end
    ForeverGuideDB = nil -- Imported once from a migrated legacy saved-variable file.
    ns.db = QuestLiteDB
    if type(ns.db.hiddenQuests) ~= "table" then ns.db.hiddenQuests = {} end
    for id, hidden in pairs(ns.db.hiddenQuests) do
        if not ns.IsFiniteNumber(id) or id <= 0 or id ~= math.floor(id) or hidden ~= true then
            ns.db.hiddenQuests[id] = nil
        end
    end
    ns.db.objectives = nil -- Retire the old objective-marker setting.
    ns.db.filterLevel, ns.db.levelsAbove = nil, nil
    if type(ns.db.savedCVars) ~= "table" then ns.db.savedCVars = nil end
    for _, key in ipairs({"sparkleOre", "sparkleHerbs", "sparkleQuest", "sparkleCorpseLoot", "sparkleOther"}) do
        ns.db[key] = nil -- Retired: custom glints depended on interaction targeting.
    end
    for key, default in pairs(ns.defaults) do
        if type(ns.db[key]) ~= "boolean" then ns.db[key] = default end
    end
    for key, default in pairs({levelsBelow = 5}) do
        local value = ns.db[key]
        if type(value) ~= "number" or value ~= value or value < 0 or value > 80 then value = default end
        ns.db[key] = math.floor(value)
    end
    if not ns.IsFiniteNumber(ns.db.minimapButtonAngle) then ns.db.minimapButtonAngle = 225 end
    ns.db.minimapButtonAngle = ns.db.minimapButtonAngle % 360
end

function ns.RegisterMapOptions(category)
    for _, row in ipairs({ {"map", "Show world map markers"},
        {"minimap", "Show minimap quest icons"},
        {"minimapButton", "Show QuestLite minimap button"},
        {"available", "Quest pickups"},
        {"itemDropLocations", "Show item-started quests"},
        {"filterAvailable", "Hide unavailable quest pickups"},
        {"hidePvPQuests", "Hide PvP quest pickups"},
        {"hideClothQuests", "Hide cloth donation pickups"},
        {"showLowLevel", "Show low level quests"},
        {"dropChances", "Show quest item drop chances"},
        {"questItemSafety", "Quest item cleanup notes"},
        {"breadcrumbWarnings", "Warn about skipped breadcrumbs"},
        {"turnins", "Quest turn-ins"} }) do
        local key = row[1]
        local setting = Settings.RegisterAddOnSetting(category, "QUESTLITE_" .. key:upper(),
            key, ns.db, Settings.VarType.Boolean, row[2], ns.defaults[key])
        setting:SetValueChangedCallback(function()
            if key == "questItemSafety" and ns.RefreshQuestItemSafety then ns.RefreshQuestItemSafety()
            elseif key == "minimapButton" and ns.UpdateMinimapButton then ns.UpdateMinimapButton()
            elseif ns.RequestMap then ns.RequestMap() end
        end)
        Settings.CreateCheckbox(category, setting, key == "filterAvailable" and
            "Hide pickups blocked by known requirements or a recently checked NPC offer list. Turning this off shows locked quests too. Completed, active, wrong-class and wrong-race quests remain hidden. Server-only conditions may still differ."
            or key == "hideClothQuests" and "Hide wool, silk, mageweave and runecloth reputation donation pickups, including repeatable runecloth donations, on both maps. Ready turn-ins stay visible. Other quests involving cloth are unaffected."
            or key == "hidePvPQuests" and "Hide PvP-tagged quest pickups on both maps, including known Questie tag corrections. Ready turn-ins remain visible. This applies even when browsing unavailable quests."
            or key == "showLowLevel" and "Show all low-level pickups, ignoring the normal level cutoff below. Availability requirements still apply. Ready turn-ins stay visible either way."
            or key == "itemDropLocations" and "Show dropped quest starters on both maps: source areas, or known turn-in destinations for zone-wide drops. The dropped item is still required. Turn off to hide these references; NPC pickups, ready turn-ins and drop-rate tooltips are unaffected."
            or key == "dropChances" and "Show source-specific database drop-rate estimates for active quest items in item and creature hover tooltips. Actual Forever server rates may differ."
            or key == "questItemSafety" and "Show Keep or finished quest-use notes on item tooltips. Checks known quests for this character, including future steps and repeatable turn-ins. Items are never deleted automatically."
            or key == "breadcrumbWarnings" and "When accepting a quest, warn in chat about known, unaccepted breadcrumb quests you may have skipped, including their pickup locations."
            or key == "minimap" and "Show nearby quest pickups and turn-ins on the minimap. Uses the same availability filter, without objective icons. Works independently of world map markers."
            or key == "minimapButton" and "Show a draggable QuestLite button around the minimap. Click it to open options."
            or "Draw quest locations on the map. Hover for details.")
    end
    for _, row in ipairs({{"levelsBelow", "Normal level limit (levels below mine)", 5}}) do
        local setting = Settings.RegisterAddOnSetting(category, "QUESTLITE_" .. row[1]:upper(),
            row[1], ns.db, Settings.VarType.Number, row[2], row[3])
        setting:SetValueChangedCallback(function() if ns.RequestMap then ns.RequestMap() end end)
        local options = Settings.CreateSliderOptions(0, 80, 1)
        if MinimalSliderWithSteppersMixin and MinimalSliderWithSteppersMixin.Label then
            options:SetLabelFormatter(MinimalSliderWithSteppersMixin.Label.Right, function(value) return tostring(math.floor(value)) end)
        end
        Settings.CreateSlider(category, setting, options, "When Show low level quests is off, hide pickups more than this many levels below your character. Default: 5. Turning Show low level quests on bypasses this cutoff. Ready turn-ins are unaffected.")
    end
end

local events = CreateFrame("Frame")
events:RegisterEvent("ADDON_LOADED")
events:RegisterEvent("PLAYER_LOGIN")
events:SetScript("OnEvent", function(self, event, name)
    if event == "ADDON_LOADED" and name == addon then
        ns.LoadSettings()
        self:UnregisterEvent("ADDON_LOADED")
    elseif event == "PLAYER_LOGIN" then
        ns.LoadSettings()
        if ns.InitMinimapButton then ns.InitMinimapButton() end
        local ok, reason = ns.InitDatabase()
        if ok then
            if ns.InitBreadcrumbWarnings then ns.InitBreadcrumbWarnings() end
            if ns.InitDropChances then ns.InitDropChances() end
            if ns.InitQuestItems then ns.InitQuestItems() end
            ns.InitMap()
            if ns.InitMinimap then ns.InitMinimap() end
        else ns.Print("Map disabled: " .. tostring(reason)) end
        for _, other in ipairs({"Questie", "ForeverLootSparkles"}) do
            local loaded = C_AddOns and ns.Safe(C_AddOns.IsAddOnLoaded, other)
            if loaded then ns.Print("Disable " .. other .. " when using QuestLite to avoid duplicate markers or competing settings.") end
        end
    end
end)

SLASH_QUESTLITE1 = "/ql"
SLASH_QUESTLITE2 = "/questlite"
SLASH_QUESTLITE3 = "/fg"
SLASH_QUESTLITE4 = "/foreverguide"
SlashCmdList.QUESTLITE = function(message)
    local command = (message or ""):lower():match("^%s*(%S+)")
    if command == "status" then
        ns.Print("Version: " .. tostring(ns.Safe(C_AddOns and C_AddOns.GetAddOnMetadata, addon, "Version") or "unknown"))
        ns.Print(ns.mapStatus or "Map is not initialized.")
        ns.Print("Cloth donation pickups: " .. (ns.db.hideClothQuests and "hidden" or "shown"))
        ns.Print("PvP quest pickups: " .. (ns.db.hidePvPQuests and "hidden" or "shown"))
        ns.Print("Availability filter: " .. (ns.db.filterAvailable and "on" or "off"))
        ns.Print("Quest item drop locations: " .. (ns.db.itemDropLocations and "shown" or "hidden"))
        ns.Print(ns.db.showLowLevel and "Low level quests: all shown, subject to availability."
            or string.format("Minimum pickup level: %d (your level minus %d). No extra upper-level cutoff.",
                math.max(1, UnitLevel("player") - ns.db.levelsBelow), ns.db.levelsBelow))
        if ns.minimapStatus then ns.Print(ns.minimapStatus) end
        if UpdateAddOnMemoryUsage then UpdateAddOnMemoryUsage() end
        if GetAddOnMemoryUsage then
            ns.Print(string.format("Memory: guide %.0f KB; QuestieDB %.0f KB (shared dependency).",
                GetAddOnMemoryUsage(addon) or 0, GetAddOnMemoryUsage("QuestieDB") or 0))
        end
    elseif command == "prereq" then
        local argument = (message or ""):match("^%s*%S+%s*(.-)%s*$")
        if ns.ReportPrerequisites then ns.ReportPrerequisites(argument) end
    elseif command == "cloth" then
        ns.db.hideClothQuests = not ns.db.hideClothQuests
        if ns.RequestMap then ns.RequestMap() end
        ns.Print("Cloth donation pickups: " .. (ns.db.hideClothQuests and "hidden" or "shown"))
    elseif command == "pvp" then
        ns.db.hidePvPQuests = not ns.db.hidePvPQuests
        if ns.RequestMap then ns.RequestMap() end
        ns.Print("PvP quest pickups: " .. (ns.db.hidePvPQuests and "hidden" or "shown"))
    elseif command == "hidden" then
        ns.ShowHiddenQuests()
    elseif command == "unhide" then
        local argument = (message or ""):lower():match("^%s*%S+%s*(.-)%s*$")
        if argument == "all" then ns.RestoreAllQuests()
        else
            local id = tonumber(argument)
            if id and ns.db.hiddenQuests[id] then ns.SetQuestHidden(id, false); ns.Print("Quest pickup restored.")
            else ns.Print("Use /ql hidden, /ql unhide <quest ID>, or /ql unhide all.") end
        end
    elseif command == "drops" then
        ns.db.itemDropLocations = not ns.db.itemDropLocations
        if ns.RequestMap then ns.RequestMap() end
        ns.Print("Quest item drop locations: " .. (ns.db.itemDropLocations and "shown" or "hidden"))
    elseif command == "taint" then
        if ns.ReportTaintState then ns.ReportTaintState() end
    elseif command == "errors" then
        local argument = (message or ""):lower():match("^%s*%S+%s*(.-)%s*$")
        if ns.ReportBlockedActions then ns.ReportBlockedActions(argument == "clear") end
    elseif command == "refresh" then
        if ns.RequestMap then ns.RequestMap(nil, "FORCE_REFRESH") end
    elseif command == "off" then
        ns.LoadSettings()
        for key in pairs(ns.defaults) do ns.db[key] = false end
        if ns.UpdateMinimapButton then ns.UpdateMinimapButton() end
        if ns.RestoreLegacySoftTargets then ns.RestoreLegacySoftTargets(true) end
        if ns.DisableLootSparkles then ns.DisableLootSparkles() end
        if ns.RequestMap then ns.RequestMap() end
        ns.Print("Features off. Restart the game to remove quest sparkles already enabled by the client.")
    elseif ns.OpenOptions then
        ns.OpenOptions("filters")
    elseif ns.category and Settings and Settings.OpenToCategory then
        Settings.OpenToCategory(ns.category:GetID())
    else
        ns.Print("Use /ql status, /ql errors, /ql taint, /ql drops, /ql pvp, /ql cloth, /ql hidden, /ql prereq, /ql refresh or /ql off.")
    end
end
