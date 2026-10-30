require("lib/ai")
require("lib/my")
local fx = require("core/fx")
LinkLuaModifier("modifier_anim", "abilities/other/generic.lua", LUA_MODIFIER_MOTION_NONE)
LinkLuaModifier("modifier_target_delay", "abilities/other/generic.lua", LUA_MODIFIER_MOTION_NONE)
boss_abyssal_underlord_certain_death = class({})

function boss_abyssal_underlord_certain_death:OnSpellStart()
	local caster = self:GetCaster()
	local heroes = ai_alive_heroes()
	local delay = self:GetSpecialValueFor("delay")
	local ticket_concession = caster:FindModifierByName("modifier_boss")
	local ticket = ticket_concession:RequestTicket()
	if #heroes ~= 0 then
		Timers:CreateTimer(function()
			if
				caster:IsChanneling()
				or caster:GetCurrentActiveAbility() ~= nil
				or caster:IsCommandRestricted()
				or not ticket_concession:QueryTicket(ticket)
			then
				return 0.1
			end
			StartAnimation(caster, { duration = delay, activity = ACT_DOTA_CAST_ABILITY_1, rate = 1 / delay })
			caster:AddNewModifier(caster, ability, "modifier_anim", { duration = delay })
			for _, hero in ipairs(heroes) do
				hero:AddNewModifier(caster, self, "modifier_target_delay", { duration = delay })
			end
			fx.once("particles/custom/aoe_warning.vpcf", PATTACH_WORLDORIGIN, caster, {
				[0] = caster:GetAbsOrigin(),
				[1] = Vector(800, 1, 1),
				[2] = Vector(delay, 1, 1),
				[3] = Vector(200, 10, 10),
			})
			Timers:CreateTimer(delay, function()
				EmitSoundOn("Hero_Bane.Nightmare", caster)
				for _, hero in ipairs(heroes) do
					local orb = CreateUnitByName(
						"npc_death_orb",
						caster:GetAbsOrigin(),
						false,
						caster,
						caster,
						caster:GetTeam()
					)
					orb:AddNewModifier(
						hero,
						self,
						"modifier_boss_abyssal_underlord_certain_death_behavior",
						{ duration = self:GetSpecialValueFor("duration") }
					)
					ticket_concession:ReleaseTicket()
				end
			end)
		end)
	end
end

LinkLuaModifier(
	"modifier_boss_abyssal_underlord_certain_death_behavior",
	"abilities/bosses/boss_abyssal_underlord_certain_death.lua",
	LUA_MODIFIER_MOTION_NONE
)
modifier_boss_abyssal_underlord_certain_death_behavior = class({})

function modifier_boss_abyssal_underlord_certain_death_behavior:CheckState()
	local state = {
		[MODIFIER_STATE_UNSELECTABLE] = true,
		[MODIFIER_STATE_ATTACK_IMMUNE] = true,
	}
	return state
end

function modifier_boss_abyssal_underlord_certain_death_behavior:IsHidden()
	return true
end

function modifier_boss_abyssal_underlord_certain_death_behavior:IsPurgable()
	return false
end

function modifier_boss_abyssal_underlord_certain_death_behavior:OnCreated()
	self.parent = self:GetParent()
	self.ability = self:GetAbility()
	self.target = self:GetCaster()
	EmitSoundOn("Hero_Bane.Nightmare.Loop", self.target)
	self.fx = fx.attach("particles/custom/certain_death_smoke.vpcf", PATTACH_POINT_FOLLOW, self.parent, {
		[3] = { ent = self.parent, attach = PATTACH_POINT_FOLLOW, point = "attach_hitloc" },
	})
	self.fx2 = fx.attach("particles/custom/bear_maul.vpcf", PATTACH_OVERHEAD_FOLLOW, self.parent, {
		[0] = { ent = self.parent, attach = PATTACH_POINT_FOLLOW, point = "attach_hitloc" },
		[1] = { ent = self.target, attach = PATTACH_POINT_FOLLOW, point = "attach_hitloc" },
		[2] = Vector(self:GetAbility():GetSpecialValueFor("duration"), 1, 0),
	})

	self:StartIntervalThink(0.25)
end

function modifier_boss_abyssal_underlord_certain_death_behavior:OnIntervalThink()
	self.parent:MoveToNPC(self.target)
end

function modifier_boss_abyssal_underlord_certain_death_behavior:IsAura()
	return true
end

function modifier_boss_abyssal_underlord_certain_death_behavior:GetAuraRadius()
	return self:GetAbility():GetSpecialValueFor("radius")
end

function modifier_boss_abyssal_underlord_certain_death_behavior:GetAuraSearchTeam()
	return DOTA_UNIT_TARGET_TEAM_ENEMY
end

function modifier_boss_abyssal_underlord_certain_death_behavior:GetAuraSearchType()
	return DOTA_UNIT_TARGET_HERO + DOTA_UNIT_TARGET_BASIC
end

function modifier_boss_abyssal_underlord_certain_death_behavior:GetModifierAura()
	return "modifier_boss_abyssal_underlord_certain_death_debuff"
end

function modifier_boss_abyssal_underlord_certain_death_behavior:OnDestroy()
	StopSoundOn("Hero_Bane.Nightmare.Loop", self.target)
	fx.stop(self.fx)
	fx.stop(self.fx2)
	self.parent:ForceKill(false)
end

LinkLuaModifier(
	"modifier_boss_abyssal_underlord_certain_death_debuff",
	"abilities/bosses/boss_abyssal_underlord_certain_death.lua",
	LUA_MODIFIER_MOTION_NONE
)
modifier_boss_abyssal_underlord_certain_death_debuff = class({})

function modifier_boss_abyssal_underlord_certain_death_debuff:IsHidden()
	return true
end

function modifier_boss_abyssal_underlord_certain_death_debuff:IsPurgable()
	return false
end

function modifier_boss_abyssal_underlord_certain_death_debuff:OnCreated()
	self.parent = self:GetParent()
	self.caster = self:GetCaster()
	self.ability = self:GetAbility()
	self.damage = self.ability:GetSpecialValueFor("damage")
	self.interval = self.ability:GetSpecialValueFor("interval")
	self:StartIntervalThink(self.interval)
end

function modifier_boss_abyssal_underlord_certain_death_debuff:OnIntervalThink()
	ApplyDamage({
		victim = self.parent,
		attacker = self.caster,
		damage = self.damage * self.interval,
		damage_type = self.ability:GetAbilityDamageType(),
		ability = self.ability, --Optional.
		damage_flags = DOTA_DAMAGE_FLAG_NONE, --Optional.
	})
end
