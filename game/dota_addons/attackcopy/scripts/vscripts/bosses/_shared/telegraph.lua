--- Boss telegraph base (ADR-0002 §5): the cast-queue replacement for generic_aoe_notarget,
-- generic_aoe and generic_target in abilities/other/generic.lua.
--
--   local telegraph = require("bosses/_shared/telegraph")
--   boss_x_wrapper = telegraph.class({ kind = "point", spell = "boss_x_fissure" })
--
-- The returned ability_lua class submits one boss_queue job to the caster's modifier_boss from
-- OnSpellStart. Numbers come from the wrapper's own KV: delay, radius, iterations (0 → 1),
-- is_line, line_length, initial_radius (0 → radius), maximum_distance (0 → 475).
-- Target spells are mostly vanilla BaseClass and cannot call modifier_boss:Confirm() themselves,
-- so the hidden modifier_telegraph_confirm watches the spell's cooldown and confirms for them.
require("abilities/other/generic") -- owns modifier_anim, modifier_weak, modifier_dummy, modifier_target_delay
require("lib/warning")
require("lib/animations")
-- luacheck: read globals aoe_particle aoe_line_particle line_to_point StartAnimation
-- The engine needs the modifier class as a global (ADR-0002 rule 1).
-- luacheck: globals modifier_telegraph_confirm

local M = {}

local CONFIRM = "modifier_telegraph_confirm"
local CONFIRM_THINK = 0.1
local SOUND = "Hero_Mars.Spear.Cast"
local SIGNIFIER = "particles/custom/boss_block.vpcf"
local TARGET_WARNING = "particles/custom/aoe_warning_target.vpcf"
local LINE_WARNING = "particles/custom/line_aoe_warning.vpcf"
local LINE_WARNING_LINGER = 1.05
local HARD_DIFFICULTY = 2
local QUEUE_DEADLINE = 6
local CAST_TIMEOUT_PAD = 1.0
local WEAK_DURATION = 0.5
local DUMMY_LINGER = 1
local DEFAULT_RANGE = 1000
local DEFAULT_MAX_DISTANCE = 475
local FOW_RADIUS = 100
local FOW_DURATION = 2
local NORMAL = { delay = 1, extra_iterations = 0 }

LinkLuaModifier(CONFIRM, "bosses/_shared/telegraph.lua", LUA_MODIFIER_MOTION_NONE)

local function nonzero(v, fallback)
	if v == 0 then
		return fallback
	end
	return v
end

-- GetSpecialValueFor returns 0 for both 0 and an absent key.
local function value(ability, name, fallback)
	return nonzero(ability:GetSpecialValueFor(name), fallback)
end

local function valid(unit)
	return unit ~= nil and not unit:IsNull() and unit:IsAlive()
end

