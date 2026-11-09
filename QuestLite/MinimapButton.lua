-- SPDX-License-Identifier: GPL-3.0-or-later
local _, ns = ...
local button

local function Position()
    local angle = math.rad(ns.db.minimapButtonAngle)
    local x = math.cos(angle) * (Minimap:GetWidth() / 2 + 8)
    local y = math.sin(angle) * (Minimap:GetHeight() / 2 + 8)
    button:ClearAllPoints()
    button:SetPoint("CENTER", Minimap, "CENTER", x, y)
end

local function StopDrag()
    button:SetScript("OnUpdate", nil)
end

function ns.UpdateMinimapButton()
    if not button then return end
    Position()
    button:SetShown(ns.db.minimapButton)
end

function ns.StyleOptionsButton(target)
    target:SetSize(31, 31)
    target:RegisterForClicks("LeftButtonUp")
    local background = target:CreateTexture(nil, "BACKGROUND")
    background:SetTexture("Interface\\Minimap\\UI-Minimap-Background")
    background:SetSize(24, 24)
    background:SetPoint("CENTER")
    local icon = target:CreateTexture(nil, "ARTWORK")
    icon:SetTexture("Interface\\GossipFrame\\AvailableQuestIcon")
    icon:SetSize(20, 20)
    icon:SetPoint("CENTER")
    local border = target:CreateTexture(nil, "OVERLAY")
    border:SetTexture("Interface\\Minimap\\MiniMap-TrackingBorder")
    border:SetSize(54, 54)
    border:SetPoint("TOPLEFT")
    target:SetHighlightTexture("Interface\\Minimap\\UI-Minimap-ZoomButton-Highlight")
    target:SetScript("OnClick", function() SlashCmdList.QUESTLITE("") end)
    target:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_LEFT")
        GameTooltip:AddLine("QuestLite", 1, .82, 0)
        GameTooltip:AddLine("Click to open options.", 1, 1, 1)
        if self == button then GameTooltip:AddLine("Drag to move around the minimap.", .7, .7, .7) end
        GameTooltip:Show()
    end)
    target:SetScript("OnLeave", function(self) if GameTooltip:GetOwner() == self then GameTooltip:Hide() end end)
end

function ns.InitMinimapButton()
    if button or not Minimap then return end
    button = CreateFrame("Button", "QuestLiteMinimapButton", Minimap)
    ns.StyleOptionsButton(button)
    button:SetFrameLevel(Minimap:GetFrameLevel() + 8)
    button:RegisterForDrag("LeftButton")
    button:SetScript("OnDragStart", function()
        GameTooltip:Hide()
        button:SetScript("OnUpdate", function()
            local scale = Minimap:GetEffectiveScale()
            local mx, my = Minimap:GetCenter()
            local px, py = GetCursorPosition()
            if not ns.IsFiniteNumber(scale) or scale <= 0 or not ns.IsFiniteNumber(mx)
                or not ns.IsFiniteNumber(my) or not ns.IsFiniteNumber(px) or not ns.IsFiniteNumber(py) then return end
            ns.db.minimapButtonAngle = math.deg(math.atan2(py / scale - my, px / scale - mx)) % 360
            Position()
        end)
    end)
    button:SetScript("OnDragStop", StopDrag)
    button:SetScript("OnHide", function()
        StopDrag()
        if GameTooltip:GetOwner() == button then GameTooltip:Hide() end
    end)
    Minimap:HookScript("OnSizeChanged", function() Position() end)
    ns.UpdateMinimapButton()
    if ns.testing then ns.testMinimapButton = button end
end
