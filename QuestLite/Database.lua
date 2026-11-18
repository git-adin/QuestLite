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

local function Get(id, field)
    local value = quest.Get(id, field)
    local row = ns.questFieldOverrides and ns.questFieldOverrides[id]
    local correction = row and row[field]
    -- Retire a correction automatically when a newer provider changes the value.
    if correction and value == correction.was then return correction.value end
    row = ns.characterQuestFieldOverrides and ns.characterQuestFieldOverrides[id]
    correction = row and row[field]
    if correction and value == correction.was then return correction.value end
    return value
end

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

local function RaceAllows(mask, id)
    if not mask or mask == 0 or not id then return true end
    -- Race IDs are not necessarily bit positions: Forever Skyborne IDs 95/96
    -- use bits 32/33. The provider owns this encoding; never truncate to 32 bits.
    local mapping = api.Enum and api.Enum.raceMaskById
    local flag = mapping and mapping[id]
    if not mapping and ns.IsFiniteNumber(id) and id >= 1 and id <= 32 then flag = 2 ^ (id - 1) end
    return ns.IsFiniteNumber(flag) and flag > 0 and math.floor(mask / flag) % 2 == 1
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
        or (policy.offerOnly and policy.offerOnly[id])
        or (policy.hidden and policy.hidden[id])
        or (policy.eventSorts and policy.eventSorts[Get(id, "zoneOrSort")]))
end

