-- SPDX-License-Identifier: GPL-3.0-or-later
local _, ns = ...
local safe = ns.Safe
local api, initialized, dirty = nil, false, true
local sources, corrections, activeItems, activeKey = {}, {}, {}, nil
local rateCache, cacheCount = {}, 0
local MAX_LINES = 8

local function ValidRate(value)
    return type(value) == "number" and value >= 0 and value <= 100
end

-- Support strings contain numeric data, not code to execute. Index only item
-- row offsets; retain the provider's strings instead of expanding all NPC rows.
local function Source(data)
    return {data = data}
end

local function Read(source, itemID, npcID)
    local data = source.data
    if type(data) == "table" then return data[itemID] and data[itemID][npcID] end
    if type(data) ~= "string" then return nil end
    if not source.offsets then
        source.offsets = {}
        for id, offset in data:gmatch("%[(%d+)%]%s*=%s*{()") do source.offsets[tonumber(id)] = offset end
    end
    local start = source.offsets[itemID]
    if not start then return nil end
    if source.rowID ~= itemID then
        local finish = data:find("}", start, true)
        if not finish then return nil end
        source.rowID, source.row = itemID, data:sub(start, finish - 1)
    end
    return tonumber(source.row:match("%[" .. npcID .. "%]%s*=%s*([%+%-]?[%d%.]+)"))
end

local function Rate(itemID, npcID)
    local key = itemID .. ":" .. npcID
    if rateCache[key] ~= nil then return rateCache[key] or nil end
    local row = corrections[itemID]
    local correction = type(row) == "table" and row[npcID]
    local value
    if ValidRate(correction) then value = correction
    elseif correction == -1 then value = Read(sources.wowhead, itemID, npcID)
    elseif correction == -2 then value = Read(sources.server, itemID, npcID) end
    if not ValidRate(value) then value = Read(sources.server, itemID, npcID) end
    if not ValidRate(value) then value = Read(sources.wowhead, itemID, npcID) end
    if not ValidRate(value) then value = nil end
    if cacheCount >= 128 then rateCache, cacheCount = {}, 0 end
    rateCache[key], cacheCount = value or false, cacheCount + 1
    return value
end

local function Release(entity, id)
    if entity.InvalidateCache then entity.InvalidateCache(id) end
end

local function ActiveItems()
    if not dirty then return activeItems end
    dirty = false
    local key = ns.GetMapStateKey(true)
    if activeKey == key then return activeItems end
    activeItems, activeKey = {}, key
    local function Add(id)
        if type(id) ~= "number" or id <= 0 or activeItems[id] then return end
        local npcs = {}
        for _, npcID in ipairs(api.Item.npcDrops(id) or {}) do npcs[npcID] = true end
        activeItems[id] = {name = api.Item.name(id) or ("Item #" .. id), npcs = npcs}
        Release(api.Item, id)
    end
    local count = safe(C_QuestLog.GetNumQuestLogEntries) or safe(GetNumQuestLogEntries) or 0
    for index = 1, count do
        local info = safe(C_QuestLog.GetInfo, index)
        local id = info and not info.isHeader and info.questID
        if not C_QuestLog.GetInfo and GetQuestLogTitle then
            local _, _, _, header, _, _, _, legacyID = GetQuestLogTitle(index)
            if not header then id = legacyID end
        end
        if type(id) == "number" and id > 0 then
            local objectives = api.Quest.Get(id, "objectives") or {}
            for _, objective in ipairs(objectives[3] or {}) do Add(objective[1]) end
            for _, itemID in ipairs(api.Quest.Get(id, "requiredSourceItems") or {}) do Add(itemID) end
            Release(api.Quest, id)
        end
    end
    return activeItems
end

local function FormatRate(value)
    if not value then return "Unknown" end
    if value > 0 and value < .1 then return "<0.1%" end
    return string.format("%.1f%%", value):gsub("%.0%%", "%%")
end

