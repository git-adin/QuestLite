-- SPDX-License-Identifier: GPL-3.0-or-later
local _, ns = ...
local panel, Render
local PER_PAGE = 4

local function Text(parent, value, font, x, y, width)
    local text = parent:CreateFontString(nil, "OVERLAY", font or "GameFontHighlightSmall")
    text:SetPoint("TOPLEFT", parent, "TOPLEFT", x, y)
    text:SetWidth(width or 620)
    text:SetJustifyH("LEFT")
    text:SetText(value)
    return text
end

local function Button(parent, label, x, y, width, action)
    local button = CreateFrame("Button", nil, parent, "UIPanelButtonTemplate")
    button:SetSize(width, 26)
    button:SetPoint("TOPLEFT", parent, "TOPLEFT", x, y)
    button:SetText(label)
    button:SetScript("OnClick", action)
    return button
end

function ns.SetOption(key, value)
    if key == "levelsBelow" then
        if not ns.IsFiniteNumber(value) then return end
        value = math.max(0, math.min(80, math.floor(value)))
    elseif ns.defaults[key] == nil or type(value) ~= "boolean" then return end
    ns.db[key] = value
    if key == "enabled" and ns.SetLootSparklesEnabled then ns.SetLootSparklesEnabled(value)
    elseif key == "minimapButton" and ns.UpdateMinimapButton then ns.UpdateMinimapButton()
    elseif ns.RequestMap then ns.RequestMap() end
    if panel and panel:IsShown() then Render() end
end

local function Check(parent, key, title, hint, x, y)
    local box = CreateFrame("CheckButton", nil, parent, "UICheckButtonTemplate")
    box:SetSize(26, 26)
    box:SetHitRectInsets(0, -280, 0, -24)
    box:SetPoint("TOPLEFT", parent, "TOPLEFT", x, y)
    Text(box, title, "GameFontNormal", 32, -5, 255)
    Text(box, hint, nil, 32, -25, 255)
    box:SetScript("OnClick", function(self) ns.SetOption(key, not not self:GetChecked()) end)
    panel.checks[key] = box
    return box
end

local function Search()
    panel.selected = nil
    panel.guideMode = nil
    panel.searched = true
    panel.results, panel.more = ns.FindQuestMatches(panel.search:GetText(), 20)
    panel.page = 1
    if #panel.results == 1 then panel.selected = panel.results[1] end
    Render()
end

