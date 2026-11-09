-- SPDX-License-Identifier: GPL-3.0-or-later
local addon, ns = ...
ns.name = addon
ns.defaults = { map = true, minimap = true, available = true, turnins = true, filterAvailable = true, showLowLevel = false,
    dropChances = true, enabled = true, sparkleOre = true, sparkleHerbs = true, sparkleQuest = true,
    sparkleCorpseLoot = true, sparkleOther = true }

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
    ns.db.objectives = nil -- Retire the old objective-marker setting.
    ns.db.filterLevel, ns.db.levelsAbove = nil, nil
    if type(ns.db.savedCVars) ~= "table" then ns.db.savedCVars = nil end
    for key, default in pairs(ns.defaults) do
        if type(ns.db[key]) ~= "boolean" then ns.db[key] = default end
    end
    for key, default in pairs({levelsBelow = 5}) do
        local value = ns.db[key]
        if type(value) ~= "number" or value ~= value or value < 0 or value > 80 then value = default end
        ns.db[key] = math.floor(value)
    end
end

function ns.RegisterMapOptions(category)
    for _, row in ipairs({ {"map", "Show world map markers"},
        {"minimap", "Show minimap quest icons"},
        {"available", "Quest pickups"},
        {"filterAvailable", "Hide unavailable quest pickups"},
        {"showLowLevel", "Show low level quests"},
        {"dropChances", "Show quest item drop chances"},
        {"turnins", "Quest turn-ins"} }) do
        local key = row[1]
        local setting = Settings.RegisterAddOnSetting(category, "QUESTLITE_" .. key:upper(),
            key, ns.db, Settings.VarType.Boolean, row[2], ns.defaults[key])
        setting:SetValueChangedCallback(function() if ns.RequestMap then ns.RequestMap() end end)
        Settings.CreateCheckbox(category, setting, key == "filterAvailable" and
            "Hide pickups blocked by known requirements or a recently checked NPC offer list. Turning this off shows locked quests too. Completed, active, wrong-class and wrong-race quests remain hidden. Server-only conditions may still differ."
            or key == "showLowLevel" and "Show all low-level pickups, ignoring the normal level cutoff below. Availability requirements still apply. Ready turn-ins stay visible either way."
            or key == "dropChances" and "Show source-specific database drop-rate estimates for active quest items in item and creature hover tooltips. Actual Forever server rates may differ."
            or key == "minimap" and "Show nearby quest pickups and turn-ins on the minimap. Uses the same availability filter, without objective icons. Works independently of world map markers."
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
        local ok, reason = ns.InitDatabase()
        if ok then
            if ns.InitDropChances then ns.InitDropChances() end
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
        ns.Print(ns.mapStatus or "Map is not initialized.")
        ns.Print("Availability filter: " .. (ns.db.filterAvailable and "on" or "off"))
        ns.Print(ns.db.showLowLevel and "Low level quests: all shown, subject to availability."
            or string.format("Minimum pickup level: %d (your level minus %d). No extra upper-level cutoff.",
                math.max(1, UnitLevel("player") - ns.db.levelsBelow), ns.db.levelsBelow))
        if ns.minimapStatus then ns.Print(ns.minimapStatus) end
        if UpdateAddOnMemoryUsage then UpdateAddOnMemoryUsage() end
        if GetAddOnMemoryUsage then
            ns.Print(string.format("Memory: guide %.0f KB; QuestieDB %.0f KB (shared dependency).",
                GetAddOnMemoryUsage(addon) or 0, GetAddOnMemoryUsage("QuestieDB") or 0))
        end
    elseif command == "errors" then
        local argument = (message or ""):lower():match("^%s*%S+%s*(.-)%s*$")
        if ns.ReportBlockedActions then ns.ReportBlockedActions(argument == "clear") end
    elseif command == "refresh" then
        if ns.RequestMap then ns.RequestMap(nil, "FORCE_REFRESH") end
    elseif command == "off" then
        ns.LoadSettings()
        for key in pairs(ns.defaults) do ns.db[key] = false end
        if ns.RefreshSoftTargets then ns.RefreshSoftTargets() end
        if ns.DisableLootSparkles then ns.DisableLootSparkles() end
        if ns.RequestMap then ns.RequestMap() end
        ns.Print("Features off. Restart the game to remove quest sparkles already enabled by the client.")
    elseif ns.category and Settings and Settings.OpenToCategory then
        Settings.OpenToCategory(ns.category:GetID())
    else
        ns.Print("Use /ql status, /ql errors, /ql refresh or /ql off.")
    end
end
