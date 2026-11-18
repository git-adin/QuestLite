-- SPDX-License-Identifier: GPL-3.0-or-later
-- Retires the soft-target settings used by QuestLite's former custom sparkles.
-- Based on the migration in Forever Loot Sparkles v2.0.0 (Ashtar Senior).
local _, ns = ...
local owned = {
    SoftTargetInteract = {[3]=true},
    SoftTargetNameplateInteract = {[0]=true,[1]=true},
    SoftTargetInteractRange = {[60]=true},
    SoftTargetInteractArc = {[2]=true},
    SoftTargetInteractOnlyInRange = {[0]=true},
    SoftTargetIconGameObject = {[1]=true},
    SoftTargetIconInteract = {[1]=true},
    SoftTargetLowPriorityIcons = {[1]=true},
}

local function Numeric(value)
    if ns.IsSecret(value) then return nil end
    if type(value) == "string" then value = tonumber(value) end
    if ns.IsFiniteNumber(value) then return value end
end

-- False requests a retry after combat. Failed writes keep the saved originals
-- for the next bounded pass/login; unknown keys are never sent to SetCVar.
function ns.RestoreLegacySoftTargets(final)
    local saved = ns.db and ns.db.savedCVars
    if type(saved) ~= "table" then return true end
    if InCombatLockdown() then return false end
    local pending = false
    for name, values in pairs(owned) do
        local original = Numeric(saved[name])
        if original then
            local current = Numeric(ns.Safe(C_CVar and C_CVar.GetCVar, name))
            if not current then
                pending = true
            elseif current == original then
                if final then saved[name] = nil end
            elseif values[current] then
                ns.TryAction("Restore legacy CVar " .. name, C_CVar.SetCVar, name, tostring(original))
                if Numeric(ns.Safe(C_CVar.GetCVar, name)) ~= original then pending = true
                elseif final then saved[name] = nil end
            else
                -- A different value is a later player choice. Leave it alone.
                saved[name] = nil
            end
        else
            saved[name] = nil
        end
    end
    if final and not pending then ns.db.savedCVars = nil end
    return true
end
