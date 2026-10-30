local fx = require("core/fx")

local STAT_CHANGE = {
	item_custom_stat_change_str = {
		particle = "particles/econ/events/ti6/hero_levelup_ti6_flash_hit_magic.vpcf",
		attribute = 0,
	},
	item_custom_stat_change_agi = {
		particle = "particles/econ/events/ti8/hero_levelup_ti8_flash_hit_magic.vpcf",
		attribute = 1,
	},
	item_custom_stat_change_int = {
		particle = "particles/econ/events/ti7/hero_levelup_ti7_flash_hit_magic.vpcf",
		attribute = 2,
	},
}

item_custom_stat_change = class({})

function item_custom_stat_change:OnSpellStart()
	local caster = self:GetCaster()
	if caster:HasModifier("modifier_item_stat_change") then
		caster:RemoveModifierByName("modifier_item_stat_change")
	end
	local choice = STAT_CHANGE[self:GetAbilityName()]
	local temp = choice and choice.attribute or 0
	if choice then
		fx.once(choice.particle, PATTACH_ABSORIGIN_FOLLOW, caster, {
			[0] = { ent = caster, attach = PATTACH_POINT_FOLLOW, point = "attach_hitloc" },
		})
	end
	self.modifier = caster:AddNewModifier(caster, self, "modifier_item_stat_change", {
		attribute = temp,
	})
end

item_custom_stat_change_str = class(item_custom_stat_change)
item_custom_stat_change_agi = class(item_custom_stat_change)
item_custom_stat_change_int = class(item_custom_stat_change)

LinkLuaModifier("modifier_item_stat_change", "items/custom_stat_change.lua", LUA_MODIFIER_MOTION_NONE)
modifier_item_stat_change = class({})

function modifier_item_stat_change:IsHidden()
	return true
end

function modifier_item_stat_change:IsPurgable()
	return false
end

function modifier_item_stat_change:RemoveOnDeath()
	return false
end

if IsServer() then
	function modifier_item_stat_change:OnCreated(keys)
		self.parent = self:GetParent()
		self.attribute = keys.attribute
		self.parent:SetPrimaryAttribute(self.attribute)
		self:StartIntervalThink(3)
	end
	function modifier_item_stat_change:OnIntervalThink()
		self.parent:SetPrimaryAttribute(self.attribute)
	end
end