local function GetPanel()
    if panel then return panel end
    panel = CreateFrame("Frame", "QuestLiteOptions", UIParent, "BackdropTemplate")
    panel:SetSize(700, 580)
    panel:SetPoint("CENTER", UIParent, "CENTER")
    panel:SetClampedToScreen(true)
    panel:SetFrameStrata("DIALOG")
    panel:EnableMouse(true)
    panel:SetMovable(true)
    panel:RegisterForDrag("LeftButton")
    panel:SetScript("OnDragStart", function(self) self:StartMoving() end)
    panel:SetScript("OnDragStop", function(self) self:StopMovingOrSizing() end)
    panel:SetBackdrop({bgFile="Interface\\DialogFrame\\UI-DialogBox-Background",
        edgeFile="Interface\\Tooltips\\UI-Tooltip-Border", tile=true, tileSize=16, edgeSize=16,
        insets={left=4,right=4,top=4,bottom=4}})
    Text(panel, "QuestLite", "GameFontNormalLarge", 20, -17)
    Text(panel, "Quest maps and a clear path to your next pickup", nil, 20, -42)
    Button(panel, "X", 650, -12, 30, function() panel:Hide() end)
    panel.tabs = {}
    for index, row in ipairs({{"map", "Map"}, {"filters", "Filters"}, {"guide", "Quest chain"}}) do
        local key, label = row[1], row[2]
        panel.tabs[key] = Button(panel, label, 20+(index-1)*150, -68, 140, function()
            panel.tab=key; Render()
        end)
    end
    panel.pages, panel.checks = {}, {}
    for _, key in ipairs({"map", "filters", "guide"}) do
        local frame = CreateFrame("Frame", nil, panel)
        frame:SetAllPoints(panel)
        panel.pages[key] = frame
    end
    local map = panel.pages.map
    Text(map, "Where quests appear", "GameFontNormalLarge", 24, -112)
    Check(map, "map", "World map icons", "Pickup and ready turn-in locations.", 24, -148)
    Check(map, "minimap", "Minimap icons", "Nearby quests as you travel.", 24, -214)
    Check(map, "available", "Quest pickups", "Show quests you can start.", 24, -280)
    Check(map, "turnins", "Ready turn-ins", "Keep completed quest destinations visible.", 24, -346)
    Check(map, "minimapButton", "Minimap options button", "Drag the button around the minimap.", 356, -148)
    Check(map, "dropChances", "Quest item drop chances", "Database estimates in item and creature tooltips.", 356, -214)
    Check(map, "enabled", "Quest loot sparkles", "Switching off needs a full game restart.", 356, -280)
    Text(map, "Click a quest marker to view its quest chain. Right-click to hide an individual pickup.", nil, 24, -444)
    local filters = panel.pages.filters
    Text(filters, "Choose the pickups you want to see", "GameFontNormalLarge", 24, -112)
    Check(filters, "filterAvailable", "Only available quests", "Check known level, faction, class and quest requirements.", 24, -148)
    Check(filters, "hidePvPQuests", "Hide PvP pickups", "Battleground and other known PvP quests.", 24, -224)
    Check(filters, "hideClothQuests", "Hide cloth donations", "Capital reputation and repeatable runecloth quests.", 24, -300)
    Check(filters, "itemDropLocations", "Show item-started quests", "Dropped quest starters: source areas or known zone-drop destinations.", 356, -148)
    Check(filters, "showLowLevel", "Show all low-level quests", "Ignore the normal lower-level cutoff.", 356, -224)
    Text(filters, "Normal lower-level cutoff", "GameFontNormal", 356, -308, 260)
    panel.levelText = Text(filters, "", nil, 356, -337, 210)
    panel.minus = Button(filters, "-", 356, -365, 36, function() ns.SetOption("levelsBelow", ns.db.levelsBelow-1) end)
    panel.plus = Button(filters, "+", 402, -365, 36, function() ns.SetOption("levelsBelow", ns.db.levelsBelow+1) end)
    Text(filters, "These filters hide pickups, not ready turn-ins. Settings are saved for this character.", nil, 24, -444)
    local guide = panel.pages.guide
    panel.search = CreateFrame("EditBox", nil, guide, "InputBoxTemplate")
    panel.search:SetSize(480, 28)
    panel.search:SetPoint("TOPLEFT", guide, "TOPLEFT", 28, -112)
    panel.search:SetAutoFocus(false)
    panel.search:SetScript("OnEnterPressed", function(self) self:ClearFocus(); Search() end)
    panel.search:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)
    Button(guide, "Search quests", 526, -112, 148, Search)
    panel.guideTitle = Text(guide, "", "GameFontNormalLarge", 24, -158, 470)
    panel.guideTitle:SetWordWrap(false)
    panel.back = Button(guide, "Back to results", 514, -153, 160, function()
        panel.selected=nil
        if not panel.results or #panel.results==0 then panel.search:SetText(""); panel.searched=false end
        panel.page=1; Render()
    end)
    panel.guideInfo = Text(guide, "", nil, 24, -187, 650)
    panel.guideModes={}
    for index,mode in ipairs({"prereqs","next"}) do
        panel.guideModes[mode]=Button(guide,mode=="next" and "Next in chain" or "Prerequisites",
            24+(index-1)*180,-239,170,function()
                panel.guideMode=mode; panel.page=1; Render()
            end)
    end
    panel.rows = {}
    for index=1,PER_PAGE do
        local y = -279-(index-1)*56
        local row = {}
        row.button = Button(guide, "", 24, y, 650, function(self)
            if self.questID then ns.OpenQuestGuide(self.questID,panel.selected and panel.guideMode) end
        end)
        row.detail = Text(guide, "", nil, 32, y-30, 630)
        panel.rows[index]=row
    end
    panel.previous = Button(guide, "Previous", 24, -508, 100, function()
        if panel.page>1 then panel.page=panel.page-1; Render() end
    end)
    panel.next = Button(guide, "Next", 574, -508, 100, function()
        panel.page=panel.page+1; Render()
    end)
    panel.pageText = Text(guide, "", nil, 148, -515, 400)
    Button(panel, "Hidden quests", 20, -546, 145, function() ns.ShowHiddenQuests() end)
    Button(panel, "Refresh markers", 177, -546, 145, function() ns.RequestMap(nil,"FORCE_REFRESH") end)
    Button(panel, "Close", 574, -546, 100, function() panel:Hide() end)
    panel:SetScript("OnHide", function(self) self.search:ClearFocus(); self:StopMovingOrSizing() end)
    panel:RegisterEvent("QUEST_TURNED_IN")
    panel:RegisterEvent("QUEST_LOG_UPDATE")
    panel:SetScript("OnEvent", function(self, event)
        if self:IsShown() and self.tab=="guide" and self.selected then
            if event=="QUEST_TURNED_IN" then self.chainKey=nil end
            local key=ns.GetMapStateKey(true)
            if event=="QUEST_TURNED_IN" or key~=self.routeKey then Render() end
        end
    end)
    if UISpecialFrames then table.insert(UISpecialFrames,"QuestLiteOptions") end
    return panel
