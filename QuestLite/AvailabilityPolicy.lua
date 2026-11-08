-- SPDX-License-Identifier: GPL-3.0-or-later
-- Compact consumer policy, separate from QuestieDB's raw requirements.
-- IDs checked against Questie v12.6.4 QuestieQuestBlacklist.lua (Forever book
-- HIDE_ON_MAP entries and InvasionQuests). No Questie runtime is required.
local _, ns = ...
-- Confirmed missing link in the installed Forever database: both Mankrik
-- entries are recorded as standalone quests. Keep corrections local, so the
-- provider's shared data/cache and other addons are never changed.
ns.chainPrerequisiteOverrides = {
    [95774] = {4921}, -- Her Name Is Olgra follows Lost in Battle.
    [98823] = {95664}, -- Earthen Echo follows Elder Knowledge (relic drop).
    [98824] = {95810}, -- Prehistoric Prism follows Lost Relic Carry (relic drop).
    [92458] = {92432}, -- Heart of Disruption (Alliance): An Alarming Request.
    [92459] = {92458}, -- Friend of the Kirin Tor: Heart of Disruption.
    [96984] = {92434}, -- Heart of Disruption (Horde): Blood in the Streets.
    [97287] = {96984}, -- Shrewd Negotiations: Heart of Disruption.
}
-- sourceItemId is quest-provided, not an inventory prerequisite. The relic
-- follow-ups above unlock on prerequisite turn-in, even if the provided copy
-- is not in the player's bags yet. See ItemGateAudit.md for verification.
local function Set(ids)
    local result = {}
    for _, id in ipairs(ids) do result[id] = true end
    return result
end
ns.pickupPolicy = {
    -- Collection bookkeeping creates a false catalog at the library trainers.
    -- The four library milestones are similarly conditional collection entries.
    collection = Set({78124,78127,78142,78143,78145,78146,78147,78148,78149,
        79091,79092,79093,79094,79095,79096,79097,79535,79947,79948,79949,
        79950,79951,79952,79953,81947,81949,81951,81952,81953,81954,81955,81956,
        84395,84396,84397,84398,84399,84400,84401,84402,
        78150,79536,82208,97286}),
    -- No reliable global Forever invasion-state API is exposed. Require a
    -- current server offer instead of advertising inactive invasion quests.
    event = Set({9085,9094,9153,9154,9260,9261,9262,9263,9264,9265,9292,9295,
        9299,9300,9301,9302,9304,9310,9317,9318,9320,9321,9333,9334,9335,
        9336,9337,9341,9343}),
}
