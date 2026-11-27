-- SPDX-License-Identifier: GPL-3.0-or-later
local _,ns=...
local api,driver,worker,workID,initialized,state
local cache,count,requests={},0,{}
local safe=ns.Safe
local function Release(entity,id) if entity.InvalidateCache then entity.InvalidateCache(id) end end
local function Contains(rows,id,nested)
    for _,row in ipairs(rows or {}) do
        if (nested and row[1] or row)==id then return true end
    end
    return false
end
local function Analyze(id)
    local item,q=api.Item,api.Quest
    local class=item.Get(id,"class")
    local teaches=item.Get(id,"teachesSpell")
    local related={}
    for _,questID in ipairs(item.Get(id,"relatedQuests") or {}) do related[questID]=true end
    local start=item.Get(id,"startQuest")
    if ns.IsFiniteNumber(start) and start>0 then related[start]=true end
    Release(item,id)
    local active={}
    for index=1,(safe(C_QuestLog.GetNumQuestLogEntries) or 0) do
        local info=safe(C_QuestLog.GetInfo,index)
        if info and not info.isHeader and ns.IsFiniteNumber(info.questID) then active[info.questID]=true end
    end
    local uses,provided,priority,reason=0,false,0,nil
    local conversions,conversionCount,uncertain={},0,false
    local function Supplies(target,visited,depth)
        if target==id then return true end
        if not ns.IsFiniteNumber(target) or visited[target] then return false end
        visited[target]=true
        local parents=conversions[target]
        if not parents then
            parents={}
            for _,parent in ipairs(item.itemDrops(target) or {}) do parents[#parents+1]=parent end
            Release(item,target)
            if conversionCount>=128 then conversions,conversionCount={},0 end
            conversions[target],conversionCount=parents,conversionCount+1
        end
        if depth>=4 and #parents>0 then uncertain=true; return false end
        for _,parent in ipairs(parents) do if Supplies(parent,visited,depth+1) then return true end end
        return false
    end
    local seen={}
    local function Check(questID,source)
        if seen[questID] then return end
        seen[questID]=true
        local applies=ns.QuestAppliesToCharacter(questID)
        if applies==false then return end
        uses=uses+1; provided=provided or source
        local rank,text=0,nil
        if applies==nil then rank,text=1,"Keep: quest use could not be verified."
        elseif active[questID] then rank,text=4,"Keep: needed by an active quest."
        elseif bit.band(q.Get(questID,"specialFlags") or 0,1)~=0
            or bit.band(q.Get(questID,"questFlags") or 0,4096)~=0 then
            rank,text=3,"Keep: used by a repeatable or daily quest."
        else
            local completed=safe(C_QuestLog.IsQuestFlaggedCompleted,questID)
            if completed~=true then
                rank,text=2,completed==false and "Keep: a known quest use is not finished."
                    or "Keep: quest completion could not be verified."
            end
        end
        if rank>priority then priority,reason=rank,text end
        Release(q,questID)
    end
    local started=debugprofilestop()
    for index,questID in ipairs(q.GetAllIds()) do
        local objectives=q.Get(questID,"objectives") or {}
        local starters=q.Get(questID,"startedBy") or {}
        local source=q.Get(questID,"sourceItemId")==id
        local supplies=false
        for _,row in ipairs(objectives[3] or {}) do
            if Supplies(row[1],{},1) then supplies=true; break end
        end
        if source or related[questID] or supplies
            or Contains(q.Get(questID,"requiredSourceItems"),id)
            or Contains(starters[3],id) then Check(questID,source) end
        Release(q,questID)
        if index%64==0 or debugprofilestop()-started>=2 then coroutine.yield(); started=debugprofilestop() end
    end
    -- Unknown related IDs must never be silently treated as completed.
    for questID in pairs(related) do Check(questID,false) end
    if uses==0 or (class~=12 and not provided) then return nil end
    if priority>0 then return {text=reason,color={1,.82,.25}} end
    if uncertain then return {text="Keep: additional item conversions could not be verified.",color={1,.82,.25}} end
    if class~=12 or (ns.IsFiniteNumber(teaches) and teaches>0) then
        return {text="Quest use finished; this item may have other uses.",color={.65,.8,1}}
    end
    return {text="Quest leftover: safe to discard for known quests.",color={.4,1,.4}}
end
local function OwnLine(tip)
    local index=tip.QuestLiteSafetyLine
    if not index then return end
    local name=tip.GetName and safe(tip.GetName,tip)
    local line=(name and _G[name.."TextLeft"..index]) or tip["TextLeft"..index]
    -- Some tooltip rebuilds do not dispatch the legacy clear script. Never
    -- overwrite a native item line merely because it reused our old index.
    if not line or safe(line.GetText,line)~=tip.QuestLiteSafetyText then
        tip.QuestLiteSafetyLine,tip.QuestLiteSafetyText=nil,nil
        return nil
    end
    return line
end
local function Display(tip,result)
    if not tip:IsShown() or not ns.db.questItemSafety then return end
    local line=OwnLine(tip)
    if line and line.SetText then
        line:SetText(result and result.text or "")
        tip.QuestLiteSafetyText=result and result.text or ""
        if result and line.SetTextColor then line:SetTextColor(unpack(result.color)) end
    elseif result and not tip.QuestLiteSafetyLine then
        tip:AddLine(result.text,result.color[1],result.color[2],result.color[3],true)
        tip.QuestLiteSafetyLine=tip:NumLines()
        tip.QuestLiteSafetyText=result.text
    end
    if result then tip:Show() end
end
local function Tooltip(tip,data)
    requests[tip]=nil -- Do not apply an older result to invalid/restricted data.
    if not api or not ns.db.questItemSafety or ns.IsSecret(data) then return end
    local id=type(data)=="table" and data.id
    if ns.IsSecret(id) then return end
    if not id and tip.GetItem then
        local ok,_,link=pcall(tip.GetItem,tip)
        if ok and not ns.IsSecret(link) and type(link)=="string" then id=tonumber(link:match("item:(%d+)")) end
    end
    if not ns.IsFiniteNumber(id) or id<=0 or id~=math.floor(id) then return end
    requests[tip]=id
    if cache[id]~=nil then Display(tip,cache[id] or nil) else driver:Show() end
end
function ns.RefreshQuestItemSafety()
    cache,count={},0; worker,workID=nil,nil
    for tip in pairs(requests) do
        local line=OwnLine(tip)
        if line and line.SetText then
            local text=ns.db.questItemSafety and "Quest status changed; checking known uses..." or ""
            line:SetText(text); tip.QuestLiteSafetyText=text
            if line.SetTextColor then line:SetTextColor(1,.82,.25) end
        end
    end
    if driver then driver:SetShown(ns.db.questItemSafety) end
end
function ns.InitQuestItems()
    if initialized then return end
    initialized,api=true,LibQuestieDB
    driver=CreateFrame("Frame"); driver:Hide()
    driver:SetScript("OnUpdate",function()
        if not ns.db.questItemSafety then driver:Hide(); return end
        if not worker then
            for tip,id in pairs(requests) do
                if tip:IsShown() and cache[id]==nil then
                    workID=id; worker=coroutine.create(function() return Analyze(id) end); break
                end
            end
            if not worker then driver:Hide(); return end
        end
        local ok,result=coroutine.resume(worker)
        if not ok or coroutine.status(worker)=="dead" then
            if count>=64 then cache,count={},0 end
            cache[workID],count=ok and result or false,count+1
            if cache[workID]==nil then cache[workID]=false end
            for tip,id in pairs(requests) do if id==workID then Display(tip,ok and result or nil) end end
            worker,workID=nil,nil
        end
    end)
    local events=CreateFrame("Frame")
    for _,event in ipairs({"QUEST_LOG_UPDATE","QUEST_TURNED_IN","PLAYER_ENTERING_WORLD"}) do events:RegisterEvent(event) end
    events:SetScript("OnEvent",function(_,event)
        local key=ns.GetMapStateKey(true)
        if event~="QUEST_LOG_UPDATE" or key~=state then state=key; ns.RefreshQuestItemSafety() end
    end)
    local function Relevant(tip) return tip==GameTooltip or tip==ItemRefTooltip end
    for _,tip in ipairs({GameTooltip,ItemRefTooltip}) do
        if tip.HasScript and tip:HasScript("OnTooltipCleared") then
            tip:HookScript("OnTooltipCleared",function(self)
                requests[self]=nil; self.QuestLiteSafetyLine,self.QuestLiteSafetyText=nil,nil
            end)
        end
    end
    if TooltipDataProcessor and TooltipDataProcessor.AddTooltipPostCall and Enum and Enum.TooltipDataType then
        TooltipDataProcessor.AddTooltipPostCall(Enum.TooltipDataType.Item,function(tip,data) if Relevant(tip) then Tooltip(tip,data) end end)
    else
        for _,tip in ipairs({GameTooltip,ItemRefTooltip}) do
            if tip.HasScript and tip:HasScript("OnTooltipSetItem") then tip:HookScript("OnTooltipSetItem",Tooltip) end
        end
    end
end
if ns.testing then ns.testQuestItems={Tooltip=Tooltip,CacheSize=function() return count end} end
