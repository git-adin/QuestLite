-- SPDX-License-Identifier: GPL-3.0-or-later
local _, ns = ...
local safe = ns.Safe
local INTERVAL, MAX_FRAMES = .12, 64
local initialized, worker, buildingMap, buildingKey, queued
local zoneID, stateKey, locations = nil, nil, {}
local active, free = {}, {}
local lastPX, lastPY, lastFacing, lastRadius, lastWidth, lastPoints, lastSquare
local driver = CreateFrame("Frame")
driver:Hide()
local elapsedSinceUpdate = 0
local drawWidth, drawHeight
local movingPX, movingPY, movingFacing, movingRadius, movingHalfWidth, movingHalfHeight

local function Release(key, pin)
    if ns.IsMarkerHovered(pin) then ns.HideMarkerTooltip(pin) end
    pin:Hide()
    pin.data, pin.ids = nil, nil
    active[key] = nil
    free[#free + 1] = pin
end

local function HideAll()
    for key, pin in pairs(active) do Release(key, pin) end
    lastPoints = nil
    movingPX, movingPY, movingFacing, movingRadius = nil, nil, nil, nil
end

local function NewPin()
    local pin = CreateFrame("Frame", nil, Minimap)
    pin.markerSize = 18
    pin:SetSize(18, 18)
    pin:SetFrameLevel(Minimap:GetFrameLevel() + 10)
    pin:EnableMouse(true)
    pin.Icon = pin:CreateTexture(nil, "OVERLAY")
    pin.Icon:SetAllPoints()
    pin.Count = pin:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    pin.Count:SetPoint("BOTTOMRIGHT", pin, "BOTTOMRIGHT", 2, -2)
    pin.Count:SetFont(STANDARD_TEXT_FONT or "Fonts\\FRIZQT__.TTF", 10, "OUTLINE")
    pin:SetScript("OnEnter", ns.ShowMarkerTooltip)
    pin:SetScript("OnLeave", ns.HideMarkerTooltip)
    return pin
end

local function PlayerZone()
    local id = C_Map and safe(C_Map.GetBestMapForUnit, "player")
    -- Database coordinates use zone maps, not a city's smaller interior map.
    for _ = 1, 5 do
        local info = id and safe(C_Map.GetMapInfo, id)
        if not info then return nil end
        if not info.mapType or info.mapType <= 4 then return id end
        id = info.parentMapID
    end
end

local function MapSize(id)
    if not (C_Map and C_Map.GetMapWorldSize) then return nil end
    local ok, width, height = pcall(C_Map.GetMapWorldSize, id)
    if not ok or ns.IsSecret(width) or ns.IsSecret(height) then return nil end
    if ns.IsFiniteNumber(width) and ns.IsFiniteNumber(height) and width > 0 and height > 0 then
        return width, height
    end
end

local function Coordinates(position)
    if not position or not position.GetXY then return nil end
    local ok, x, y = pcall(position.GetXY, position)
    if not ok or ns.IsSecret(x) or ns.IsSecret(y) then return nil end
    if ns.IsFiniteNumber(x) and ns.IsFiniteNumber(y) then return x, y end
end

local function Position(dx, dy, radius, facing, halfWidth, halfHeight, square)
    if facing then
        local cos, sin = math.cos(facing), math.sin(facing)
        dx, dy = dx * cos - dy * sin, dx * sin + dy * cos
    end
    local x, y = dx / radius, dy / radius
    local limit = .88 -- keep the whole icon inside the minimap edge
    if square then
        if math.abs(x) > limit or math.abs(y) > limit then return nil end
    elseif x * x + y * y > limit * limit then return nil end
    return x * halfWidth, -y * halfHeight
end

local function Draw()
    if not ns.db.minimap or not Minimap:IsVisible() then HideAll(); return end
    if PlayerZone() ~= zoneID then HideAll(); return end
    local position = safe(C_Map.GetPlayerMapPosition, zoneID, "player")
    local px, py = Coordinates(position)
    local width, height = MapSize(zoneID)
    drawWidth, drawHeight = width, height
    local radius = C_Minimap and safe(C_Minimap.GetViewRadius)
    if not px or not width or not ns.IsFiniteNumber(radius) or radius <= 0 then HideAll(); return end
    local rotate = C_CVar and safe(C_CVar.GetCVar, "rotateMinimap") == "1"
    if C_Minimap and safe(C_Minimap.IsRotateMinimapIgnored) then rotate = false end
    local facing = rotate and safe(GetPlayerFacing) or nil
    if rotate and not ns.IsFiniteNumber(facing) then HideAll(); return end
    local halfWidth, halfHeight = Minimap:GetWidth() / 2, Minimap:GetHeight() / 2
    if not ns.IsFiniteNumber(halfWidth) or not ns.IsFiniteNumber(halfHeight) or halfWidth <= 0 or halfHeight <= 0 then HideAll(); return end
    local square = GetMinimapShape and GetMinimapShape() == "SQUARE"
    local geometry = width .. ":" .. height .. ":" .. halfWidth .. ":" .. halfHeight
    if px == lastPX and py == lastPY and facing == lastFacing and radius == lastRadius
        and geometry == lastWidth and square == lastSquare and locations == lastPoints then return end
    lastPX, lastPY, lastFacing, lastRadius = px, py, facing, radius
    lastWidth, lastSquare, lastPoints = geometry, square, locations
    local groups, ordered = {}, {}
    for _, location in ipairs(locations) do
        local sx, sy = Position((location.x - px) * width, (location.y - py) * height,
            radius, facing, halfWidth, halfHeight, square)
        if sx then
            -- Zone-anchored cells keep group identity stable while moving,
            -- rotating and zooming. Player-relative screen cells caused jitter.
            local key = math.floor(location.x / .002 + .5) .. ":" .. math.floor(location.y / .002 + .5)
            local group = groups[key]
            if not group then
                group = {key = key, sx = sx, sy = sy, x = location.x, y = location.y, kind = location.kind, quests = {}}
                groups[key] = group
                ordered[#ordered + 1] = group
            end
            if location.kind == "turnin" then group.kind = "turnin" end
            for id, entry in pairs(location.quests) do group.quests[id] = entry end
        end
    end
    table.sort(ordered, function(a, b)
        local left, right = a.sx * a.sx + a.sy * a.sy, b.sx * b.sx + b.sy * b.sy
        if left == right then return a.key < b.key end
        return left < right
    end)
    -- Bound the pool even on dense quest hubs. Nearby overflow shares the last
    -- visible group instead of allocating frames or dropping quest details.
    for index = MAX_FRAMES + 1, #ordered do
        for id, entry in pairs(ordered[index].quests) do ordered[MAX_FRAMES].quests[id] = entry end
        groups[ordered[index].key] = nil
    end
    for key, pin in pairs(active) do if not groups[key] then Release(key, pin) end end
    for index = 1, math.min(#ordered, MAX_FRAMES) do
        local group = ordered[index]
        local pin = active[group.key]
        if not pin then pin = table.remove(free) or NewPin(); active[group.key] = pin end
        local previousIDs, previousData = pin.ids, pin.data
        pin.data, pin.ids = group, {}
        for id in pairs(group.quests) do pin.ids[#pin.ids + 1] = id end
        table.sort(pin.ids)
        ns.SetMarkerIcon(pin.Icon, group.kind, group.quests)
        pin.Count:SetText(#pin.ids > 1 and tostring(#pin.ids) or "")
        pin:SetPoint("CENTER", Minimap, "CENTER", group.sx, group.sy)
        pin.screenX, pin.screenY = group.sx, group.sy
        pin:Show()
        if ns.IsMarkerHovered(pin) then
            local changed = not previousIDs or not previousData or #previousIDs ~= #pin.ids
            if not changed then
                for i, id in ipairs(pin.ids) do
                    if previousIDs[i] ~= id or previousData.quests[id] ~= group.quests[id] then changed = true; break end
                end
            end
            if changed then ns.ShowMarkerTooltip(pin) end
        end
    end
    ns.minimapStatus = string.format("Minimap: %d nearby quest icons", math.min(#ordered, MAX_FRAMES))
end

-- Move only the bounded set of existing frames between the slower range/group
-- checks. No database scan, grouping tables or frame allocations per frame.
local function MovePins()
    if not drawWidth or not drawHeight or not next(active) then return end
    local px, py = Coordinates(safe(C_Map.GetPlayerMapPosition, zoneID, "player"))
    local radius = C_Minimap and safe(C_Minimap.GetViewRadius)
    local rotate = C_CVar and safe(C_CVar.GetCVar, "rotateMinimap") == "1"
    if C_Minimap and safe(C_Minimap.IsRotateMinimapIgnored) then rotate = false end
    local facing = rotate and safe(GetPlayerFacing) or nil
    if not px or not ns.IsFiniteNumber(radius) or radius <= 0 or (rotate and not ns.IsFiniteNumber(facing)) then HideAll(); return end
    local halfWidth, halfHeight = Minimap:GetWidth() / 2, Minimap:GetHeight() / 2
    if not ns.IsFiniteNumber(halfWidth) or not ns.IsFiniteNumber(halfHeight) or halfWidth <= 0 or halfHeight <= 0 then HideAll(); return end
    if px == movingPX and py == movingPY and facing == movingFacing and radius == movingRadius
        and halfWidth == movingHalfWidth and halfHeight == movingHalfHeight then return end
    movingPX, movingPY, movingFacing, movingRadius = px, py, facing, radius
    movingHalfWidth, movingHalfHeight = halfWidth, halfHeight
    local square = GetMinimapShape and GetMinimapShape() == "SQUARE"
    for _, pin in pairs(active) do
        local data = pin.data
        local sx, sy = Position((data.x - px) * drawWidth, (data.y - py) * drawHeight,
            radius, facing, halfWidth, halfHeight, square)
        if sx then
            if pin.screenX ~= sx or pin.screenY ~= sy then
                pin:SetPoint("CENTER", Minimap, "CENTER", sx, sy)
                pin.screenX, pin.screenY = sx, sy
            end
            pin:Show()
        else
            if ns.IsMarkerHovered(pin) then ns.HideMarkerTooltip(pin) end
            pin:Hide()
        end
    end
end

function ns.RequestMinimap(key)
    if not initialized then return end
    if not ns.db.minimap then
        worker, queued = nil, nil
        HideAll(); driver:Hide()
        ns.minimapStatus = "Minimap quest icons off"
        return
    end
    driver:Show()
    local id = PlayerZone()
    if not id then
        worker, queued, buildingMap, buildingKey = nil, nil, nil, nil
        HideAll(); return
    end
    -- Cancel before checking the displayed snapshot: A -> B -> A can return
    -- while B is still scanning, even though the cached A snapshot is current.
    if worker and buildingMap ~= id then
        worker, queued, buildingMap, buildingKey = nil, nil, nil, nil
    end
    key = key or ns.GetCurrentMapStateKey()
    if zoneID == id and stateKey == key then return end
    if worker and buildingMap == id and buildingKey == key then return end
    if worker and buildingMap == id then queued = true; return end
    if zoneID ~= id then HideAll() end
    queued = nil
    local nextLocations, byPoint = {}, {}
    buildingMap, buildingKey = id, key
    local cycleStart = debugprofilestop()
    local operations = 0
    local function Checkpoint()
        operations = operations + 1
        if operations >= 2048 or (operations % 16 == 0 and debugprofilestop() - cycleStart >= 2) then
            coroutine.yield()
            cycleStart, operations = debugprofilestop(), 0
        end
    end
    worker = coroutine.create(function()
        ns.BuildMap(id, function(questID, kind, label, x, y, confirmed)
            local pointKey = math.floor(x * 10000 + .5) .. ":" .. math.floor(y * 10000 + .5)
            local point = byPoint[pointKey]
            if not point then
                point = {x = x, y = y, kind = kind, quests = {}}
                byPoint[pointKey] = point
                nextLocations[#nextLocations + 1] = point
            end
            if kind == "turnin" then point.kind = "turnin" end
            point.quests[questID] = {kind = kind, label = label or "", x = x, y = y, confirmed = confirmed,
                repeatable = ns.GetQuestSummary(questID).repeatable}
        end, Checkpoint, key)
        locations, zoneID, stateKey = nextLocations, id, key
    end)
end

driver:SetScript("OnUpdate", function(_, elapsed)
    if not Minimap:IsVisible() then HideAll(); return end
    if worker and PlayerZone() ~= buildingMap then
        worker, queued = nil, nil
        ns.RequestMinimap()
    end
    if worker then
        local ok, reason = coroutine.resume(worker)
        if not ok then
            worker, queued = nil, nil
            locations, zoneID, stateKey = {}, nil, nil
            HideAll(); driver:Hide()
            ns.Print("Minimap scan stopped: " .. tostring(reason))
            return
        elseif coroutine.status(worker) == "dead" then
            worker = nil
            if queued then queued = nil; ns.RequestMinimap() end
        end
    end
    elapsedSinceUpdate = elapsedSinceUpdate + elapsed
    if elapsedSinceUpdate >= INTERVAL then
        elapsedSinceUpdate = 0
        ns.RequestMinimap()
        Draw()
    else
        MovePins()
    end
end)

function ns.InitMinimap()
    if initialized then return end
    if not (Minimap and C_Map and C_Map.GetMapWorldSize and C_Map.GetPlayerMapPosition
        and C_Minimap and C_Minimap.GetViewRadius) then
        ns.minimapStatus = "Minimap coordinate API unavailable."
        return
    end
    initialized = true
    local events = CreateFrame("Frame")
    for _, event in ipairs({"ZONE_CHANGED_NEW_AREA", "ZONE_CHANGED", "ZONE_CHANGED_INDOORS",
        "MINIMAP_UPDATE_ZOOM"}) do events:RegisterEvent(event) end
    events:SetScript("OnEvent", function() ns.RequestMinimap() end)
    ns.RequestMinimap()
end

if ns.testing then
    ns.testMinimapPosition = Position
    ns.testMinimapActive = active
end
