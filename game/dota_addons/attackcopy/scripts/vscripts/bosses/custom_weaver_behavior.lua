require("lib/my")

custom_weaver_behavior = class({})

function custom_weaver_behavior:GetIntrinsicModifierName()
	if not self:GetCaster():IsIllusion() then
		return "modifier_custom_weaver_behavior"
	end
end

LinkLuaModifier("modifier_custom_weaver_behavior", "bosses/custom_weaver_behavior.lua", LUA_MODIFIER_MOTION_NONE)

modifier_custom_weaver_behavior = class({})

function modifier_custom_weaver_behavior:IsHidden()
	return true
end
function modifier_custom_weaver_behavior:IsPurgable()
	return false
end

-- StartIntervalThink(0) would cast flicker every frame
local FALLBACK_INTERVAL = 5.0

if IsServer() then
	function modifier_custom_weaver_behavior:OnCreated()
		self.parent = self:GetParent()
		self.ability = self:GetAbility()
		self.itemAbility = self.parent:AddItemByName("item_flicker_boss")
		self.interval = self.ability:GetSpecialValueFor("interval")
		if self.interval <= 0 then
			Warning(
				string.format(
					"custom_weaver_behavior: interval %.2f <= 0, using %.1f\n",
					self.interval,
					FALLBACK_INTERVAL
				)
			)
			self.interval = FALLBACK_INTERVAL
		end
		Timers:CreateTimer(0.01 * RandomInt(0, 100), function()
			self:StartIntervalThink(self.interval)
		end)
	end
end
function modifier_custom_weaver_behavior:OnIntervalThink()
	self.itemAbility:CastAbility()
end