local function IsProgressItem(text, itemName, suffix)
    -- Match a whole objective item, not "Tooth" inside "Sharp Tooth" or
    -- "Tooth Fragment". Strip visual markup only for matching; keep the
    -- original string intact when inserting the percentage.
    local clean = text:gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", "")
        :gsub("|T.-|t", ""):gsub("|A.-|a", "")
    local first, last = clean:find(itemName, 1, true)
    if not first then return false end
    local before, after = clean:sub(1, first - 1), clean:sub(last + 1)
    if after:sub(1, #suffix) == suffix then after = after:sub(#suffix + 1) end
    return (before:match("%d+%s*/%s*%d+%s*$") and after:match("^%s*$"))
        or (before:match("^%s*$") and after:match("^%s*:?%s*%d+%s*/%s*%d+%s*$"))
end

local function Begin(tooltip, token)
    if not tooltip or not tooltip.AddLine or not tooltip.NumLines then return false end
    if tooltip.QuestLiteDropToken == token and tooltip.QuestLiteDropLines == tooltip:NumLines() then return false end
    tooltip:AddLine("Quest item drop chance (DB estimate)", .5, .8, 1)
    tooltip.QuestLiteDropToken = token
    return true
end

local function Finish(tooltip)
    tooltip.QuestLiteDropLines = tooltip:NumLines()
    tooltip:Show()
end

local function ItemTooltip(tooltip, data)
    if not api or not ns.db.dropChances or ns.IsSecret(data) then return end
    local id = type(data) == "table" and data.id
    if ns.IsSecret(id) then return end
    if not id and tooltip.GetItem then
        local ok, _, link = pcall(tooltip.GetItem, tooltip)
        if ok and not ns.IsSecret(link) and type(link) == "string" then id = tonumber(link:match("item:(%d+)")) end
    end
    if type(id) ~= "number" or not ActiveItems()[id] then return end
    if not Begin(tooltip, "item:" .. id) then return end
    local drops = api.Item.npcDrops(id) or {}
    local shown, known = 0, 0
    for _, npcID in ipairs(drops) do
        local value = Rate(id, npcID)
        if value ~= nil then
            known = known + 1
            if shown < MAX_LINES then
                tooltip:AddDoubleLine(api.Npc.name(npcID) or ("NPC #" .. npcID), FormatRate(value), 1, .85, .3, 1, 1, 1)
                Release(api.Npc, npcID)
                shown = shown + 1
            end
        end
    end
    Release(api.Item, id)
    if known > shown then tooltip:AddLine("And " .. (known - shown) .. " other sources", .7, .7, .7) end
    if shown == 0 then tooltip:AddLine("Unknown: no NPC drop-rate data", .7, .7, .7) end
    Finish(tooltip)
end

local function UnitTooltip(tooltip, data)
    if not api or not ns.db.dropChances or ns.IsSecret(data) then return end
    -- Forever restricts unit tooltip data inside instances. Leave that native
    -- tooltip untouched instead of attempting to inspect protected identifiers.
    if safe(IsInInstance) then return end
    local guid = type(data) == "table" and data.guid
    if ns.IsSecret(guid) then return end
    if not guid and tooltip.GetUnit then
        local ok, _, unit = pcall(tooltip.GetUnit, tooltip)
        if ok and not ns.IsSecret(unit) and type(unit) == "string" then guid = safe(UnitGUID, unit) end
    end
    if type(guid) ~= "string" or not (guid:match("^Creature%-") or guid:match("^Vehicle%-")) then return end
    local npcID = tonumber(guid:match("^[^-]+%-[^-]+%-[^-]+%-[^-]+%-[^-]+%-(%d+)%-"))
    if not npcID then return end
    local ids = {}
    local needed = ActiveItems()
    for id, item in pairs(needed) do if item.npcs[npcID] then ids[#ids + 1] = id end end
    if #ids == 0 then return end
    -- Longer names first, so a short item name cannot claim another item's row.
    table.sort(ids, function(a, b)
        if #needed[a].name ~= #needed[b].name then return #needed[a].name > #needed[b].name end
        return a < b
    end)
    local name = tooltip.GetName and safe(tooltip.GetName, tooltip)
    local changed = false
    for index = 1, tooltip:NumLines() do
        local line = (name and _G[name .. "TextLeft" .. index]) or tooltip["TextLeft" .. index]
        local text = line and line.GetText and safe(line.GetText, line)
        -- Annotate native progress rows without replacing titles, player names,
        -- checks, counters or colors. The same item can occur in party rows.
        if type(text) == "string" and text:match("%d+%s*/%s*%d+") then
            for _, id in ipairs(ids) do
                local first, last = text:find(needed[id].name, 1, true)
                if first then
                    local value = Rate(id, npcID)
                    if value ~= nil then
                        local suffix = " (" .. FormatRate(value) .. ")"
                        if IsProgressItem(text, needed[id].name, suffix) then
                            if text:sub(last + 1, last + #suffix) ~= suffix then
                                line:SetText(text:sub(1, last) .. suffix .. text:sub(last + 1))
                                changed = true
                            end
                            break
                        end
                    end
                end
            end
        end
    end
    if changed then tooltip:Show() end
end

function ns.InitDropChances()
    if initialized then return end
    initialized, api = true, LibQuestieDB
    local support = api.Support.Get("QuestieClassicItemDrops") or {}
    local fixes = api.Support.Get("QuestieItemDropCorrections") or {}
    sources = {wowhead = Source(support.wowheadData), server = Source(support.cmangosData)}
    corrections = fixes.Era or {}
    local events = CreateFrame("Frame")
    for _, event in ipairs({"QUEST_LOG_UPDATE", "QUEST_TURNED_IN", "PLAYER_ENTERING_WORLD"}) do events:RegisterEvent(event) end
    events:SetScript("OnEvent", function() dirty = true end)
    local function Clear(tooltip) tooltip.QuestLiteDropToken, tooltip.QuestLiteDropLines = nil, nil end
    for _, tooltip in ipairs({GameTooltip, ItemRefTooltip}) do
        if tooltip.HasScript and tooltip:HasScript("OnTooltipCleared") then tooltip:HookScript("OnTooltipCleared", Clear) end
    end
    if GameTooltip and type(GameTooltip.GetPrimaryTooltipData) == "function" and TooltipDataProcessor
        and TooltipDataProcessor.AddTooltipPostCall and Enum and Enum.TooltipDataType then
        local function Relevant(tooltip) return tooltip == GameTooltip or tooltip == ItemRefTooltip end
        TooltipDataProcessor.AddTooltipPostCall(Enum.TooltipDataType.Item, function(tooltip, data)
            if Relevant(tooltip) then ItemTooltip(tooltip, data) end
        end)
        TooltipDataProcessor.AddTooltipPostCall(Enum.TooltipDataType.Unit, function(tooltip, data)
            if Relevant(tooltip) then UnitTooltip(tooltip, data) end
        end)
    else
        for _, tooltip in ipairs({GameTooltip, ItemRefTooltip}) do
            if tooltip.HasScript then
                if tooltip:HasScript("OnTooltipSetItem") then tooltip:HookScript("OnTooltipSetItem", ItemTooltip) end
                if tooltip:HasScript("OnTooltipSetUnit") then tooltip:HookScript("OnTooltipSetUnit", UnitTooltip) end
            end
        end
    end
end

if ns.testing then
    ns.testDropChances = {Rate = Rate, ItemTooltip = ItemTooltip, UnitTooltip = UnitTooltip, FormatRate = FormatRate}
end
