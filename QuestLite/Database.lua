-- SPDX-License-Identifier: GPL-3.0-or-later
local _, ns = ...
local api, quest, areaMaps, dungeonAreas
local eligibleCache
local offers, offerSerial = {}, 0
local safe = ns.Safe

-- Support mappings are serialized Lua tables supplied by the installed provider.
-- Parse numeric pairs as data; never execute the strings with loadstring.
local function MergeMap(target, source)
    if type(source) == "table" then
        for key, value in pairs(source) do target[key] = value end
    elseif type(source) == "string" then
        for key, value in source:gmatch("%[(%d+)%]%s*=%s*(%d+)") do
            target[tonumber(key)] = tonumber(value)
        end
    end
end

function ns.InitDatabase()
    eligibleCache = nil
    api = LibQuestieDB
    if type(api) ~= "table" or type(api.RequireContract) ~= "function" then
        return false, "QuestieDB with public contract 4 is required."
    end
    local ok, reason = api.RequireContract(4)
    if not ok then return false, reason end
    quest = api.Quest
    if not (quest and api.Npc and api.Object and api.Item and api.Support) then
        return false, "QuestieDB is missing its entity or zone API."
    end
    local zones = api.Support.Get("ZoneDB")
    local mapping = zones and zones.private
    if not mapping then return false, "QuestieDB zone mappings are unavailable." end
    areaMaps = {}
    MergeMap(areaMaps, mapping.areaIdToUiMapId)
    MergeMap(areaMaps, mapping.areaIdToUiMapIdOverride)
    dungeonAreas = {}
    for area, dungeon in pairs(mapping.dungeons or {}) do
        dungeonAreas[area] = dungeon
        for _, alias in ipairs(dungeon[2] or {}) do dungeonAreas[alias] = dungeon end
    end
    if not next(areaMaps) then return false, "QuestieDB zone mappings are empty." end
    return true
end

local function Get(id, field) return quest.Get(id, field) end

-- Release just the row read here, using the provider's public lifecycle API.
-- Do not flush the entire shared cache or mutate provider-owned results.
local function Release(entity, id)
    if entity.InvalidateCache then entity.InvalidateCache(id) end
end

local function Completed(id)
    return id and id > 0 and safe(C_QuestLog.IsQuestFlaggedCompleted, id) == true
end

local function MaskAllows(mask, id)
    if not mask or mask == 0 or not id then return true end
    -- Forever race masks can exceed 32 bits; bit.band truncates those masks.
    return math.floor(mask / 2 ^ (id - 1)) % 2 == 1
end

local function Snapshot()
    local player = { active = {}, skills = {}, skillsKnown = true, level = UnitLevel("player") }
    player.race = select(3, UnitRace("player"))
    player.class = select(3, UnitClass("player"))
    local count = safe(C_QuestLog.GetNumQuestLogEntries) or safe(GetNumQuestLogEntries) or 0
    for index = 1, count do
        local info = safe(C_QuestLog.GetInfo, index)
        local id = info and not info.isHeader and info.questID
        if not C_QuestLog.GetInfo and GetQuestLogTitle then
            local _, _, _, header, _, _, _, legacyID = GetQuestLogTitle(index)
            if not header then id = legacyID end
        end
        if type(id) == "number" and id > 0 then player.active[id] = true end
    end
    if C_SkillInfo and C_SkillInfo.GetSkillLineInfo then
        for index = 1, safe(C_SkillInfo.GetNumSkillLines) or 0 do
            local info = safe(C_SkillInfo.GetSkillLineInfo, index)
            if info and info.isHeader and info.isCollapsed then player.skillsKnown = false end
            if info and info.skillID then player.skills[info.skillID] = info.rank end
        end
    end
    return player
end

local function KnownSpell(id)
    if not id or id == 0 then return true end
    local known = safe(IsPlayerSpell, math.abs(id)) == true or safe(IsSpellKnown, math.abs(id)) == true
    if id < 0 then return not known end
    return known
end

local function RepPass(requirement, minimum)
    if not requirement then return true end
    local data = C_Reputation and safe(C_Reputation.GetFactionDataByID, requirement[1])
    local standing = data and data.currentStanding
    if standing == nil and GetFactionInfoByID then standing = select(6, GetFactionInfoByID(requirement[1])) end
    if standing == nil then return false end
    if minimum then return standing >= requirement[2] end
    return standing < requirement[2]
end

