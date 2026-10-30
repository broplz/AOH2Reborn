require("lib/timers")
local fx = require("core/fx")

local exclude_items = {
	item_arcane_boots = true,
	item_custom_refresher = true,
	item_guardian_greaves = true,
	item_sheepstick = true,
	item_conduit = true,
	item_custom_fusion_rune = true,
	item_echo_wand = true,
	shadow_demon_disruption = true,
}

shadow_demon_dark_trance = class({})

function shadow_demon_dark_trance:OnSpellStart()
	local caster = self:GetCaster()
	caster:AddNewModifier(
		caster,
		self,
		"modifier_shadow_demon_dark_trance",
		{ duration = self:GetSpecialValueFor("duration") }
	)
end

LinkLuaModifier(
	"modifier_shadow_demon_dark_trance",
	"abilities/heroes/shadow_demon_dark_trance.lua",
	LUA_MODIFIER_MOTION_NONE
)
modifier_shadow_demon_dark_trance = class({})

function modifier_shadow_demon_dark_trance:IsHidden()
	return false
end

function modifier_shadow_demon_dark_trance:IsPurgable()
	return false
end

function modifier_shadow_demon_dark_trance:DeclareFunctions()
	return {
		MODIFIER_EVENT_ON_ABILITY_FULLY_CAST,
		MODIFIER_PROPERTY_CASTTIME_PERCENTAGE,
	}
end

function modifier_shadow_demon_dark_trance:GetModifierPercentageCasttime()
	return self:GetAbility():GetSpecialValueFor("casttime_reduce")
end

if IsServer() then
	function modifier_shadow_demon_dark_trance:OnCreated()
		self.parent = self:GetParent()
		self.cooldown = self:GetAbility():GetSpecialValueFor("cooldown")
		self.ability = self:GetAbility()
		if self:GetCaster():HasScepter() then
			self.cooldown = self.cooldown - self:GetAbility():GetSpecialValueFor("scepter_reduce")
		end
		self.particle = fx.attach(
			"particles/econ/items/arc_warden/arc_warden_ti9_immortal/arc_warden_ti9_wraith_distortion.vpcf",
			PATTACH_POINT,
			self.parent,
			{ [0] = { ent = self.parent, attach = PATTACH_POINT_FOLLOW, point = "attach_hitloc" } }
		)
	end

	function modifier_shadow_demon_dark_trance:OnAbilityFullyCast(keys)
		local used_ability = keys.ability
		local unit = keys.unit
		if
			unit == self.parent
			and used_ability:GetCooldown(0) > 0
			and keys.ability ~= self.ability
			and not exclude_items[used_ability:GetAbilityName()]
		then
			if used_ability:GetCooldownTimeRemaining() > 0 then
				used_ability:EndCooldown()
				used_ability:StartCooldown(self.cooldown)
			end
		end
	end

	function modifier_shadow_demon_dark_trance:OnDestroy()
		fx.stop(self.particle, false)
	end
end
