-- SPDX-License-Identifier: GPL-3.0-or-later
-- Adapted from Forever Loot Sparkles v1.3.1 by Ashtar Senior (svengabr).
-- Changes: shared settings, map options, slash-command shutdown.
-- Quest item sparkles need outlineModeShowLootEffectWhenDisabled on. Graphics
-- presets reset it, so it is applied at login and again after every relevant
-- cvar change. The outline mode is the player's: up to 1.3.0 it was forced
-- off, which took away the Self Highlight outline (CurseForge issue #1).

local ADDON_NAME, ns = ...;

local WANTED = {
	outlineModeShowLootEffectWhenDisabled = "1",
};

-- Written once when the option is switched off
local DISABLED = {
	outlineModeShowLootEffectWhenDisabled = "0",
};

local WATCHED = {
	graphicsquality = true,
	raidgraphicsquality = true,
};
for cvar in pairs(WANTED) do
	WATCHED[strlower(cvar)] = true;
end

local db;
-- Whether sparkles have been on at any point since the game started. Once on,
-- they stay visible until the next restart, even after the option is switched off.
local sparklesShown;
local applying = false;
local pendingAfterCombat = false;

local function IsEnabled()
	return db == nil or db.enabled ~= false;
end

local function SetAll(values)
	applying = true;
	for cvar, value in pairs(values) do
		local current = C_CVar.GetCVar(cvar);
		if current ~= nil and current ~= value then
			ns.TryAction("SetCVar " .. cvar, C_CVar.SetCVar, cvar, value);
		end
	end
	applying = false;
end

local function Apply()
	if not IsEnabled() then
		return;
	end
	if InCombatLockdown() then
		pendingAfterCombat = true;
		return;
	end
	SetAll(WANTED);
end

local applyAt;
local timerFrame = CreateFrame("Frame");
timerFrame:Hide();
timerFrame:SetScript("OnUpdate", function(self)
	if GetTime() >= applyAt then
		self:Hide();
		Apply();
	end
end);

local function ScheduleApply(delay)
	applyAt = GetTime() + delay;
	timerFrame:Show();
end

local function OnEnabledChanged(_, value)
	if value then
		ns.restoreLootAfterCombat = nil;
		sparklesShown = true;
		Apply();
	else
		pendingAfterCombat = false;
		timerFrame:Hide();
		if InCombatLockdown() then ns.restoreLootAfterCombat = true else SetAll(DISABLED) end;
		-- Switching off only takes effect after a full game restart (/reload is
		-- not enough). Told in chat: a shown predicate on a settings initializer
		-- runs addon code inside Blizzard's options search and taints it.
		if sparklesShown then
			print("|cffff8000QuestLite:|r restart the game to remove the sparkles. /reload is not enough.");
		end
	end
end

local function RegisterOptions()
	local category = Settings.RegisterVerticalLayoutCategory("QuestLite");
	ns.category = category;
	ns.RegisterMapOptions(category);

	local setting = Settings.RegisterAddOnSetting(category, "QUESTLITE_ENABLED", "enabled",
		db, Settings.VarType.Boolean, "Show quest item sparkles", Settings.Default.True);
	setting:SetValueChangedCallback(OnEnabledChanged);
	Settings.CreateCheckbox(category, setting,
		"Keeps the game's loot sparkle on, even after a graphics preset turns it off. Your outline mode is left as you set it. Switching this off takes effect after restarting the game.");

	ns.AddSoftTargetOptions(category, db);

	Settings.RegisterAddOnCategory(category);
end

local frame = CreateFrame("Frame");
frame:RegisterEvent("ADDON_LOADED");
frame:RegisterEvent("PLAYER_LOGIN");
frame:RegisterEvent("PLAYER_REGEN_ENABLED");
pcall(frame.RegisterEvent, frame, "CVAR_UPDATE");
frame:SetScript("OnEvent", function(self, event, arg1)
	if event == "ADDON_LOADED" then
		if arg1 == ADDON_NAME then
			self:UnregisterEvent("ADDON_LOADED");
			ns.LoadSettings();
			db = ns.db;
			RegisterOptions();
			sparklesShown = IsEnabled();
		end
	elseif event == "PLAYER_LOGIN" then
		Apply();
		ScheduleApply(5);
	elseif event == "PLAYER_REGEN_ENABLED" then
		if ns.restoreLootAfterCombat then
			ns.restoreLootAfterCombat = nil;
			SetAll(DISABLED);
		end
		if pendingAfterCombat then
			pendingAfterCombat = false;
			Apply();
		end
	elseif not applying and type(arg1) == "string" and WATCHED[strlower(arg1)] then
		ScheduleApply(1);
	end
end);

function ns.DisableLootSparkles()
    pendingAfterCombat = false;
    timerFrame:Hide();
    if InCombatLockdown() then
        ns.restoreLootAfterCombat = true;
    else
        SetAll(DISABLED);
    end
end
