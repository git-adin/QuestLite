-- SPDX-License-Identifier: GPL-3.0-or-later
local _, ns = ...
local picker
local PAGE_SIZE = 12

local function ValidID(id)
    return ns.IsFiniteNumber(id) and id > 0 and id == math.floor(id)
end

function ns.SetQuestHidden(id, hidden)
    if not ValidID(id) then return end
    local wanted = hidden and true or nil
    if ns.db.hiddenQuests[id] == wanted then return end
    ns.db.hiddenQuests[id] = wanted
    ns.hiddenQuestRevision = (ns.hiddenQuestRevision or 0) + 1
    if ns.RequestMap then ns.RequestMap() end
end

function ns.RestoreAllQuests()
    if not next(ns.db.hiddenQuests) then ns.Print("No hidden quest pickups."); return end
    ns.db.hiddenQuests = {}
    ns.hiddenQuestRevision = (ns.hiddenQuestRevision or 0) + 1
    if picker then picker:Hide() end
    if ns.RequestMap then ns.RequestMap() end
    ns.Print("Restored all hidden quest pickups.")
end

local function Button(parent, label, width, x, y)
    local button = CreateFrame("Button", nil, parent, "UIPanelButtonTemplate")
    button:SetSize(width, 22)
    button:SetPoint("TOPLEFT", parent, "TOPLEFT", x, y)
    button:SetText(label)
    return button
end

local function Render()
    local start = (picker.page - 1) * PAGE_SIZE
    for index, button in ipairs(picker.rows) do
        local id = picker.ids[start + index]
        button.questID = id
        if id then
            local summary = ns.GetQuestSummary(id)
            button:SetText(string.format("%s [%d] %s", picker.viewing and "View" or picker.restoring and "Restore" or "Hide", summary.level, summary.name))
            button:Show()
        else button:Hide() end
    end
    picker.pageText:SetText(string.format("%d / %d", picker.page, math.max(1, math.ceil(#picker.ids / PAGE_SIZE))))
end

local function GetPicker()
    if picker then return picker end
    picker = CreateFrame("Frame", "QuestLiteQuestPicker", UIParent, "BackdropTemplate")
    picker:SetSize(400, 370)
    picker:SetPoint("CENTER", UIParent, "CENTER")
    picker:SetClampedToScreen(true)
    picker:SetFrameStrata("DIALOG")
    picker:SetFrameLevel(100)
    picker:EnableMouse(true)
    picker:SetBackdrop({bgFile="Interface\\DialogFrame\\UI-DialogBox-Background",
        edgeFile="Interface\\Tooltips\\UI-Tooltip-Border", tile=true, tileSize=16, edgeSize=16,
        insets={left=4,right=4,top=4,bottom=4}})
    picker.title = picker:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    picker.title:SetPoint("TOPLEFT", picker, "TOPLEFT", 12, -14)
    Button(picker, "X", 24, 364, -8):SetScript("OnClick", function() picker:Hide() end)
    picker.rows = {}
    for index=1,PAGE_SIZE do
        local button = Button(picker, "", 376, 12, -36 - (index-1)*24)
        button:SetScript("OnClick", function(self)
            local id, restoring, viewing = self.questID, picker.restoring, picker.viewing
            if not id then return end
            picker:Hide()
            if viewing then ns.OpenQuestGuide(id); return end
            ns.SetQuestHidden(id, not restoring)
            ns.Print((restoring and "Restored: " or "Hidden pickup: ") .. ns.GetQuestSummary(id).name
                .. (restoring and "" or ". Use /ql hidden to restore."))
            if restoring then ns.ShowHiddenQuests() end
        end)
        picker.rows[index] = button
    end
    Button(picker, "Previous", 90, 12, -334):SetScript("OnClick", function()
        if picker.page > 1 then picker.page=picker.page-1; Render() end
    end)
    Button(picker, "Next", 90, 298, -334):SetScript("OnClick", function()
        if picker.page*PAGE_SIZE < #picker.ids then picker.page=picker.page+1; Render() end
    end)
    picker.pageText=picker:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    picker.pageText:SetPoint("TOP", picker, "TOP", 0, -340)
    picker:SetScript("OnHide", function(self) self.ids={}; self.owner=nil end)
    picker:RegisterEvent("PLAYER_REGEN_DISABLED")
    picker:SetScript("OnEvent", function(self) self:Hide() end)
    if UISpecialFrames then table.insert(UISpecialFrames, "QuestLiteQuestPicker") end
    return picker
end

local function ShowPicker(ids, restoring, viewing)
    if #ids == 0 then
        if picker then picker:Hide() end
        if restoring then ns.Print("No hidden quest pickups.") end
        return
    end
    table.sort(ids, function(a,b)
        local left,right=ns.GetQuestSummary(a).name,ns.GetQuestSummary(b).name
        if left~=right then return left<right end
        return a<b
    end)
    local frame=GetPicker()
    frame.ids,frame.page,frame.restoring,frame.viewing=ids,1,restoring,viewing
    frame.title:SetText(viewing and "Choose a quest" or restoring and "Restore hidden quest pickups" or "Hide a quest pickup")
    Render(); frame:Show()
end

function ns.ShowHiddenQuests()
    local ids={}
    for id in pairs(ns.db.hiddenQuests) do ids[#ids+1]=id end
    ShowPicker(ids,true)
end

function ns.MarkerMouseUp(pin, button)
    if button=="LeftButton" and not (IsShiftKeyDown and IsShiftKeyDown()) and ns.OpenQuestGuide then
        local ids={}
        for id in pairs(pin.data and pin.data.quests or {}) do ids[#ids+1]=id end
        if #ids==1 then ns.OpenQuestGuide(ids[1]) else ShowPicker(ids,false,true) end
        if ns.HideMarkerTooltip then ns.HideMarkerTooltip(pin) end
        return
    end
    if button~="RightButton" and not (button=="LeftButton" and IsShiftKeyDown and IsShiftKeyDown()) then return end
    local ids={}
    for id,entry in pairs(pin.data and pin.data.quests or {}) do
        if entry.kind=="pickup" then ids[#ids+1]=id end
    end
    if #ids==1 and button=="LeftButton" then
        ns.SetQuestHidden(ids[1],true)
        ns.Print("Hidden pickup: "..ns.GetQuestSummary(ids[1]).name..". Use /ql hidden to restore.")
    else ShowPicker(ids,false) end
    if ns.HideMarkerTooltip then ns.HideMarkerTooltip(pin) end
end
