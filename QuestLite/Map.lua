-- SPDX-License-Identifier: GPL-3.0-or-later
local _, ns = ...
local TEMPLATE = "QuestLitePinTemplate"
local LIMIT, BUDGET_MS = 750, 4
local map, provider, worker, pendingAt, job, refreshAfterScan
local runner = CreateFrame("Frame")
runner:Hide()

QuestLitePinMixin = CreateFromMixins(MapCanvasPinMixin)
local Pin = QuestLitePinMixin
local labels = {pickup = "Quest pickup", turnin = "Ready to turn in"}
local priorities = {pickup = 2, turnin = 3}
local colors = {pickup = {1, .78, .12}, turnin = {.35, 1, .45}}
local tooltip, hoveredPin
local displayed, displayedMapID = {}, nil
local cache, cacheClock, contextRevision = {}, 0, 0
local displayedStateKey
local invalidatingEvents = {QUEST_TURNED_IN=true, PLAYER_LEVEL_UP=true,
    PLAYER_ENTERING_WORLD=true, SKILL_LINES_CHANGED=true, UPDATE_FACTION=true,
    SPELLS_CHANGED=true, BAG_UPDATE_DELAYED=true, FORCE_REFRESH=true}
local icons = {pickup = "Interface\\GossipFrame\\AvailableQuestIcon",
    turnin = "Interface\\GossipFrame\\ActiveQuestIcon"}
local atlases = {pickup = "QuestNormal", turnin = "QuestTurnin"}

function ns.SetMarkerIcon(texture, kind)
    if texture.SetAtlas and C_Texture and ns.Safe(C_Texture.GetAtlasInfo, atlases[kind]) then
        texture:SetAtlas(atlases[kind], false)
    else
        texture:SetTexture(icons[kind])
    end
end

local function GetTooltip()
    if not tooltip then
        tooltip = CreateFrame("GameTooltip", "QuestLiteTooltip", UIParent, "GameTooltipTemplate")
        tooltip:SetClampedToScreen(true)
        tooltip:SetFrameStrata("TOOLTIP")
        tooltip:EnableMouse(false)
        if tooltip.SetBackdropColor then tooltip:SetBackdropColor(.025, .03, .04, .98) end
        if tooltip.SetBackdropBorderColor then tooltip:SetBackdropBorderColor(1, .78, .12, 1) end
        tooltip:RegisterEvent("MODIFIER_STATE_CHANGED")
        tooltip:SetScript("OnEvent", function()
            if hoveredPin then ns.ShowMarkerTooltip(hoveredPin) end
        end)
    end
    return tooltip
end

function Pin:OnLoad()
    self.isWorldMapPin = true
    self:UseFrameLevelType("PIN_FRAME_LEVEL_AREA_POI")
    self:SetSize(22, 22)
    self:EnableMouse(true)
    self:EnableMouseWheel(false)
    self.Count:SetFont(STANDARD_TEXT_FONT or "Fonts\\FRIZQT__.TTF", 11, "OUTLINE")
    self:SetScalingLimits(1, 1, 1)
end

