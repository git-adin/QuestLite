-- SPDX-License-Identifier: GPL-3.0-or-later
-- Compact consumer policy, separate from QuestieDB's raw requirements.
-- IDs checked against Questie v12.6.4 QuestieQuestBlacklist.lua (Forever book
-- HIDE_ON_MAP entries and InvasionQuests). No Questie runtime is required.
local _, ns = ...
-- Remote Contact referrals are not offered to the reporting character. The provider
-- records alternative referrals but no reliable closure condition. Require a
-- server offer instead of inventing a Stealing Knowledge breadcrumb flag.
ns.questAvailabilityNotes = {
    [91734] = "Referral to Jediga and the Stealing Knowledge chain. Availability is conditional; a current offer from Andron Gant is required in available-only mode.",
    [91735] = "Referral to Jediga and the Stealing Knowledge chain. Availability is conditional; a current offer from Jes'rimon is required in available-only mode.",
    [91737] = "Referral to Jediga and the Stealing Knowledge chain. Availability is conditional; a current offer from Magatha Grimtotem is required in available-only mode.",
}
-- Verified in game without a writ in bags or bank: Xylem offers this order
-- directly. The writ is still required to complete it. Do not generalize this
-- observation to every crafting order or every quest from Xylem.
ns.npcWritPickups = {
    [94316] = {npc=8379, note="Xylem offers this order without a writ. Completing it still requires the Potion of Demonslaying writ and requested potion."},
}
-- Old Classic tail remains in the provider beside Forever's rewritten route.
-- Keep direct inspection/active quests, but require a real offer for pickups.
ns.legacyQuestReplacements = {
    [3506] = {note="Legacy Betrayed step. Forever's route is Seals of the Sin'dorei, then An Explosive Gambit, then Revenge Exacted. The tome also starts Sin'dorei Tome of Summoning."},
    [3507] = {note="Legacy Betrayed finale. Forever's revised route ends with Revenge Exacted after An Explosive Gambit."},
}
-- Firsthand Forever reports confirm Fishing 1 for Winter Frontier Fishery
-- on both factions and Kurll's Deadliest Catch. No Fishing gate on the hide
-- introduction, and no inferred gate on the Alliance shark quest.
local fishing = {skill={356,1}, note="Requires Fishing (skill 1). Route: Home on the Range, then Winter Frontier Fishery, then Deadliest Catch. The squid can be bought."}
ns.questSkillRequirements = {[89228]=fishing,[91610]=fishing,[91611]=fishing}
-- Forever Timbermaw quests require Neutral, except the Legashi introduction
-- and repeatable horns. Explicit IDs from the Timbermaw reputation guide;
-- native nonempty requirements supersede this missing-field fallback.
ns.questReputationRequirements = {}
local timbermaw = {minimum={576,0}, note="Requires Neutral reputation with Timbermaw Hold. Other quest turn-ins may also apply."}
for _, id in ipairs({86752,86777,86791,86792,86796,86797,86798,86799,86804,
    86812,86813,86814,86925,86926,86927,87346,92065,92066}) do
    ns.questReputationRequirements[id] = timbermaw
