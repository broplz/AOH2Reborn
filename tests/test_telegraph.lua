-- bosses/_shared/telegraph.lua on the stub. tests/dota_stub.lua is frozen for feature tasks
-- (guard hook), so the engine surface telegraph needs is defined here.
-- luacheck: globals aoe_particle aoe_line_particle line_to_point StartAnimation
-- luacheck: read globals modifier_telegraph_confirm
local M = {}

local CONFIRM = "modifier_telegraph_confirm"
local S = {} -- per-test recorders, reset by setup()

local function noop() end

-- Vectors with engine arithmetic (the stub's Vector is a plain table).
local V = {}
V.__index = V
local function vec(x, y)
	return setmetatable({ x = x, y = y, z = 0 }, V)
end
V.__add = function(a, b)
	return vec(a.x + b.x, a.y + b.y)
end
V.__sub = function(a, b)
	return vec(a.x - b.x, a.y - b.y)
end
V.__mul = function(a, k)
	return vec(a.x * k, a.y * k)
end
V.__eq = function(a, b)
	return a.x == b.x and a.y == b.y
end
function V:Length2D()
	return math.sqrt(self.x * self.x + self.y * self.y)
end
function V:Normalized()
	local len = self:Length2D()
	return vec(self.x / len, self.y / len)
end

local Unit = getmetatable(T.stub.unit())

local function unit(name, pos)
	local u = T.stub.unit(name)
	u.origin, u.orders, u.abilities = pos or vec(0, 0), {}, {}
	u.GetAbsOrigin = function(self)
		return self.origin
	end
	u.GetTeamNumber = function()
		return 2
	end
	u.GetPlayerOwnerID = function()
		return 0
	end
	u.Stop, u.FaceTowards = noop, noop
	u.IsSilenced = function(self)
		return self._flags.silenced == true
	end
	u.FindAbilityByName = function(self, n)
		return self.abilities[n]
	end
	u.CastAbilityNoTarget = function(self, spell, pid)
		table.insert(self.orders, { kind = "no_target", spell = spell, pid = pid })
	end
	u.CastAbilityOnPosition = function(self, point, spell, pid)
		table.insert(self.orders, { kind = "point", spell = spell, pid = pid, point = point })
	end
	u.CastAbilityOnTarget = function(self, target, spell, pid)
		table.insert(self.orders, { kind = "unit_target", spell = spell, pid = pid, target = target })
	end
	u.ForceKill = function(self)
		self._alive = false
	end
	u.AddNewModifier = function(self, caster, ability, n, kv)
		if n == CONFIRM then
			local m = T.stub.attach(self, modifier_telegraph_confirm, kv)
			m.Destroy = function(mod)
				mod:OnDestroy()
				self._mods[n] = nil
			end
			self._mods[n] = m
			m:OnCreated(kv)
			return m
		end
		local m = Unit.AddNewModifier(self, caster, ability, n, kv)
		m.IsNull = function()
			return false
		end
		m.SetDuration = function(mod, d)
			mod.duration = d
		end
		return m
	end
	return u
end

local engine = {
	LUA_MODIFIER_MOTION_NONE = 0,
	PATTACH_ABSORIGIN_FOLLOW = 1,
	PATTACH_WORLDORIGIN = 7,
	ACT_DOTA_CAST_ABILITY_1 = 1503,
	DOTA_UNIT_TARGET_TEAM_ENEMY = 2,
	DOTA_UNIT_TARGET_HERO = 1,
	DOTA_UNIT_TARGET_BASIC = 18,
	DOTA_UNIT_TARGET_FLAG_NONE = 0,
	FIND_FARTHEST = 2,
	ParticleManager = {
		CreateParticle = function()
			return 1
		end,
		SetParticleControl = noop,
		SetParticleControlEnt = noop,
		ReleaseParticleIndex = noop,
		DestroyParticle = noop,
	},
	EmitSoundOn = noop,
	AddFOWViewer = noop,
	FindUnitsInRadius = function()
		return S.found
	end,
	CreateUnitByName = function(name, pos)
		local u = unit(name, pos)
		table.insert(S.created, u)
		return u
	end,
}
for k, v in pairs(engine) do
	rawset(_G, k, v)
end

local function recorder(name)
	return function(...)
		table.insert(S.warnings, { name, ... })
	end
end
aoe_particle = recorder("aoe_particle")
aoe_line_particle = recorder("aoe_line_particle")
line_to_point = recorder("line_to_point")
StartAnimation = function(_, t)
	table.insert(S.animations, t)
end

package.loaded["abilities/other/generic"] = true
package.loaded["lib/warning"] = true
package.loaded["lib/animations"] = true
local telegraph = require("bosses/_shared/telegraph")

local A = {
	GetAbilityName = function(self)
		return self.name
	end,
	GetSpecialValueFor = function(self, k)
		return self.values[k] or 0
	end,
	GetCastPoint = function(self)
		return self.cast_point
	end,
	IsCooldownReady = function(self)
		return self.ready
	end,
	EndCooldown = function(self)
		self.ready = true
	end,
	IsNull = function()
		return false
	end,
	GetCastRange = function()
		return 0
	end,
	GetCaster = function(self)
		return self.caster
	end,
	GetCursorPosition = function(self)
		return self.cursor
	end,
	GetCursorTarget = function(self)
		return self.target
	end,
}

local function ability(name, values, cls)
	local a = { name = name, values = values, cast_point = 0.3, ready = true }
	return setmetatable(a, {
		__index = function(_, k)
			return (cls and cls[k]) or A[k]
		end,
	})
end

local function setup(kind, values, difficulty)
	S.found, S.created, S.warnings, S.animations = {}, {}, {}, {}
	rawset(_G, "AOHGameMode", { _difficulty = difficulty or 1 })
	local caster = unit("boss", vec(0, 0))
	local spell = ability("boss_spell", {})
	caster.abilities.boss_spell = spell
	local env = { caster = caster, spell = spell, jobs = {}, confirms = 0 }
	caster._mods.modifier_boss = {
		Submit = function(_, job)
			table.insert(env.jobs, job)
			return #env.jobs
		end,
		Confirm = function()
			env.confirms = env.confirms + 1
		end,
	}
	env.wrapper = ability("boss_wrapper", values, telegraph.class({ kind = kind, spell = "boss_spell" }))
	env.wrapper.caster = caster
	return env
end

local function start(env)
	env.wrapper:OnSpellStart()
	T.eq(#env.jobs, 1, "one Submit")
	return env.jobs[1]
end

function M.test_no_target()
	local env = setup("no_target", { delay = 2, radius = 300 })
	local job = start(env)
	T.eq(job.iterations, 1, "iterations absent → 1")
	T.eq(job.prio, 0)
	T.eq(job.deadline, 6)
	T.eq(job.cast_timeout, 0.3 + 1.0)
	T.eq(job.telegraph(job), 2 - 0.3, "delay - cast point")
	T.eq(env.caster._mods.modifier_anim.kv.duration, 2 - 0.3)
	T.eq(S.animations[1].rate, 1 / (2 - 0.3), "animation rate without the precedence bug")
	T.eq(S.warnings[1][1], "aoe_particle")
	T.truthy(job.cast(job), "cast ok")
	T.eq(#env.caster.orders, 1)
	T.eq(env.caster.orders[1].kind, "no_target")
	T.eq(env.caster.orders[1].spell, env.spell)
	T.eq(env.caster.orders[1].pid, -1)
end

function M.test_point_line_hard()
	local env = setup("point", { delay = 2, radius = 200, is_line = 1, line_length = 800, iterations = 2 }, 2)
	env.wrapper.cursor = vec(500, 0)
	local job = start(env)
	T.eq(job.iterations, 3, "hard: iterations + 1")
	T.eq(job.telegraph(job), 2 * 0.8 - 0.3, "hard: delay x0.8")
	T.eq(S.warnings[1][1], "aoe_line_particle")
	T.eq(S.warnings[1][5], vec(800, 0), "line end at line_length")
	T.eq(S.warnings[1][6], 200, "initial_radius absent → radius")
	T.truthy(job.cast(job))
	local order = env.caster.orders[1]
	T.eq(order.kind, "point")
	T.eq(order.point, vec(500, 0), "first iteration at the cursor")
	T.eq(order.pid, 0, "point orders use the owner's player id")
end

function M.test_point_retargets_after_first_iteration()
	local env = setup("point", { delay = 2, radius = 200 })
	env.wrapper.cursor = vec(500, 0)
	local job = start(env)
	job.telegraph(job)
	S.found = { unit("hero", vec(100, 100)) }
	job.telegraph(job)
	T.eq(job.point, vec(100, 100), "iteration 2 aims at an enemy in range")
	S.found = {}
	job.telegraph(job)
	T.eq(job.point, vec(500, 0), "no enemy → cursor")
end

function M.test_unit_target_hard()
	local env = setup("unit_target", { delay = 2, radius = 100, iterations = 2 }, 2)
	local target = unit("hero", vec(300, 0))
	env.wrapper.target = target
	local job = start(env)
	T.eq(job.iterations, 2, "hard: iterations unchanged")
	T.eq(job.maximum_distance, 475, "maximum_distance absent → 475")
	T.eq(job.telegraph(job), 2 * 0.8 - 0.3, "hard: delay x0.8")
	T.truthy(target:HasModifier("modifier_target_delay"))
	T.truthy(job.cast(job))
	local order = env.caster.orders[1]
	T.eq(order.kind, "unit_target")
	T.eq(order.target, target)
	T.eq(order.pid, -1)
	T.eq(#S.created, 0, "no dummy when the target stayed")
end

function M.test_unit_target_lost()
	local env = setup("unit_target", { delay = 2 })
	local target = unit("hero", vec(300, 0))
	env.wrapper.target = target
	local job = start(env)
	job.telegraph(job)
	target._alive = false
	T.falsy(job.cast(job), "dead target → cast gives up")
	T.eq(#env.caster.orders, 0)
end

function M.test_confirm_once_then_destroyed()
	local env = setup("no_target", { delay = 2 })
	local job = start(env)
	job.telegraph(job)
	job.cast(job)
	local confirm = env.caster._mods[CONFIRM]
	T.truthy(confirm, "confirm modifier added")
	T.eq(confirm._think, 0.1)
	T.eq(confirm._kv.duration, job.cast_timeout)
	confirm:OnIntervalThink()
	T.eq(env.confirms, 0, "spell still ready: no confirm")
	T.eq(#env.caster.orders, 2, "idle caster: order reissued")
	env.spell.ready = false
	confirm:OnIntervalThink()
	T.eq(env.confirms, 1, "Confirm exactly once")
	T.falsy(env.caster:HasModifier(CONFIRM), "destroyed")
	T.eq(confirm._think, -1, "think stopped")
	T.truthy(env.caster:HasModifier("modifier_weak"), "weak after the last iteration")
end

function M.test_cancel_cleans_up()
	local env = setup("unit_target", { delay = 2 })
	local target = unit("hero", vec(300, 0))
	env.wrapper.target = target
	local job = start(env)
	job.telegraph(job)
	T.truthy(env.caster:HasModifier("modifier_anim"))
	target.origin = vec(1000, 0)
	job.cast(job)
	T.eq(#S.created, 1, "target moved past maximum_distance → dummy")
	local dummy = S.created[1]
	T.eq(dummy:GetUnitName(), "npc_target")
	T.eq(env.caster.orders[1].target, dummy, "cast on the dummy")
	T.truthy(dummy:HasModifier("modifier_dummy"))
	job.on_cancel(job)
	T.falsy(env.caster:HasModifier("modifier_anim"), "modifier_anim removed")
	T.falsy(dummy:IsAlive(), "dummy killed")
end

-- A unit_target cast whose target walked away: the cast goes to an npc_target dummy.
local function cast_on_dummy()
	local env = setup("unit_target", { delay = 2 })
	local target = unit("hero", vec(300, 0))
	env.wrapper.target = target
	local job = start(env)
	job.telegraph(job)
	target.origin = vec(1000, 0)
	job.cast(job)
	return env, job, S.created[1]
end

function M.test_unconfirmed_dummy_lingers()
	local env, _, dummy = cast_on_dummy()
	env.caster._flags.silenced = true
	local confirm = env.caster._mods[CONFIRM]
	confirm:OnIntervalThink()
	T.eq(#env.caster.orders, 1, "silenced: no reissue")
	confirm:Destroy() -- cast_timeout ran out without a confirm
	T.eq(env.confirms, 0, "never confirmed")
	T.eq(dummy:FindModifierByName("modifier_dummy").duration, 1, "dummy no longer immortal")
end

function M.test_lost_cast_target_stops_reissue()
	local env, _, dummy = cast_on_dummy()
	dummy._alive = false
	local confirm = env.caster._mods[CONFIRM]
	confirm:OnIntervalThink()
	T.eq(#env.caster.orders, 1, "dead cast target: no reissue")
	T.falsy(env.caster:HasModifier(CONFIRM), "watch ends")
	T.eq(env.confirms, 0)
end

function M.test_no_boss_does_nothing()
	local env = setup("point", { delay = 2 })
	env.caster._mods.modifier_boss = nil
	env.wrapper:OnSpellStart()
	T.eq(#env.jobs, 0)
end

return M
