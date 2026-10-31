local safe_call = require("lib/safe_call")

if DashManager == nil then
	_G.DashManager = class({})
end

function DashManager:Init()
	CustomGameEventManager:RegisterListener("dash", safe_call.protect("dash", Dynamic_Wrap(DashManager, "Dash")))
end

-- keys.PlayerID is set by the engine; the payload's unit list is client-controlled.
local function DashableHero(unit, keys)
	local hero = EntIndexToHScript(unit)
	if not hero or hero:IsNull() then
		return nil
	end
	if hero:GetPlayerOwnerID() ~= keys.PlayerID then
		return nil
	end
	if hero:IsHero() and hero:HasModifier("modifier_builtin_blink") then
		return hero
	end
	return nil
end

function DashManager:Dash(keys)
	local temp_vector = Vector(keys.pos["0"], keys.pos["1"], keys.pos["2"])
	for _, unit in pairs(keys.units) do
		local hero = DashableHero(unit, keys)
		if hero then
			hero:FindModifierByName("modifier_builtin_blink"):Dash({ pos = temp_vector })
		end
	end
end