-- Iteration 2+ of a point telegraph: a random enemy within the spell's cast range (generic_aoe).
local function retarget(job)
	local caster = job.caster
	local range = nonzero(job.spell:GetCastRange(job.cursor, caster), DEFAULT_RANGE)
	local enemies = FindUnitsInRadius(
		caster:GetTeamNumber(),
		caster:GetAbsOrigin(),
		nil,
		range,
		DOTA_UNIT_TARGET_TEAM_ENEMY,
		DOTA_UNIT_TARGET_HERO + DOTA_UNIT_TARGET_BASIC,
		DOTA_UNIT_TARGET_FLAG_NONE,
		FIND_FARTHEST,
		false
	)
	if #enemies == 0 then
		return job.cursor
	end
	return enemies[RandomInt(1, #enemies)]:GetAbsOrigin()
end

local function line_end(job, origin, point)
	if job.line_length then
		return origin + (point - origin):Normalized() * job.line_length
	end
	return point
end

local function warn_point(job, point)
	local caster = job.caster
	local origin = caster:GetAbsOrigin()
	if job.is_line == 1 then
		aoe_line_particle(caster, job.delay, origin, line_end(job, origin, point), job.initial_radius, job.radius)
		return
	end
	aoe_particle(caster, job.delay, point, job.radius)
	line_to_point(caster, job.delay, origin, point)
end

local function warn_target(job, point)
	local caster, target = job.caster, job.target
	local fx = ParticleManager:CreateParticle(TARGET_WARNING, PATTACH_WORLDORIGIN, target)
	ParticleManager:SetParticleControl(fx, 0, point)
	ParticleManager:SetParticleControl(fx, 1, Vector(job.maximum_distance, job.delay, 1))
	ParticleManager:ReleaseParticleIndex(fx)
	target:AddNewModifier(caster, job.ability, "modifier_target_delay", { duration = job.delay })
	if job.is_line == 1 then
		local origin = caster:GetAbsOrigin()
		local line = ParticleManager:CreateParticle(LINE_WARNING, PATTACH_ABSORIGIN_FOLLOW, caster)
		ParticleManager:SetParticleControl(line, 0, origin)
		ParticleManager:SetParticleControl(line, 1, origin)
		ParticleManager:SetParticleControlEnt(
			line,
			2,
			target,
			PATTACH_ABSORIGIN_FOLLOW,
			"attach_hitloc",
			target:GetAbsOrigin(),
			true
		)
		ParticleManager:SetParticleControl(line, 3, Vector(job.radius, job.initial_radius, 1))
		ParticleManager:SetParticleControl(line, 4, Vector(job.delay * LINE_WARNING_LINGER, 1, 1))
		ParticleManager:ReleaseParticleIndex(line)
	end
end

-- The target moved more than maximum_distance since the telegraph: cast on an npc_target dummy
-- maximum_distance away from it, towards the telegraphed point (generic_target).
local function pick_cast_target(job)
	local target = job.target
	local now = target:GetAbsOrigin()
	job.cast_target, job.dummy, job.dummy_mod = target, nil, nil
	if (job.point - now):Length2D() <= job.maximum_distance then
		return
	end
	local spot = now + (job.point - now):Normalized() * job.maximum_distance
	local dummy = CreateUnitByName("npc_target", spot, false, target, target, target:GetTeamNumber())
	AddFOWViewer(job.caster:GetTeamNumber(), spot, FOW_RADIUS, FOW_DURATION, false)
	job.dummy = dummy
	job.dummy_mod = dummy:AddNewModifier(job.caster, job.ability, "modifier_dummy", { duration = -1 })
	job.cast_target = dummy
end

local function aim_caster(job)
	return job.caster:GetAbsOrigin()
end

-- Iteration 1 at the cursor, later iterations at an enemy in range.
local function aim_point(job)
	if job.step == 1 then
		return job.cursor
	end
	return retarget(job)
end

local function aim_target(job)
	return job.target:GetAbsOrigin()
end

local function warn_caster(job, point)
	aoe_particle(job.caster, job.delay, point, job.radius)
end

local function order_no_target(job)
	job.caster:CastAbilityNoTarget(job.spell, -1)
end

local function order_point(job)
	job.caster:CastAbilityOnPosition(job.point, job.spell, job.caster:GetPlayerOwnerID())
end

local function order_target(job)
	job.caster:CastAbilityOnTarget(job.cast_target, job.spell, -1)
end

-- Per kind: hard-difficulty scaling, aim point, warning, optional pre-cast step, cast order.
local KINDS = {
	["no_target"] = { hard = NORMAL, aim = aim_caster, warn = warn_caster, order = order_no_target },
	["point"] = {
		hard = { delay = 0.8, extra_iterations = 1 },
		faces = true,
		aim = aim_point,
		warn = warn_point,
		order = order_point,
	},
	["unit_target"] = {
		hard = { delay = 0.8, extra_iterations = 0 },
		faces = true,
		needs_target = true,
		aim = aim_target,
		warn = warn_target,
		prepare = pick_cast_target,
		order = order_target,
	},
}

local function target_lost(job, kind)
	return kind.needs_target and not valid(job.target)
end

local function issue(job, kind)
	if kind.faces then
		job.caster:FaceTowards(job.point)
	end
	kind.order(job)
end

local function telegraph(job)
	local kind = KINDS[job.kind]
	job.step = job.step + 1
	if target_lost(job, kind) then
		return 0
	end
	local caster = job.caster
	local wind_up = job.delay - job.spell:GetCastPoint()
	job.point = kind.aim(job)
	kind.warn(job, job.point)
	caster:Stop()
	caster:FaceTowards(job.point)
	EmitSoundOn(SOUND, caster)
	caster:AddNewModifier(caster, job.ability, "modifier_anim", { duration = wind_up })
	StartAnimation(caster, { duration = wind_up, activity = ACT_DOTA_CAST_ABILITY_1, rate = 1 / wind_up })
	return wind_up
end

local function cast(job)
	local kind = KINDS[job.kind]
	if target_lost(job, kind) then
		return false
	end
	local caster = job.caster
	job.spell:EndCooldown()
	if kind.prepare then
		kind.prepare(job)
	end
	issue(job, kind)
	local confirm = caster:AddNewModifier(caster, job.ability, CONFIRM, { duration = job.cast_timeout })
	if confirm then
		confirm.job = job
	end
	return true
end

local function on_cancel(job)
	local caster = job.caster
	if caster and not caster:IsNull() then
		caster:RemoveModifierByName("modifier_anim")
		caster:RemoveModifierByName(CONFIRM)
	end
	if job.dummy and not job.dummy:IsNull() then
		job.dummy:ForceKill(false)
	end
end

local function difficulty_scale(kind)
	if _G.AOHGameMode and _G.AOHGameMode._difficulty == HARD_DIFFICULTY then
		return KINDS[kind].hard
	end
	return NORMAL
end

local function build_job(ability, spec, caster, spell)
	local scale = difficulty_scale(spec.kind)
	local radius = ability:GetSpecialValueFor("radius")
	return {
		name = ability:GetAbilityName(),
		kind = spec.kind,
		caster = caster,
		ability = ability,
		spell = spell,
		cursor = ability:GetCursorPosition(),
		target = ability:GetCursorTarget(),
		delay = ability:GetSpecialValueFor("delay") * scale.delay,
		radius = radius,
		initial_radius = value(ability, "initial_radius", radius),
		is_line = ability:GetSpecialValueFor("is_line"),
		line_length = value(ability, "line_length", nil),
		maximum_distance = value(ability, "maximum_distance", DEFAULT_MAX_DISTANCE),
		iterations = value(ability, "iterations", 1) + scale.extra_iterations,
		step = 0,
		prio = 0,
		deadline = QUEUE_DEADLINE,
		cast_timeout = spell:GetCastPoint() + CAST_TIMEOUT_PAD,
		telegraph = telegraph,
		cast = cast,
		on_cancel = on_cancel,
	}
end

--- spec = { kind = "no_target"|"point"|"unit_target", spell = "<target ability name>" }
function M.class(spec)
	assert(KINDS[spec.kind], "telegraph.class: unknown kind " .. tostring(spec.kind))
	local cls = class({})
	function cls:OnSpellStart()
		if not IsServer() then
			return
		end
		local caster = self:GetCaster()
		local boss = caster:FindModifierByName("modifier_boss")
		local spell = caster:FindAbilityByName(spec.spell)
		if not boss or not spell then
			return
		end
		local fx = ParticleManager:CreateParticle(SIGNIFIER, PATTACH_ABSORIGIN_FOLLOW, caster)
		ParticleManager:ReleaseParticleIndex(fx)
		boss:Submit(build_job(self, spec, caster, spell))
	end
	return cls
end

-- Hidden watcher on the caster for one cast: confirms the queue job once the target spell went
-- on cooldown, re-issues the order while the caster idles (replaces generic.lua's retry timers).
modifier_telegraph_confirm = class({})

function modifier_telegraph_confirm:IsHidden()
	return true
end

function modifier_telegraph_confirm:IsPurgable()
	return false
end

function modifier_telegraph_confirm:OnCreated()
	if not IsServer() then
		return
	end
	self:StartIntervalThink(CONFIRM_THINK)
end

function modifier_telegraph_confirm:OnIntervalThink()
	local job = self.job
	if not job or job.spell:IsNull() then
		return
	end
	local caster = self:GetParent()
	if job.spell:IsCooldownReady() then
		self:reissue(job, caster)
		return
	end
	local boss = caster:FindModifierByName("modifier_boss")
	if boss then
		boss:Confirm()
	end
	if job.iterations == 1 then
		caster:AddNewModifier(caster, job.ability, "modifier_weak", { duration = WEAK_DURATION })
	end
	self:Destroy()
end

-- The spell is still ready: re-issue while the caster idles; a lost unit target ends the watch.
function modifier_telegraph_confirm:reissue(job, caster)
	local kind = KINDS[job.kind]
	if kind.needs_target and not valid(job.cast_target) then
		self:Destroy()
		return
	end
	if caster:GetCurrentActiveAbility() == nil and not caster:IsSilenced() then
		issue(job, kind)
	end
end

-- Confirmed or timed out, this cast's dummy stops being immortal (the queue moves on without
-- on_cancel after cast_timeout, and later iterations overwrite job.dummy_mod).
function modifier_telegraph_confirm:OnDestroy()
	if not IsServer() then
		return
	end
	self:StartIntervalThink(-1)
	local dummy_mod = self.job and self.job.dummy_mod
	if dummy_mod and not dummy_mod:IsNull() then
		dummy_mod:SetDuration(DUMMY_LINGER, true)
	end
end

return M