end

Render = function()
    for key, page in pairs(panel.pages) do page:SetShown(key==panel.tab) end
    for key, box in pairs(panel.checks) do box:SetChecked(ns.db[key]) end
    panel.levelText:SetText(ns.db.showLowLevel and "Cutoff is bypassed while showing all." or ("Hide more than "..ns.db.levelsBelow.." levels below me."))
    for key, button in pairs(panel.tabs) do button:SetText((key==panel.tab and "|cffffd100" or "|cffffffff")
        .. ({map="Map",filters="Filters",guide="Quest chain"})[key] .. "|r") end
    if panel.tab~="guide" then panel.search:ClearFocus(); return end
    panel.back:SetShown(panel.selected~=nil)
    local entries, truncated, hints = panel.results or {}, panel.more, nil
    if panel.selected then
        local summary = ns.GetQuestSummary(panel.selected)
        hints, entries, truncated = ns.GetPrerequisiteHints(panel.selected)
        entries=entries or {}
        panel.guideMode=panel.guideMode or ((#entries>0 or summary.availabilityNote) and "prereqs" or "next")
        panel.guideTitle:SetText("["..summary.level.."] "..summary.name)
        local location,active,completed=ns.GetQuestLocation(panel.selected)
        local status=completed and "Quest already completed." or active and "In your quest log. Return here when the objectives are complete."
            or (#entries>0 and "Complete required steps; choose one when marked Alternative. Click a step for details."
                or (#hints>0 and table.concat(hints,"\n") or "No missing quest turn-ins found. Other requirements may still apply."))
        if not active and not completed and summary.availabilityNote then status=summary.availabilityNote end
        if panel.guideMode=="next" then
            local key=panel.selected..":"..ns.GetMapStateKey(true)
            if panel.chainKey~=key then
                panel.chainSteps,panel.chainMore=ns.GetNextChainSteps(panel.selected)
                panel.chainKey=key
            end
            entries,truncated=panel.chainSteps,panel.chainMore
            status=#entries>0 and "Known direct follow-ups. Other requirements may apply. Click a quest for its chain."
                or "No known follow-up quests in the database."
        end
        panel.guideInfo:SetText(ns.GetQuestLevelDescription(panel.selected).."\n"..location.."\n"..status)
        panel.routeKey=ns.GetMapStateKey(true)
    else
        panel.guideTitle:SetText("Find a quest for your character")
        panel.guideInfo:SetText(#entries>0 and "Choose a quest below." or panel.searched and "No matching quests. Try a shorter name or a quest link." or "Search part of a quest name, paste a quest link, or click a map marker.")
    end
    for mode,button in pairs(panel.guideModes) do
        button:SetShown(panel.selected~=nil)
        button:SetText((panel.guideMode==mode and "|cffffd100" or "|cffffffff")
            .. (mode=="next" and "Next in chain" or "Prerequisites").."|r")
    end
    local pages=math.max(1,math.ceil(#entries/PER_PAGE))
    panel.page=math.max(1,math.min(panel.page or 1,pages))
    for index, row in ipairs(panel.rows) do
        local offset=(panel.page-1)*PER_PAGE+index
        local entry=entries[offset]
        row.button:SetShown(entry~=nil); row.detail:SetShown(entry~=nil)
        if entry then
            local id=panel.selected and entry.id or entry
            row.button.questID=id
            if panel.selected then
                row.button:SetText(offset..". "..(entry.alternative and "Alternative: " or "")..entry.action.." - "..entry.name)
                row.detail:SetText(entry.location)
            else
                local summary=ns.GetQuestSummary(id)
                row.button:SetText("["..summary.level.."] "..summary.name)
                row.detail:SetText("View quest chain")
            end
        else row.button.questID=nil end
    end
    panel.previous:SetShown(panel.page>1)
    panel.next:SetShown(panel.page<pages)
    panel.pageText:SetText("Page "..panel.page.." of "..pages..(truncated and " | More quests or steps omitted." or ""))
end

function ns.OpenOptions(tab)
    local frame=GetPanel()
    frame.tab=tab or frame.tab or "filters"
    Render(); frame:Show()
end

function ns.OpenQuestGuide(id,mode)
    local frame=GetPanel()
    frame.selected,frame.page=id,1
    frame.guideMode=mode
    frame.search:SetText(ns.GetQuestSummary(id).name)
    frame.search:ClearFocus()
    ns.OpenOptions("guide")
end