local function RanksPass(requirements)
    local positive, allowed = false, false
    for _, row in ipairs(requirements or {}) do
        local spells = ns.professionRankSpells and ns.professionRankSpells[row[1]]
        local rank = row[2]
        if spells and rank and rank < 0 then
            local spell = spells[-rank]
            if spell and KnownSpell(spell) then return false end
        elseif rank and rank > 0 then
            positive = true
            if spells then
                for index = rank, #spells do
                    if KnownSpell(spells[index]) then allowed = true; break end
                end
            end
        end
    end
    return not positive or allowed
end

local function SpecializationPass(id, player)
    if not id or id == 0 then return true end
    local constants = api.Enum or {}
    for name, skillID in pairs(constants.professionKeys or {}) do
        if id == skillID then
            -- A profession ID means "has this profession but no specialization";
            -- a specialization spell ID instead requires knowing that spell.
            local professionKnown = player.skills[skillID] ~= nil
            for _, spell in ipairs((ns.professionRankSpells or {})[skillID] or {}) do
                if KnownSpell(spell) then professionKnown = true; break end
            end
            if not professionKnown and player.skillsKnown ~= false then return false end
            for key, spell in pairs(constants.specializationKeys or {}) do
                if key:sub(1, #name + 1) == name .. "_" and KnownSpell(spell) then return false end
            end
            return true
        end
    end
    return KnownSpell(id)
end

local function PolicyRestricted(id)
    local policy = ns.pickupPolicy
    return policy and (policy.collection[id] or policy.event[id]
        or (policy.hidden and policy.hidden[id])
        or (policy.eventSorts and policy.eventSorts[Get(id, "zoneOrSort")]))
end

local function ChainRequirementsPass(id, player)
    for _, predecessor in ipairs((ns.chainPrerequisiteOverrides or {})[id] or {}) do
        if not Completed(predecessor) then return false end
    end
    local parent = Get(id, "parentQuest")
    if parent and parent > 0 and not player.active[parent] then return false end
    local sinceID = Get(id, "availableStartingWith")
    if sinceID and sinceID > 0 and not player.active[sinceID] and not Completed(sinceID) then return false end
    local alternatives = Get(id, "preQuestSingle")
    if alternatives and #alternatives > 0 then
        local found = false
        for _, other in ipairs(alternatives) do if Completed(other) then found = true; break end end
        if not found then return false end
    else
        for _, other in ipairs(Get(id, "preQuestGroup") or {}) do
            -- Negative group IDs require that exact quest completed; positive
            -- IDs may also be satisfied by a completed exclusive alternative.
            local fulfilled = Completed(math.abs(other))
            if not fulfilled and other > 0 then
                for _, alternative in ipairs(Get(other, "exclusiveTo") or {}) do
                    if Completed(alternative) then fulfilled = true; break end
                end
                Release(quest, other)
            end
            if not fulfilled then return false end
        end
    end
    return true
end

local function Eligible(id, player)
    if player.active[id] then return false end
    if not ns.db.showLowLevel then
        local level = Get(id, "questLevel")
        -- Scaling (-1) and unknown levels do not provide a fixed level to hide.
        if type(level) == "number" and level > 0
            and level < player.level - ns.db.levelsBelow then return false end
    end
    -- Mandatory chain requirements also apply to confirmed offers in strict
    -- mode. Objective completion or acceptance is not prerequisite turn-in.
    -- Explicit offers can still restore conditional entries and repeatables.
    if ns.db.filterAvailable and player.confirmed and player.confirmed[id] then
        return ChainRequirementsPass(id, player)
    end
    if Completed(id) then return false end
    if not MaskAllows(Get(id, "requiredRaces"), player.race)
        or not MaskAllows(Get(id, "requiredClasses"), player.class) then return false end
    if ns.db.filterAvailable == false then return true end
    if PolicyRestricted(id) then return false end
    if (Get(id, "requiredLevel") or 1) > player.level then return false end
    local maximum = Get(id, "requiredMaxLevel")
    if maximum and maximum > 0 and player.level > maximum then return false end
    local autoRewarded = api.Enum and api.Enum.questFlags and api.Enum.questFlags.AUTO_REWARDED or 1024
    if bit.band(Get(id, "questFlags") or 0, autoRewarded) ~= 0 then return false end
    local function ActiveOrDone(other) return player.active[other] or Completed(other) end
    for _, other in ipairs(Get(id, "exclusiveTo") or {}) do
        if ActiveOrDone(other) then return false end
    end
    local nextID = Get(id, "nextQuestInChain")
    if nextID and nextID > 0 and ActiveOrDone(nextID) then return false end
    local breadcrumb = Get(id, "breadcrumbForQuestId")
    if breadcrumb and breadcrumb > 0 and ActiveOrDone(breadcrumb) then return false end
    for _, other in ipairs(Get(id, "breadcrumbs") or {}) do
        if player.active[other] then return false end
    end
    local disabled = Get(id, "disabledByQuest")
    if disabled and player.active[disabled] then return false end
    local untilID = Get(id, "availableUntilCompleted")
    if untilID and Completed(untilID) then return false end
    if not ChainRequirementsPass(id, player) then return false end
    local skill = Get(id, "requiredSkill")
    if skill and C_SkillInfo and (player.skillsKnown ~= false or player.skills[skill[1]])
        and (player.skills[skill[1]] or 0) < skill[2] then return false end
    if not RanksPass(Get(id, "requiredRanks")) then return false end
    if not SpecializationPass(Get(id, "requiredSpecialization"), player) then return false end
    if not KnownSpell(Get(id, "requiredSpell")) then return false end
    if not RepPass(Get(id, "requiredMinRep"), true) or not RepPass(Get(id, "requiredMaxRep"), false) then return false end
    for _, itemID in ipairs(Get(id, "requiredSourceItems") or {}) do
        local count = safe(C_Item and C_Item.GetItemCount or GetItemCount, itemID)
        if type(count) == "number" and count == 0 then return false end
    end
    return true
end

function ns.ClearOfferObservations() offers = {} end

-- An NPC's complete gossip quest list is server evidence for that giver only.
-- Never infer a complete list from QUEST_DETAIL, which can display just one quest.
function ns.ObserveQuestOffers(event)
    local guid = safe(UnitGUID, "npc") or safe(UnitGUID, "questnpc")
    if type(guid) ~= "string" then return false end
    if not guid:match("^Creature%-") and not guid:match("^Vehicle%-") then return false end
    local npcID = tonumber(guid:match("^[^-]+%-[^-]+%-[^-]+%-[^-]+%-[^-]+%-(%d+)%-"))
    if not npcID then return false end
    local ids = {}
    local complete = event ~= "QUEST_DETAIL"
    if event == "QUEST_DETAIL" then
        local id = safe(GetQuestID)
        if type(id) ~= "number" or id <= 0 then return false end
        ids[id] = true
    elseif event == "QUEST_GREETING" then
        local count = safe(GetNumAvailableQuests)
        if type(count) ~= "number" or not GetAvailableQuestInfo then return false end
        for index = 1, count do
            -- Forever returns the quest ID in the fifth position.
            local ok, title, level, trivial, frequency, id = pcall(GetAvailableQuestInfo, index)
            if not ok or ns.IsSecret(id) or type(id) ~= "number" or id <= 0 then return false end
            ids[id] = true
        end
    else
        local rows = C_GossipInfo and safe(C_GossipInfo.GetAvailableQuests)
        if type(rows) ~= "table" then return false end
        for _, row in ipairs(rows) do
            local id = row.questID
            if ns.IsSecret(id) or type(id) ~= "number" or id <= 0 then return false end
            ids[id] = true
        end
    end
    offerSerial = offerSerial + 1
    local characterState = ns.GetMapStateKey(true)
    if not complete and offers[npcID] and offers[npcID].state == characterState then
        for id in pairs(ids) do offers[npcID].ids[id] = true end
        offers[npcID].serial = offerSerial
    else
        offers[npcID] = {ids = ids, complete = complete, state = characterState, serial = offerSerial}
    end
    local count, oldestID, oldest = 0, nil, math.huge
    for id, entry in pairs(offers) do
        count = count + 1
        if entry.serial < oldest then oldestID, oldest = id, entry.serial end
    end
    if count > 64 then offers[oldestID] = nil end
    return true
end

function ns.BuildMap(mapID, emit, checkpoint, stateKey)
    local mapInfo = safe(C_Map.GetMapInfo, mapID)
    local overview = mapInfo and mapInfo.mapType == 2
    local projections = {}
    local function Projection(sourceID)
        if sourceID == mapID then return true end
        if not overview or not sourceID then return false end
        if projections[sourceID] ~= nil then return projections[sourceID] end
        projections[sourceID] = false
        local info = safe(C_Map.GetMapInfo, sourceID)
        local sourceInfo = info
        -- Rectangles alone do not establish continent membership. Follow the
        -- native hierarchy before projecting, and never flatten dungeon floors.
        if not info or info.mapType ~= 3 then return false end
        local parent, depth = sourceID, 0
        while info and parent ~= mapID and depth < 16 do
            parent = info.parentMapID
            if not parent or parent == 0 then break end
            info = safe(C_Map.GetMapInfo, parent)
            depth = depth + 1
        end
        if parent ~= mapID or not C_Map.GetMapRectOnMap then return false end
        local ok, left, right, top, bottom = pcall(C_Map.GetMapRectOnMap, sourceID, mapID)
        if ok and ns.IsFiniteNumber(left) and ns.IsFiniteNumber(right)
            and ns.IsFiniteNumber(top) and ns.IsFiniteNumber(bottom)
            and left < right and top < bottom then
            projections[sourceID] = {left, right - left, top, bottom - top, name = sourceInfo.name}
        end
        return projections[sourceID]
    end
    local function Location(sourceID, id, kind, label, x, y, confirmed)
        if type(x) ~= "number" or type(y) ~= "number" or not (x >= 0 and x <= 100 and y >= 0 and y <= 100) then return end
        local projection = Projection(sourceID)
        if not projection then return end
        x, y = x / 100, y / 100
        if projection == true then emit(id, kind, label, x, y, confirmed); return end
        local px, py = projection[1] + x * projection[2], projection[3] + y * projection[4]
        if px >= 0 and px <= 1 and py >= 0 and py <= 1 then
            emit(id, kind, label, px, py, confirmed, projection.name or ("Map " .. sourceID), x, y)
        end
    end
    local player = Snapshot()
    player.offerState, player.confirmed = ns.GetMapStateKey(true), {}
    for _, offer in pairs(offers) do
        if offer.state == player.offerState then
            for id in pairs(offer.ids) do player.confirmed[id] = true end
        end
    end
    local function Spawns(spawns, id, kind, label, confirmed)
        for area, points in pairs(spawns or {}) do
            local dungeon = dungeonAreas[area]
            if dungeon then
                for _, entrance in ipairs(dungeon[4] or {}) do
                    Location(areaMaps[entrance[1]], id, kind,
                        (label or "Quest location") .. " (inside " .. dungeon[1] .. "; entrance)",
                        entrance[2], entrance[3], confirmed)
                    checkpoint()
                end
            end
            if Projection(areaMaps[area]) then
                for _, point in ipairs(points) do
                    local x, y = point[1], point[2]
                    if type(x) == "number" and type(y) == "number" and x >= 0 and x <= 100 and y >= 0 and y <= 100 then
                        Location(areaMaps[area], id, kind, label, x, y, confirmed)
                    end
                    checkpoint()
                end
            end
        end
    end
    local function Entity(entity, entityID, id, kind, fallback, directGiver)
        local confirmed
        local knownOffer = directGiver and offers[entityID]
        if knownOffer and knownOffer.state ~= player.offerState then knownOffer = nil end
        confirmed = knownOffer and knownOffer.ids[id] == true
        if directGiver and kind == "pickup" and ns.db.filterAvailable then
            local friendly = entity.Get(entityID, "friendlyToFaction")
            local faction = safe(UnitFactionGroup, "player")
            if not confirmed and ((friendly == "A" and faction == "Horde") or (friendly == "H" and faction == "Alliance")
                or (ns.pickupPolicy and ns.pickupPolicy.hiddenGivers and ns.pickupPolicy.hiddenGivers[entityID])
                or (knownOffer and knownOffer.complete and not knownOffer.ids[id])
                or (player.confirmed[id] and PolicyRestricted(id))) then
                Release(entity, entityID)
                checkpoint()
                return
            end
        end
        Spawns(entity.spawns(entityID), id, kind, fallback or entity.name(entityID), confirmed)
        Release(entity, entityID)
        checkpoint()
    end
    local function Item(itemID, id, kind, label, seen, depth)
        if depth > 3 or seen[itemID] then return end
        seen[itemID] = true
        for _, source in ipairs(api.Item.npcDrops(itemID) or {}) do Entity(api.Npc, source, id, kind, label) end
        for _, source in ipairs(api.Item.objectDrops(itemID) or {}) do Entity(api.Object, source, id, kind, label) end
        for _, source in ipairs(api.Item.itemDrops(itemID) or {}) do Item(source, id, kind, label, seen, depth + 1) end
        Release(api.Item, itemID)
        checkpoint()
    end
    local function Givers(givers, id, kind)
        if not givers then return end
        for _, source in ipairs(givers[1] or {}) do Entity(api.Npc, source, id, kind, nil, true) end
        for _, source in ipairs(givers[2] or {}) do Entity(api.Object, source, id, kind) end
        for _, source in ipairs(givers[3] or {}) do
            Item(source, id, kind, api.Item.name(source) or "Quest-starting item", {}, 1)
        end
    end
    -- Active quests are emitted first, before the longer available-quest scan.
    local activeIDs = {}
    for id in pairs(player.active) do activeIDs[#activeIDs + 1] = id end
    table.sort(activeIDs)
    for _, id in ipairs(activeIDs) do
        if safe(C_QuestLog.IsComplete, id) == true then
            if ns.db.turnins then Givers(Get(id, "finishedBy"), id, "turnin") end

        end
        Release(quest, id)
        checkpoint()
    end
    if ns.db.available then
        if stateKey and eligibleCache and eligibleCache.key == stateKey then
            for _, id in ipairs(eligibleCache.ids) do
                Givers(Get(id, "startedBy"), id, "pickup")
                Release(quest, id)
                checkpoint()
            end
        else
            local ids = {}
            for _, id in ipairs(quest.GetAllIds()) do
                if Eligible(id, player) then
                    ids[#ids + 1] = id
                    Givers(Get(id, "startedBy"), id, "pickup")
                end
                Release(quest, id)
                checkpoint()
            end
            -- Publish only a complete pass; cancellation must not cache half a list.
            if stateKey then eligibleCache = {key = stateKey, ids = ids} end
        end
    end
end

local summaries, summaryCount = {}, 0
function ns.GetQuestSummary(id)
    if not summaries[id] then
        if summaryCount >= 256 then summaries, summaryCount = {}, 0 end
        summaries[id] = {name = quest.name(id) or ("Quest #" .. id), level = Get(id, "questLevel") or 0}
        summaryCount = summaryCount + 1
        Release(quest, id)
    end
    return summaries[id]
end

-- Objective counters do not affect pickup/turn-in markers. Only identity and
-- completion transitions need to invalidate a map on QUEST_LOG_UPDATE.
function ns.GetMapStateKey(characterOnly)
    local parts = {tostring(UnitLevel("player"))}
    -- A daily reset can change repeatable completion without changing quest-log
    -- identity. Include the native reset boundary without scanning completed IDs.
    local reset = safe(C_DateAndTime and C_DateAndTime.GetSecondsUntilDailyReset or GetQuestResetTime)
    local serverTime = safe(GetServerTime)
    if type(reset) == "number" and type(serverTime) == "number" and reset >= 0 then
        parts[#parts + 1] = "reset" .. math.floor((serverTime + reset + 30) / 60)
    end
    if not characterOnly then
        parts[#parts + 1] = tostring(ns.db.map)
        parts[#parts + 1] = tostring(ns.db.available)
        parts[#parts + 1] = tostring(ns.db.turnins)
        parts[#parts + 1] = tostring(ns.db.filterAvailable)
        parts[#parts + 1] = tostring(ns.db.showLowLevel)
        parts[#parts + 1] = tostring(ns.db.levelsBelow)
    end
    local ids = {}
    local count = safe(C_QuestLog.GetNumQuestLogEntries) or safe(GetNumQuestLogEntries) or 0
    for index = 1, count do
        local info = safe(C_QuestLog.GetInfo, index)
        local id = info and not info.isHeader and info.questID
        if not C_QuestLog.GetInfo and GetQuestLogTitle then
            local _, _, _, header, _, _, _, legacyID = GetQuestLogTitle(index)
            if not header then id = legacyID end
        end
        if type(id) == "number" and id > 0 then ids[#ids + 1] = id end
    end
    table.sort(ids)
    for _, id in ipairs(ids) do
        parts[#parts + 1] = id .. (safe(C_QuestLog.IsComplete, id) and "c" or "a")
    end
    return table.concat(parts, ":")
end

function ns.ShowQuestDetails(tooltip, id, bodyOnly)
    if not bodyOnly then tooltip:AddLine(quest.name(id) or ("Quest #" .. id), 1, .82, .18, true) end
    if not bodyOnly then
    tooltip:AddLine(string.format("Level %s  |  Requires level %s", Get(id, "questLevel") or "?",
        Get(id, "requiredLevel") or 1), .75, .75, .75)
    end
    local progress = safe(C_QuestLog.GetQuestObjectives, id)
    if progress and #progress > 0 then
        for _, row in ipairs(progress) do
            tooltip:AddLine(row.text or "", row.finished and .4 or 1, row.finished and 1 or .85, .4, true)
        end
    else
        for _, text in ipairs(Get(id, "objectivesText") or {}) do tooltip:AddLine(text, .92, .92, .92, true) end
    end
    Release(quest, id)
end

-- Kept local in production; pure helpers are exposed only to the offline harness.
if ns.testing then ns.test = { MergeMap = MergeMap, Eligible = Eligible } end