end
-- Document Box is tradeable: owning it unlocks these deliveries, without
-- requiring this character to complete the Alcaz rescue chain. Native item
-- requirements take precedence when the provider supplies them.
local documentBox = {items={274041}, note="Requires a Document Box in your bags: buy one, or finish More Valuable Than Gold (Alcaz Prison chain; Westfall 43.4, 67.8). Personal chain completion is optional."}
ns.questPickupItemRequirements = {
    [96376]=documentBox, -- Nazgrel, Horde.
    [96377]=documentBox, -- Renzik, Alliance.
    [96379]=documentBox, -- Rix Xizzix, neutral.
}
-- Tooga moves during his escort. This per-quest stop must not move his normal
-- escort pickup or Torta's destination. Availability is confirmed by NPC offers.
ns.questLocationOverrides = {
    [97540] = {npc=5955,map=1446,x=41,y=54,parent=1560,
        note="During Tooga's Quest, lead Tooga to the oasis at 41, 54 and wait for him to drink. Talk to him when he offers Oasis."},
}
-- Darkspear Islands battleground mark turn-ins and victory quests. These
-- Forever records lack native/Questie PvP tags, including zone-less variants.
-- Explicit IDs avoid localized-title matching or treating every giver as PvP.
ns.additionalPvPQuests = {
    [98887]=true,[98888]=true,[98889]=true,[98890]=true,[98891]=true,[98893]=true,
    [98895]=true,[98896]=true,[98897]=true,[98898]=true,[98899]=true,[98901]=true,
    [98903]=true,[98904]=true,[98905]=true,[98906]=true,[98907]=true,[98908]=true,
}
-- Capital reputation cloth donations, including both Skyborne factions.
-- IDs verified against the installed provider; no localized title matching at runtime.
ns.clothDonationQuests = {
    [7791]=true,[7792]=true,[7793]=true,[7794]=true,[7795]=true,[7796]=true,[7798]=true,[7799]=true,[7800]=true,[7801]=true,
    [7802]=true,[7803]=true,[7804]=true,[7805]=true,[7806]=true,[7807]=true,[7808]=true,[7809]=true,[7811]=true,[7812]=true,
    [7813]=true,[7814]=true,[7817]=true,[7818]=true,[7819]=true,[7820]=true,[7821]=true,[7822]=true,[7823]=true,[7824]=true,
    [7825]=true,[7826]=true,[7827]=true,[7831]=true,[7832]=true,[7833]=true,[7834]=true,[7835]=true,[7836]=true,[7837]=true,
    [99191]=true,[99192]=true,[99193]=true,[99194]=true,[99195]=true,[99196]=true,[99197]=true,[99198]=true,[99199]=true,[99200]=true,
}
-- Historical missing links for older QuestieDB builds. Native prerequisite
-- expressions take precedence once supplied; no provider-owned data is changed.
-- Neutral Powderfuse follow-up unlocked by either faction's introduction.
-- Kept separate from mandatory ALL lists: the opposite-faction lead is not required.
ns.chainAlternativeOverrides = {
    [95288] = {93976, 94928}, -- Smuggler's Paradise: Goblin Trader OR A Few Furs for Friz.
}
ns.chainPrerequisiteOverrides = {
    [91611] = {91610}, -- Kurll: Deadliest Catch follows Winter Frontier Fishery.
    [95183] = {95424}, -- Step One: Rock follows Might Makes Right; that quest follows Land of Giants.
    [93976] = {93788}, -- The Goblin Trader follows Borrowed Blades (Horde).
    [94928] = {94925}, -- A Few Furs for Friz follows A Fur Trade (Alliance).
    [95293] = {95288}, -- Smuggler's Special follows Smuggler's Paradise.
    [95774] = {4921}, -- Her Name Is Olgra follows Lost in Battle.
    [98823] = {95664}, -- Earthen Echo follows Elder Knowledge (relic drop).
    [98824] = {95810}, -- Prehistoric Prism follows Lost Relic Carry (relic drop).
    [92458] = {92432}, -- Heart of Disruption (Alliance): An Alarming Request.
    [92459] = {92458}, -- Friend of the Kirin Tor: Heart of Disruption.
    [96984] = {92434}, -- Heart of Disruption (Horde): Blood in the Streets.
    [97287] = {96984}, -- Shrewd Negotiations: Heart of Disruption.
    [545] = {93680}, -- Dalaran Patrols also needs Key to the City; native 544 still applies.
    [92434] = {545, 93680}, -- Blood in the Streets needs patrol and key turn-ins (both).
    [98252] = {98251}, -- A Void Path follows Never Coming Back (Forever, all Horde classes).
    [98094] = {528}, -- Scout Support requires Battle of Hillsbrad part II turned in.
    [98095] = {98094}, -- Valuable Vantages follows Scout Support.
    [95621] = {95495}, -- Trouble in the Valley follows The Hermit Tanner delivery.
    [95508] = {95621}, -- Unwelcome Guests follows Trouble in the Valley.
    -- Verified Undead Paladin / Moonsilver Blade chain: fallback for older
    -- providers that lack these prerequisite fields.
    [91859] = {91858}, -- A Curious Pair <- Diplomatic Incident.
    [91860] = {91859}, -- A Grim Fate <- A Curious Pair.
    [91861] = {91860}, -- Into Fenris Keep <- A Grim Fate.
    [91862] = {91861}, -- Lumina Windsinger <- Into Fenris Keep.
    [96204] = {91862}, -- The Windshaper's Wrath <- Lumina Windsinger.
    [95034] = {96204}, -- The Debt <- The Windshaper's Wrath.
    [95036] = {95034}, -- A Moon-Kissed Blade <- The Debt.
    [95111] = {95036}, -- An Underrated Talent <- A Moon-Kissed Blade.
    [95125] = {95111}, -- Ott's Masterwork <- An Underrated Talent.
    [95126] = {95125}, -- The Moonsilver Blade <- Ott's Masterwork.
    [95140] = {95126}, -- Old Fire-Eye <- The Moonsilver Blade.
}
-- Verified missing character restrictions in QuestieDB 1.1.0. Apply only to
-- these exact old values; newer native masks always win. See ClassSeasonAudit.md.
ns.characterQuestFieldOverrides = {
    [96136] = {requiredClasses = {was = 0, value = 64}}, -- Call of Air: Shaman.
    [93797] = {requiredClasses = {was = 0, value = 128}}, -- Boughs in the Wind: Mage.
    [98341] = {requiredClasses = {was = 0, value = 1024}}, -- Windborne Cat Spirit: Druid.
    [98404] = {requiredClasses = {was = 0, value = 1024}}, -- Windborne Cat Spirit: Druid.
    [98738] = {requiredClasses = {was = 0, value = 1024}}, -- Windborne Cat blessing: Druid.
    -- Add only Horde Skyborne to the old non-Undead Horde mask. Forsaken and
    -- Alliance remain excluded; a future provider correction supersedes this.
    [1049] = {requiredRaces = {was = 162, value = 8589934754}}, -- Compendium of the Fallen.
}
-- These IDs leak into the Forever data with no class or season restrictions.
-- They are Alonso's Season of Discovery Warrior rune turn-ins, not general
-- Forever pickups. Keep the classification visible when a Warrior browses
-- unfiltered candidates; never infer a season from numeric quest-ID ranges.
local sodWarrior = {season = "Season of Discovery", requiredClasses = 1,
    label = "Season of Discovery / Warrior"}