function Pin:UpdateData(data)
    self.data = data
    self.ids = {}
    for id in pairs(data.quests) do self.ids[#self.ids + 1] = id end
    table.sort(self.ids)
    ns.SetMarkerIcon(self.Icon, data.kind)
    self.Count:SetText(#self.ids > 1 and tostring(#self.ids) or "")
    if self.pinX ~= data.x or self.pinY ~= data.y then
        self:SetPosition(data.x, data.y)
        self.pinX, self.pinY = data.x, data.y
    end
end

function Pin:OnAcquired(data)
    self:UpdateData(data)
end

function Pin:OnReleased()
    if hoveredPin == self then
        if tooltip then tooltip:Hide() end
        hoveredPin = nil
    end
    self.data, self.ids, self.selectedID = nil, nil, nil
    self.pinX, self.pinY = nil, nil
    MapCanvasPinMixin.OnReleased(self)
end

function Pin:OnMouseEnter()
    if not self.data or not self.ids or #self.ids == 0 then return end
    hoveredPin = self
    local tip = GetTooltip()
    tip:SetOwner(self, "ANCHOR_CURSOR")
    local shift = IsShiftKeyDown and IsShiftKeyDown()
    local groups, names = {}, {}
    for _, id in ipairs(self.ids) do
        local entry = self.data.quests[id]
        local name = entry.label ~= "" and entry.label or labels[entry.kind]
        if not groups[name] then groups[name] = {}; names[#names + 1] = name end
        groups[name][#groups[name] + 1] = id
    end
    table.sort(names)
    for index, name in ipairs(names) do
        if index > 1 then tip:AddLine(" ") end
        if index == 1 and not shift then
            tip:AddDoubleLine(name, "Hold Shift", .2, 1, .2, .55, .55, .55)
        else
            tip:AddLine(name, .2, 1, .2, true)
        end
        local ids = groups[name]
        table.sort(ids, function(a, b)
            local left, right = ns.GetQuestSummary(a), ns.GetQuestSummary(b)
            if left.level ~= right.level then return left.level < right.level end
            if left.name ~= right.name then return left.name < right.name end
            return a < b
        end)
        for _, id in ipairs(ids) do
            local entry = self.data.quests[id]
            local summary = ns.GetQuestSummary(id)
            local color = GetQuestDifficultyColor and GetQuestDifficultyColor(summary.level)
            local status = entry.kind == "turnin" and "Complete" or entry.confirmed and "Available"
                or ns.db.filterAvailable and "Pickup" or "Unfiltered"
            if summary.classification then status = summary.classification .. " | " .. status end
            tip:AddDoubleLine(string.format("[%d] %s", summary.level, summary.name), status,
                color and color.r or 1, color and color.g or .85, color and color.b or .2,
                .75, .75, .75)
            if entry.zone then tip:AddLine("  " .. entry.zone, .65, .7, .75) end
            if shift then
                ns.ShowQuestDetails(tip, id, true)
                tip:AddLine(string.format("  Location: %.1f, %.1f", entry.x * 100, entry.y * 100), .65, .7, .75)
            end
        end
    end
    tip:Show()
end

function Pin:OnMouseLeave()
    if hoveredPin == self then
        if tooltip then tooltip:Hide() end
        hoveredPin = nil
    end
end

-- Plain minimap frames share the tooltip renderer, without map-canvas methods
-- or XML inheritance. Their mouse scripts are attached explicitly at creation.
ns.ShowMarkerTooltip = Pin.OnMouseEnter
ns.HideMarkerTooltip = Pin.OnMouseLeave
function ns.IsMarkerHovered(pin) return hoveredPin == pin end

local function Clear()
    worker, job = nil, nil
    if hoveredPin and hoveredPin.isWorldMapPin then
        if tooltip then tooltip:Hide() end
        hoveredPin = nil
    end
    for _, data in pairs(displayed) do data.pin = nil end
    displayed, displayedMapID, displayedStateKey = {}, nil, nil
    if map then map:RemoveAllPinsByTemplate(TEMPLATE) end
end

local function Publish(snapshot, stateKey)
    for key, old in pairs(displayed) do
        if not snapshot.pins[key] then map:RemovePin(old.pin); old.pin = nil end
    end
    for key, data in pairs(snapshot.pins) do
        local old = displayed[key]
        if old and old.pin then
            data.pin = old.pin
            data.pin:UpdateData(data)
        else
            data.pin = map:AcquirePin(TEMPLATE, data)
        end
    end
    displayed, displayedMapID, displayedStateKey = snapshot.pins, snapshot.mapID, stateKey
    if hoveredPin then ns.ShowMarkerTooltip(hoveredPin) end
    ns.mapStatus = string.format("Map %d: %d markers", snapshot.mapID, snapshot.count)
    map.QuestLiteStatus:SetText("QuestLite: ! Pickups  |  ? Turn-ins  |  Hold Shift for details")
end

local function StateKey()
    return tostring(contextRevision) .. ":" .. ns.GetMapStateKey()
end
ns.GetCurrentMapStateKey = StateKey

local function Remember(snapshot)
    cacheClock = cacheClock + 1
    snapshot.used, snapshot.cells = cacheClock, nil
    cache[snapshot.mapID] = snapshot
    local count, oldestID, oldestTime = 0, nil, math.huge
    for id, entry in pairs(cache) do
        count = count + 1
        if entry.used < oldestTime then oldestID, oldestTime = id, entry.used end
    end
    if count > 4 then cache[oldestID] = nil end
end

local function Start()
    worker, job = nil, nil
    if not map:IsShown() or not ns.db.map then Clear(); runner:Hide(); return end
    local mapID = map:GetMapID()
    if displayedMapID ~= mapID then Clear() end
    local info = mapID and C_Map.GetMapInfo(mapID)
    -- BuildMap projects zone coordinates through the native continent rectangles.
    if not info or (info.mapType and info.mapType < 2) then
        ns.mapStatus = "Open a continent or zone map to see quest locations."
        map.QuestLiteStatus:SetText(ns.mapStatus)
        runner:Hide()
        return
    end
    job = { count = 0, clustered = 0, pins = {}, cells = {}, mapID = mapID, stateKey = StateKey() }
    local current = job
    local function Emit(id, kind, label, x, y, confirmed, zone, sourceX, sourceY)
        local key = math.floor(x * 1000 + .5) .. ":" .. math.floor(y * 1000 + .5)
        local data = current.pins[key]
        local cellX, cellY = math.floor(x / .01), math.floor(y / .01)
        local best = 1
        if not data then
            for dx = -1, 1 do
                for dy = -1, 1 do
                    for _, candidate in ipairs(current.cells[(cellX + dx) .. ":" .. (cellY + dy)] or {}) do
                        local distance = ((candidate.x - x) / .01)^2 + ((candidate.y - y) / .01)^2
                        if distance < best then data, best = candidate, distance end
                    end
                end
            end
            if data then data.clustered = true; current.clustered = current.clustered + 1 end
        end
        if not data and current.count >= LIMIT then
            -- Keep every quest represented without allocating unlimited frames.
            -- Dense overflow goes to the nearest marker, with exact source
            -- coordinates and paged details in its tooltip.
            local bestDistance = math.huge
            for _, candidate in pairs(current.pins) do
                local distance = (candidate.x - x)^2 + (candidate.y - y)^2
                if distance < bestDistance then data, bestDistance = candidate, distance end
            end
            data.clustered = true
            current.clustered = current.clustered + 1
        end
        if not data then
            data = { kind = kind, x = x, y = y, quests = {} }
            current.pins[key] = data
            current.count = current.count + 1
            local cell = cellX .. ":" .. cellY
            current.cells[cell] = current.cells[cell] or {}
            table.insert(current.cells[cell], data)
        end
        if priorities[kind] > priorities[data.kind] then
            data.kind = kind
        end
        if not data.quests[id] then
            data.quests[id] = {kind = kind, label = label or "", x = sourceX or x,
                y = sourceY or y, zone = zone, confirmed = confirmed}
        end
        if kind == "pickup" then data.hasPickup = true end
    end
    local cycleStart, operations = debugprofilestop(), 0
    local function Checkpoint()
        operations = operations + 1
        if operations >= 2048 or (operations % 16 == 0 and debugprofilestop() - cycleStart >= BUDGET_MS) then
            coroutine.yield()
            cycleStart, operations = debugprofilestop(), 0
        end
    end
    worker = coroutine.create(function() ns.BuildMap(mapID, Emit, Checkpoint, current.stateKey) end)
    ns.mapStatus = "Loading quest locations..."
    map.QuestLiteStatus:SetText(ns.mapStatus)
end

function ns.RequestMap(_, event)
    if not map then return end
    if event == "GOSSIP_SHOW" or event == "QUEST_GREETING" or event == "QUEST_DETAIL" then
        if not ns.ObserveQuestOffers(event) then return end
        contextRevision = contextRevision + 1
    elseif invalidatingEvents[event] then
        ns.ClearOfferObservations()
        contextRevision = contextRevision + 1
    end
    local key = StateKey()
    if ns.RequestMinimap then ns.RequestMinimap(key) end
    local mapID = map:GetMapID()
    if not map:IsShown() then pendingAt = nil; runner:Hide(); return end
    if not ns.db.map then Clear(); pendingAt = nil; runner:Hide(); return end
    if displayedMapID == mapID and displayedStateKey == key then return end
    if worker and job and job.mapID == mapID then
        if job.stateKey ~= key then refreshAfterScan = true end
        return
    end
    if displayedMapID ~= mapID then Clear() end
    local saved = cache[mapID]
    if saved and saved.stateKey == key then
        cacheClock = cacheClock + 1; saved.used = cacheClock
        Publish(saved, key)
        pendingAt = nil; runner:Hide()
        return
    end
    if pendingAt then return end
    refreshAfterScan = nil
    map.QuestLiteStatus:SetText("Loading quest locations...")
    pendingAt = GetTime() -- No artificial map-open delay.
    runner:Show()
end

runner:SetScript("OnUpdate", function()
    if not map or not map:IsShown() then Clear(); runner:Hide(); return end
    if pendingAt then
        if GetTime() < pendingAt then return end
        pendingAt = nil
        Start()
    end
    if not worker then return end
    local ok, reason = coroutine.resume(worker)
    if not ok then
        ns.mapStatus = "Map scan stopped: " .. tostring(reason)
        ns.Print(ns.mapStatus)
        Clear()
        map.QuestLiteStatus:SetText("Quest locations unavailable; see /ql status")
        runner:Hide()
    elseif coroutine.status(worker) == "dead" then
        Remember(job)
        Publish(job, job.stateKey)
        worker, job = nil, nil
        if refreshAfterScan then
            refreshAfterScan = nil
            pendingAt = GetTime()
        else
            runner:Hide()
        end
    end
end)

function ns.InitMap()
    if map then return end
    if not WorldMapFrame and C_AddOns and C_AddOns.LoadAddOn then
        C_AddOns.LoadAddOn("Blizzard_WorldMap")
    end
    map = WorldMapFrame
    if not (map and map.AddDataProvider and MapCanvasDataProviderMixin) then
        ns.mapStatus = "World map API unavailable on this client."
        ns.Print(ns.mapStatus)
        return
    end
    local status = map:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    status:SetPoint("BOTTOM", map, "BOTTOM", 0, 24)
    map.QuestLiteStatus = status
    provider = CreateFromMixins(MapCanvasDataProviderMixin)
    function provider:RefreshAllData() ns.RequestMap(nil, "MAP_OPEN") end
    function provider:OnShow() ns.RequestMap(nil, "MAP_OPEN") end
    function provider:OnHide()
        pendingAt, refreshAfterScan = nil, nil
        Clear()
        runner:Hide()
    end
    function provider:RemoveAllData() Clear() end
    map:AddDataProvider(provider)
    local events = CreateFrame("Frame")
    for _, event in ipairs({"QUEST_LOG_UPDATE", "QUEST_TURNED_IN", "PLAYER_LEVEL_UP",
        "PLAYER_ENTERING_WORLD", "SKILL_LINES_CHANGED", "UPDATE_FACTION", "SPELLS_CHANGED",
        "BAG_UPDATE_DELAYED", "GOSSIP_SHOW", "QUEST_GREETING", "QUEST_DETAIL"}) do
        events:RegisterEvent(event)
    end
    events:SetScript("OnEvent", ns.RequestMap)
    ns.mapStatus = "Ready. Open a zone map to see quest locations."
    ns.RequestMap()
end