-- Share native/fallback precedence between eligibility and on-demand guidance.
local function PrerequisiteLists(id)
    local alternatives, group = Get(id, "preQuestSingle"), Get(id, "preQuestGroup")
    local missing = not (alternatives and #alternatives > 0) and not (group and #group > 0)
    local oldPatrols = id == 545 and alternatives and #alternatives == 1
        and alternatives[1] == 544 and not (group and #group > 0)
    if missing or oldPatrols then
        return alternatives, group, (ns.chainPrerequisiteOverrides or {})[id],
            (ns.chainAlternativeOverrides or {})[id]
    end
    return alternatives, group
end

local function AnyCompleted(ids)
    for _, id in ipairs(ids or {}) do if Completed(id) then return true end end
    return false
end

local function GroupCompleted(other)
    if Completed(math.abs(other)) then return true end
    if other > 0 then
        for _, alternative in ipairs(Get(other, "exclusiveTo") or {}) do
            if Completed(alternative) then Release(quest, other); return true end
        end
        Release(quest, other)
    end
    return false
end

local function ChainRequirementsPass(id, player)
    local alternatives,group,all,any=PrerequisiteLists(id)
    for _, other in ipairs(all or {}) do if not Completed(other) then return false end end
    if any and #any>0 and not AnyCompleted(any) then return false end
    local parent=Get(id,"parentQuest")
    if parent and parent>0 and not player.active[parent] then return false end
    local sinceID=Get(id,"availableStartingWith")
    if sinceID and sinceID>0 and not player.active[sinceID] and not Completed(sinceID) then return false end
    if alternatives and #alternatives>0 then
        if not AnyCompleted(alternatives) then return false end
    else
        for _, other in ipairs(group or {}) do if not GroupCompleted(other) then return false end end
    end
    return true
end

local function MinimumLevel(id)
    local minimum = Get(id, "requiredLevel")
    if minimum == 0 then
        -- A zero minimum is missing provider data, not permission at every level.
        -- Match Questie's conservative fallback until a real NPC offer is seen.
        local level = Get(id, "questLevel")
        if type(level) == "number" and level > 0 then return level end
    end
    return minimum or 1
end

local function QuestTag(info) return info.tagID end

function ns.IsPvPQuest(id)
    if ns.additionalPvPQuests and ns.additionalPvPQuests[id] then return true end
    local tag = ns.questTagOverrides and ns.questTagOverrides[id]
    if tag ~= nil then return tag == 41 end
    if C_QuestLog and type(C_QuestLog.GetQuestTagInfo) == "function" then
        local info = ns.Safe(C_QuestLog.GetQuestTagInfo, id)
        if type(info) == "table" then tag = ns.Safe(QuestTag, info) end
    else
        tag = ns.Safe(GetQuestTagInfo, id)
    end
    -- Unknown or secret tags are not classified. Never guess from quest names.
    return tag == 41
end

local function Eligible(id, player)
    if ns.db.hiddenQuests[id] or player.active[id] then return false end
    if ns.db.hidePvPQuests and ns.IsPvPQuest(id) then return false end
    if ns.db.hideClothQuests and ns.clothDonationQuests[id] then return false end
    local restriction = ns.questRestrictions and ns.questRestrictions[id]
    if restriction then
        if not MaskAllows(restriction.requiredClasses, player.class) then return false end
        -- Unsupported-season records are not ordinary event candidates. An old
        -- or malformed NPC offer observation must not restore them in strict mode.
        if ns.db.filterAvailable and restriction.season then return false end
    end
    if not ns.db.showLowLevel then
        local level = Get(id, "questLevel")
        -- Scaling (-1) and unknown levels do not provide a fixed level to hide.
        if type(level) == "number" and level > 0
            and level < player.level - ns.db.levelsBelow then return false end
    end
    if not RaceAllows(Get(id, "requiredRaces"), player.race)
        or not MaskAllows(Get(id, "requiredClasses"), player.class) then return false end
    -- Mandatory race/class and chain requirements also apply to confirmed offers in strict
    -- mode. Objective completion or acceptance is not prerequisite turn-in.
    -- Explicit offers can still restore conditional entries and repeatables.
    if ns.db.filterAvailable and player.confirmed and player.confirmed[id] then
        return ChainRequirementsPass(id, player)
    end
    if Completed(id) then return false end
    if ns.db.filterAvailable == false then return true end
    if PolicyRestricted(id) then return false end
    if MinimumLevel(id) > player.level then return false end
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
    local dropStarter
    local function Location(sourceID, id, kind, label, x, y, confirmed)
        if type(x) ~= "number" or type(y) ~= "number" or not (x >= 0 and x <= 100 and y >= 0 and y <= 100) then return end
        local projection = Projection(sourceID)
        if not projection then return end
        x, y = x / 100, y / 100
        if projection == true then emit(id, kind, label, x, y, confirmed, nil, nil, nil, dropStarter); return end
        local px, py = projection[1] + x * projection[2], projection[3] + y * projection[4]
        if px >= 0 and px <= 1 and py >= 0 and py <= 1 then
            emit(id, kind, label, px, py, confirmed, projection.name or ("Map " .. sourceID), x, y, dropStarter)
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
        local spawns = entity.spawns(entityID)
        local label = fallback or entity.name(entityID)
        Spawns(spawns, id, kind, label, confirmed)
        local observed = entity == api.Npc and ns.npcLocationFallbacks and ns.npcLocationFallbacks[entityID]
        if observed and (not spawns or not next(spawns)) then
            Location(observed.map, id, kind, label, observed.x, observed.y, confirmed)
        end
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
    local function Givers(givers, id, kind, destination)
        if not givers then return end
        for _, source in ipairs(givers[1] or {}) do
            -- Neutral library collection quests can be returned in either capital.
            -- The current provider omits Owen Thadd for 36 Garion-only records.
            -- Only redirect an already-ready turn-in for a Horde character.
            if kind == "turnin" and source == 211033 and ns.pickupPolicy
                and ns.pickupPolicy.collection[id] and safe(UnitFactionGroup, "player") == "Horde" then
                source = 211022
            end
            Entity(api.Npc, source, id, kind, nil, not destination)
        end
        for _, source in ipairs(givers[2] or {}) do Entity(api.Object, source, id, kind) end
        if not destination and (kind ~= "pickup" or ns.db.itemDropLocations) then
            for _, source in ipairs(givers[3] or {}) do
                dropStarter = true
                Item(source, id, kind, api.Item.name(source) or "Quest-starting item", {}, 1)
                dropStarter = nil
            end
        end
    end
    local function Pickups(id)
        local starters = Get(id, "startedBy")
        if ns.zoneDropDestinations[id] and starters and starters[3] and #starters[3]>0
            and not (starters[1] and #starters[1]>0) and not (starters[2] and #starters[2]>0) then
            if not ns.db.itemDropLocations then return end
            local finishers = Get(id, "finishedBy")
            if finishers and ((finishers[1] and #finishers[1]>0) or (finishers[2] and #finishers[2]>0)) then
                -- This is a reference destination, not an NPC offer or a ready
                -- turn-in. Do not suppress it when that NPC has no pickup.
                dropStarter = "destination"
                Givers(finishers, id, "pickup", true)
                dropStarter = nil
                return
            end
        end
        Givers(starters, id, "pickup")
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
                Pickups(id)
                Release(quest, id)
                checkpoint()
            end
        else
            local ids = {}
            for _, id in ipairs(quest.GetAllIds()) do
                if Eligible(id, player) then
                    ids[#ids + 1] = id
                    Pickups(id)
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
        local restriction = ns.questRestrictions and ns.questRestrictions[id]
        local minimum = Get(id, "requiredLevel")
        summaries[id] = {name = quest.name(id) or ("Quest #" .. id), level = Get(id, "questLevel") or 0,
            minimumLevel = MinimumLevel(id), minimumKnown = type(minimum)=="number" and minimum>0,
            availabilityNote = ns.pickupPolicy.offerOnly and ns.pickupPolicy.offerOnly[id]
                and "Availability is unverified. A current NPC offer is required in strict mode." or nil,
            classification = restriction and restriction.label,
            repeatable = bit.band(Get(id, "specialFlags") or 0, 1) ~= 0}
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
        parts[#parts + 1] = tostring(ns.db.itemDropLocations)
        parts[#parts + 1] = tostring(ns.db.hidePvPQuests)
        parts[#parts + 1] = tostring(ns.db.hideClothQuests)
        parts[#parts + 1] = tostring(ns.hiddenQuestRevision or 0)
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

local function QuestLocation(other, player)
        local active = player.active[other]
        local givers = Get(other, active and "finishedBy" or "startedBy") or {}
        for index, entity in ipairs({api.Npc, api.Object}) do
            for _, entityID in ipairs(givers[index] or {}) do
                local name = entity.name(entityID) or "Quest giver"
                for area, points in pairs(entity.spawns(entityID) or {}) do
                    for _, point in ipairs(points) do
                        local mapID, dungeon = areaMaps[area], dungeonAreas[area]
                        if dungeon then Release(entity, entityID); return name .. " (inside " .. dungeon[1] .. ")" end
                        local info = mapID and safe(C_Map and C_Map.GetMapInfo, mapID)
                        if mapID and ns.IsFiniteNumber(point[1]) and ns.IsFiniteNumber(point[2])
                            and point[1]>=0 and point[1]<=100 and point[2]>=0 and point[2]<=100 then
                            local result = string.format("%s - %s %.1f, %.1f", name,
                                info and info.name or ("Map " .. mapID), point[1], point[2])
                            Release(entity, entityID); return result
                        end
                    end
                end
                Release(entity, entityID)
                return name .. " (location unknown)"
            end
        end
        local itemID = givers[3] and givers[3][1]
        if itemID then
            local name = api.Item.name(itemID) or ("Item #" .. itemID)
            Release(api.Item, itemID); return "quest-starting item: " .. name
        end
        return active and "turn-in location unknown" or "pickup location unknown"
    end

function ns.GetQuestLocation(id)
    if not quest then return "Quest database unavailable" end
    local player=Snapshot()
    local text=QuestLocation(id,player)
    Release(quest,id)
    return text,player.active[id],Completed(id)
end

-- Called only for Shift details or explicit chat lookup; no full graph/index cache.
function ns.GetPrerequisiteHints(id)
    if not quest then return {} end
    local alternatives,group,all,any=PrerequisiteLists(id)
    if not ((alternatives and #alternatives>0) or (group and #group>0)
        or (all and #all>0) or (any and #any>0)) then Release(quest,id); return {} end
    local player, lines, visited, steps = Snapshot(), {}, {}, {}
    if player.active[id] then Release(quest,id); return lines end
    local truncated = false
    local Walk
    local function Add(other, depth, alternative)
        other = math.abs(other)
        if visited[other] or Completed(other) then return end
        if #lines>=10 then truncated=true; return end
        if alternative then visited[other]=true
        elseif depth<4 then Walk(other, depth+1) else visited[other]=true; truncated=true end
        if #lines>=10 then truncated=true; return end
        local action = player.active[other] and (safe(C_QuestLog.IsComplete, other) and "Turn in" or "Finish and turn in") or "Complete"
        local place=QuestLocation(other,player)
        steps[#steps+1]={id=other,name=ns.GetQuestSummary(other).name,action=action,alternative=alternative,
            location=(player.active[other] and "Return to: " or "Pick up: ")..place}
        lines[#lines+1] = (alternative and "Alternative: " or "") .. action .. " [" .. other .. "] "
            .. ns.GetQuestSummary(other).name .. " - " .. steps[#steps].location
        Release(quest, other)
    end
    local function Alternatives(ids, depth)
        if not ids or #ids==0 or AnyCompleted(ids) then return end
        local candidates={}
        for _, other in ipairs(ids) do
            if RaceAllows(Get(other,"requiredRaces"), player.race)
                and MaskAllows(Get(other,"requiredClasses"), player.class) then candidates[#candidates+1]=other end
            Release(quest, other)
        end
        if #candidates==0 then
            if #lines<10 then lines[#lines+1]="No matching prerequisite branch in known character data." end
            return
        end
        for _, other in ipairs(candidates) do Add(other,depth,#candidates>1) end
    end
    Walk = function(current, depth)
        if visited[current] then return end
        visited[current]=true
        local alternatives,group,required,any=PrerequisiteLists(current)
        for _, other in ipairs(required or {}) do Add(other,depth,false) end
        Alternatives(any,depth)
        if alternatives and #alternatives>0 then Alternatives(alternatives,depth)
        else
            for _, other in ipairs(group or {}) do if not GroupCompleted(other) then Add(other,depth,false) end end
        end
        Release(quest,current)
    end
    Walk(id,1)
    if truncated then lines[#lines+1]="Earlier steps may be omitted (route limit reached)." end
    return lines,steps,truncated
end

function ns.FindQuestMatches(query,limit)
    if not quest then return {},false end
    query=(query or ""):match("^%s*(.-)%s*$")
    limit=limit or 20
    local id=tonumber(query:match("quest:(%d+)") or query)
    if id then
        if ns.IsFiniteNumber(id) and id>0 and id==math.floor(id) and quest.name(id) then
            Release(quest,id); return {id},false
        end
        return {},false
    end
    if #query<2 then return {},false end
    local matches,exact,total,exactCount={}, {},0,0
    local lower=query:lower()
    local race=select(3,UnitRace("player"))
    local class=select(3,UnitClass("player"))
    for _,other in ipairs(quest.GetAllIds()) do
        local name=quest.name(other)
        if name and name:lower():find(lower,1,true) and RaceAllows(Get(other,"requiredRaces"),race)
            and MaskAllows(Get(other,"requiredClasses"),class) then
            total=total+1
            if #matches<limit then matches[#matches+1]=other end
            if name:lower()==lower then
                exactCount=exactCount+1
                if #exact<limit then exact[#exact+1]=other end
            end
        end
        Release(quest,other)
    end
    if #exact>0 then return exact,exactCount>limit end
    return matches,total>limit
end

function ns.ReportPrerequisites(argument)
    argument = (argument or ""):match("^%s*(.-)%s*$")
    local ids, number = {}, tonumber(argument)
    if number and ns.IsFiniteNumber(number) and number>0 and number==math.floor(number) then
        if quest.name(number) then ids[1]=number end
        Release(quest,number)
    elseif argument~="" then
        local wanted=argument:lower()
        for _, other in ipairs(quest.GetAllIds()) do
            local name=quest.name(other)
            if name and name:lower()==wanted and #ids<3 then ids[#ids+1]=other end
            Release(quest,other)
        end
    end
    if #ids==0 then ns.Print("Use /ql prereq <quest ID or exact quest name>."); return end
    for _, other in ipairs(ids) do
        ns.Print(ns.GetQuestSummary(other).name .. " [" .. other .. "] - known missing quest turn-ins:")
        local hints=ns.GetPrerequisiteHints(other)
        if #hints==0 then ns.Print("No missing quest turn-ins found. Level, faction and server-only conditions may still apply.") end
        for _, line in ipairs(hints) do ns.Print(line) end
    end
end

function ns.GetQuestLevelDescription(id)
    local summary=ns.GetQuestSummary(id)
    return string.format("Quest level %s | Minimum pickup level: %s", summary.level,
        summary.minimumKnown and tostring(summary.minimumLevel) or "unknown")
end

function ns.ShowQuestDetails(tooltip, id, bodyOnly)
    if not bodyOnly then tooltip:AddLine(quest.name(id) or ("Quest #" .. id), 1, .82, .18, true) end
    if not bodyOnly then tooltip:AddLine(ns.GetQuestLevelDescription(id), .75, .75, .75, true) end
    local progress = safe(C_QuestLog.GetQuestObjectives, id)
    if progress and #progress > 0 then
        for _, row in ipairs(progress) do
            tooltip:AddLine(row.text or "", row.finished and .4 or 1, row.finished and 1 or .85, .4, true)
        end
    else
        for _, text in ipairs(Get(id, "objectivesText") or {}) do tooltip:AddLine(text, .92, .92, .92, true) end
    end
    if bodyOnly then tooltip:AddLine(ns.GetQuestLevelDescription(id), .75, .75, .75, true) end
    local note = ns.GetQuestSummary(id).availabilityNote
    if note then tooltip:AddLine(note, .65, .8, 1, true) end
    local hints = ns.GetPrerequisiteHints(id)
    if #hints>0 then
        tooltip:AddLine("Missing quest turn-ins:", .65, .8, 1)
        for _, line in ipairs(hints) do tooltip:AddLine(line, .85, .85, .85, true) end
    end
    Release(quest, id)
end

-- Kept local in production; pure helpers are exposed only to the offline harness.
if ns.testing then ns.test = { MergeMap = MergeMap, Eligible = Eligible } end
