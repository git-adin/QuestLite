-- Minimal offline client surface. Tests drive events and frames explicitly.
frames, messages, settings, writes = {}, {}, {}, {}
now, combat, clockMS = 0, false, 0
function print(value) messages[#messages + 1] = value end
function GetTime() return now end
function debugprofilestop() clockMS = clockMS + .02; return clockMS end
function InCombatLockdown() return combat end
function issecretvalue() return false end
function strlower(s) return s:lower() end
function wipe(t) for k in pairs(t) do t[k] = nil end end
function CreateFromMixins(...)
    local result = {}
    for i = 1, select('#', ...) do for k,v in pairs(select(i,...)) do result[k] = v end end
    return result
end
local methods = {}
function methods:RegisterEvent(e) self.events[e] = true end
function methods:UnregisterEvent(e) self.events[e] = nil end
function methods:SetScript(e,f) self.scripts[e] = f end
function methods:GetScript(e) return self.scripts[e] end
function methods:Show() self.shown = true end
function methods:Hide() self.shown = false end
function methods:IsShown() return self.shown end
function methods:IsVisible() return self.shown end
function methods:SetShown(value) self.shown = value end
function methods:SetTexture(value) self.texture = value; return true end
function methods:SetAtlas(value) self.atlas = value end
function methods:GetTexture() return self.texture end
function methods:GetAtlas() return nil end
function methods:SetText(value) self.text = value end
function methods:SetFont() end
function methods:SetTextColor() end
function methods:SetBackdrop() end
function methods:SetBackdropColor() end
function methods:SetBackdropBorderColor() end
function methods:SetClampedToScreen() end
function methods:SetWidth() end
function methods:SetOwner(owner,anchor) self.owner=owner; self.anchor=anchor; self.lines={} end
function methods:AddLine(text) self.lines[#self.lines+1]=text end
function methods:AddDoubleLine(left,right) self.lines[#self.lines+1]=left..'  '..right end
function methods:NumLines() return #(self.lines or {}) end
function AddNativeTooltipLine(tooltip,text)
    tooltip:AddLine(text)
    local index=#tooltip.lines
    tooltip['TextLeft'..index]={
        GetText=function() return tooltip.lines[index] end,
        SetText=function(_,value) tooltip.lines[index]=value end,
    }
end
function methods:CreateTexture() return CreateFrame('Texture') end
function methods:CreateFontString() return CreateFrame('FontString') end
function methods:SetPoint(...) self.point={...} end
function methods:SetAllPoints() end
function methods:GetWidth() return self.width or 140 end
function methods:GetHeight() return self.height or 140 end
function methods:SetSize(width,height) self.width,self.height=width,height end
function methods:SetRotation() end
function methods:SetVertexColor() end
function methods:SetBlendMode() end
function methods:ClearAllPoints() end
function methods:SetParent() end
function methods:SetFrameLevel() end
function methods:GetFrameLevel() return 10 end
function methods:SetIgnoreParentAlpha() end
function methods:EnableMouse(value) self.mouseClick=value; self.mouseMotion=value end
function methods:IsMouseClickEnabled() return self.mouseClick==true end
function methods:IsMouseMotionEnabled() return self.mouseMotion==true end
function methods:SetFrameStrata(value) self.strata=value end
function methods:UseFrameLevelType(value) self.frameLevelType=value end
function methods:EnableMouseWheel() end
function methods:SetScalingLimits() end
function methods:SetPosition(x,y) self.x,self.y=x,y end
function CreateFrame(kind,name)
    local frame = setmetatable({events={}, scripts={}, shown=true}, {__index=methods})
    if name then _G[name]=frame end
    frames[#frames+1] = frame
    return frame
end
UIParent = CreateFrame()
SlashCmdList = {}
function Fire(event,...)
    for _,frame in ipairs(frames) do
        if frame.events[event] and frame.scripts.OnEvent then frame.scripts.OnEvent(frame,event,...) end
    end
end
function Tick(count)
    for i=1,count do
        now=now+.05
        for _,frame in ipairs(frames) do
            if frame.shown and frame.scripts.OnUpdate then frame.scripts.OnUpdate(frame,.05) end
        end
    end
end
Settings={VarType={Boolean='boolean',Number='number'}, Default={True=true}}
function Settings.CreateSliderOptions(low,high,step) return {minValue=low,maxValue=high,step=step} end
function Settings.CreateSlider(category,setting,options,tooltip) assert(options.step==1) end
function Settings.RegisterVerticalLayoutCategory()
    return {GetID=function() return 1 end}
end
function Settings.RegisterAddOnSetting(category,variable,key,db,kind,label,default)
    local s={key=key,db=db}
    function s:SetValueChangedCallback(f) self.callback=f end
    function s:Change(value) self.db[self.key]=value; self.callback(self,value) end
    settings[key]=s
    return s
end
function Settings.CreateCheckbox() end
function Settings.RegisterInitializer() end
function Settings.RegisterAddOnCategory() end
function Settings.OpenToCategory() end
function CreateSettingsListSectionHeaderInitializer() return {} end
cvars={outlineModeShowLootEffectWhenDisabled='0',SoftTargetInteract='0',SoftTargetNameplateInteract='0',
    SoftTargetInteractRange='10',SoftTargetInteractArc='0',SoftTargetInteractOnlyInRange='1',SoftTargetIconGameObject='0'}
C_CVar={GetCVar=function(name) return cvars[name] end,SetCVar=function(name,value)
    assert(not combat,'CVar write during combat')
    cvars[name]=tostring(value); writes[#writes+1]={name,value}
end}
UnitLevel=function() return 10 end
UnitRace=function() return 'Human','Human',1 end
UnitClass=function() return 'Warrior','WARRIOR',1 end
UnitExists=function() return false end
UnitIsGameObject=function() return false end
IsPlayerSpell=function() return false end
IsSpellKnown=IsPlayerSpell
bit={band=function(a,b)
    local result,place=0,1
    while a>0 or b>0 do
        if a%2==1 and b%2==1 then result=result+place end
        a,b,place=math.floor(a/2),math.floor(b/2),place*2
    end
    return result
end,lshift=function(a,b) return a*2^b end}
quests,npcs,objects,items,completed,active,progress,done,invalidated={},{},{},{},{},{},{},{},{}
local function Entity(data)
    local entity={}
    function entity.Get(id,key) return data[id] and data[id][key] end
    function entity.GetAllIds()
        local result={}; for id in pairs(data) do result[#result+1]=id end; table.sort(result); return result
    end
    for _,key in ipairs({'name','spawns','npcDrops','objectDrops','itemDrops'}) do
        entity[key]=function(id) return entity.Get(id,key) end
    end
    function entity.InvalidateCache(id) invalidated[#invalidated+1]=id end
    return entity
end
mockDropData={wowheadData='return {[100]={[10]=25,[11]=12.345,[12]=0.01},[101]={[10]=75},[102]={[10]=35},[103]={[10]=45},[104]={[10]=55}}',
    cmangosData='return {[100]={[10]=50,[11]=60},[101]={[10]=80},[103]={[10]=90}}'}
mockDropFixes={Era={[100]={[10]=40},[101]={[10]=-1},[102]={[10]=-2},[104]={[10]=0}}}
LibQuestieDB={Quest=Entity(quests),Npc=Entity(npcs),Object=Entity(objects),Item=Entity(items),
    RequireContract=function(v) return v==4 end,
    Support={Get=function(name)
        if name=='QuestieClassicItemDrops' then return mockDropData end
        if name=='QuestieItemDropCorrections' then return mockDropFixes end
        return {private={areaIdToUiMapId='return {[12]=1429,[14]=1411}',areaIdToUiMapIdOverride='return {[14]=1412}'}}
    end}}
C_QuestLog={GetNumQuestLogEntries=function() return #active end,
    GetInfo=function(i) return active[i] and {questID=active[i]} end,
    GetQuestObjectives=function(id) return progress[id] end,
    IsQuestFlaggedCompleted=function(id) return completed[id] or false end,
    IsComplete=function(id) return done[id] or false end}
C_AddOns={IsAddOnLoaded=function() return false end}
C_SkillInfo={GetNumSkillLines=function() return 0 end,GetSkillLineInfo=function() end}
C_Map={GetMapInfo=function(id) return {mapType=id==947 and 0 or 3} end}
GameTooltip={IsOwned=function() return false end,Hide=function() end,SetOwner=function() end,AddLine=function() end,Show=function() end}
MapCanvasPinMixin={OnReleased=function() end}
MapCanvasDataProviderMixin={}
WorldMapFrame=CreateFrame()
WorldMapFrame.mapID=1429
WorldMapFrame.pins={}
function WorldMapFrame:GetMapID() return self.mapID end
function WorldMapFrame:RemoveAllPinsByTemplate() self.pins={} end
function WorldMapFrame:AcquirePin(template,data)
    local pin=CreateFrame()
    for key,value in pairs(QuestLitePinMixin) do pin[key]=value end
    pin.Icon=pin:CreateTexture(); pin.Count=pin:CreateFontString()
    setmetatable(pin,{__index=function(self,key)
        return methods[key] or (rawget(self,'data') and self.data[key])
    end})
    -- Match Forever MapCanvasMixin:AcquirePin: input scripts are installed
    -- from the XML flags BEFORE the custom pin's OnLoad runs.
    pin:EnableMouse(pinTemplateMouseEnabled==true)
    if pin:IsMouseMotionEnabled() then
        assert(pin:GetScript('OnEnter')==nil and pin:GetScript('OnLeave')==nil)
        pin:SetScript('OnEnter',pin.OnMouseEnter)
        pin:SetScript('OnLeave',pin.OnMouseLeave)
    end
    pin:OnLoad(); pin:OnAcquired(data)
    self.pins[#self.pins+1]=pin
    return pin
end
function WorldMapFrame:RemovePin(pin)
    for i,value in ipairs(self.pins) do
        if value==pin then pin:OnReleased(); table.remove(self.pins,i); return end
    end
end
function WorldMapFrame:AddDataProvider(provider) self.provider=provider end

function EnableMinimapMock()
    Minimap=CreateFrame(); Minimap:SetSize(140,140)
    miniMapID, miniPX, miniPY, miniRadius, miniFacing=1429,.2,.3,100,0
    C_Map.GetBestMapForUnit=function() return miniMapID end
    C_Map.GetMapWorldSize=function() return 1000,1000 end
    C_Map.GetPlayerMapPosition=function()
        if miniPX==nil then return nil end
        return {GetXY=function() return miniPX,miniPY end}
    end
    C_Minimap={GetViewRadius=function() return miniRadius end}
    GetPlayerFacing=function() return miniFacing end
    cvars.rotateMinimap='0'
end
