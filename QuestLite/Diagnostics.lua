-- SPDX-License-Identifier: GPL-3.0-or-later
local addon, ns = ...
local LIMIT = 10
local notified = false

local function Text(value, limit)
    if ns.IsSecret(value) or type(value) ~= "string" then return "Unavailable" end
    return value:sub(1, limit)
end

local function History()
    ns.LoadSettings()
    local saved, clean = ns.db.blockedActions, {}
    if type(saved) == "table" then
        for index = math.max(1, #saved - LIMIT + 1), #saved do
            local row = saved[index]
            if type(row) == "table" and type(row.action) == "string" and type(row.event) == "string" then
                clean[#clean + 1] = {
                    action = Text(row.action, 160), event = Text(row.event, 40),
                    context = Text(row.context, 200), stack = Text(row.stack, 1500),
                    combat = row.combat == true,
                }
            end
        end
    end
    ns.db.blockedActions = clean
    return clean
end

-- Used only around calls that were already protected by pcall. This records
-- synchronous context without suppressing events or bypassing UI protections.
function ns.TryAction(label, func, ...)
    local previous = ns.currentAction
    ns.currentAction = label
    local ok, value = pcall(func, ...)
    ns.currentAction = previous
    return ok, value
end

local events = CreateFrame("Frame")
events:RegisterEvent("ADDON_ACTION_BLOCKED")
events:RegisterEvent("ADDON_ACTION_FORBIDDEN")
events:SetScript("OnEvent", function(_, event, blockedAddon, action)
    if ns.IsSecret(blockedAddon) or blockedAddon ~= addon then return end
    local rows = History()
    rows[#rows + 1] = {
        event = Text(event, 40), action = Text(action, 160),
        context = Text(ns.currentAction or "No QuestLite CVar call active", 200),
        stack = Text(ns.Safe(debugstack, 2, 8, 4), 1500),
        combat = ns.Safe(InCombatLockdown) == true,
    }
    if #rows > LIMIT then table.remove(rows, 1) end
    if not notified then
        notified = true
        ns.Print("Blocked UI action recorded: " .. rows[#rows].action .. ". Use /ql errors for details.")
    end
end)

function ns.ReportBlockedActions(clear)
    if clear then
        ns.LoadSettings()
        ns.db.blockedActions = nil
        ns.Print("Recorded blocked-action history cleared. This does not reset Blizzard's warning counter.")
        return
    end
    local rows = History()
    if #rows == 0 then
        ns.Print("No blocked QuestLite actions recorded by this version. Play normally, then use /ql errors if the warning returns.")
        return
    end
    ns.Print("Last " .. #rows .. " blocked actions (oldest first):")
    for index, row in ipairs(rows) do
        ns.Print(string.format("%d. %s: %s [%s; %s]", index, row.event, row.action,
            row.combat and "in combat" or "out of combat", row.context))
    end
end