ns.questRestrictions = {
    -- Questie's SoD phase replaces 2856/2849 with these item-217268 variants.
    -- They have no native prerequisite/skill gates in the Forever provider.
    [82656] = {season = "Season of Discovery", label = "Season of Discovery / Leatherworking"},
    [82657] = {season = "Season of Discovery", label = "Season of Discovery / Leatherworking"},
    [3504] = {label = "NPC offer required"}, -- Betrayed: listed minimum 44, but availability unverified on Forever.
    [80001] = {season = "Season of Discovery", label = "Season of Discovery"}, -- Rekindle; excluded by Questie 12.9.0.
    [79090] = {season = "Season of Discovery", label = "Season of Discovery"}, -- Repelling Invaders.
    [79098] = {season = "Season of Discovery", label = "Season of Discovery"}, -- Clear the Forest!.

    [78270] = {requiredClasses = 8, label = "Rogue"}, -- Goblin Lockpicks: missing provider class mask.
    [78132] = sodWarrior, -- Dragonslayer's Helm.
    [78133] = sodWarrior, -- Dragonslayer's Shield.
    [78134] = sodWarrior, -- Dragonslayer's Lance.
}
-- sourceItemId is quest-provided, not an inventory prerequisite. The relic
-- follow-ups above unlock on prerequisite turn-in, even if the provided copy
-- is not in the player's bags yet. See ItemGateAudit.md for verification.
local function Set(ids)
    local result = {}
    for _, id in ipairs(ids) do result[id] = true end
    return result
end
-- Item-started crafting orders, including records that also list the delivery
-- NPC as a starter. IDs verified against QuestieDB Forever 1.1.5; no runtime
-- localized-name or numeric-range classification.
ns.craftsmanWritQuests = Set({
    94004,94212,94213,94214,94215,94216,94217,94218,94219,94220,94221,94222,
    94223,94224,94225,94226,94227,94228,94229,94230,94231,94232,94233,94234,
    94235,94236,94237,94238,94239,94240,94241,94242,94243,94244,94245,94246,
    94247,94248,94249,94250,94251,94252,94253,94254,94255,94256,94257,94258,
    94259,94260,94261,94262,94263,94264,94265,94266,94267,94268,94269,94270,
    94271,94272,94273,94274,94275,94276,94277,94278,94279,94280,94281,94282,
    94283,94284,94285,94286,94287,94288,94289,94290,94291,94292,94293,94294,
    94295,94296,94297,94298,94299,94300,94301,94302,94303,94304,94305,94306,
    94307,94308,94309,94310,94311,94312,94313,94314,94315,94316,94317,94318,
    94319,94320,94321,94322,94323,94324,94325,94326,94327,94328,94329,94330,
    94331,94332,94333,94334,94335,94336,94337,94338,94339,94340,94341,94342,
    94343,94344,94345,94346,94347,94348,94349,94350,94351,94352,94353,94354,
    94355,94356,94357,94358,94359,94360,
})
-- These dropped starters are distributed across a zone. Show their known
-- delivery destination instead of representative creature-drop coordinates.
-- Explicit IDs avoid reclassifying localized or single-source item starters.
ns.zoneDropDestinations = Set({351,485,635,2766}) -- OOX beacons; Pendant of Myzrael.
ns.pickupPolicy = {
    -- User and independent Forever reports contradict the legacy availability.
    -- Keep the listed level; require an actual offer instead of inventing a gate.
    offerOnly = Set({3504,3506,3507,91734,91735,91737,97540}),
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
