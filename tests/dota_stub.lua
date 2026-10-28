-- Minimal Dota 2 VScript API stub so pure-logic modules can be unit-tested outside the game.
-- Extend it in the task that needs more (allowed_paths: tests/**). Keep it honest: a stub
-- method does the simplest thing the real engine would do; it never "passes" by default.
local stub = {}

local _time = 0
function stub.setTime(t)
	_time = t
end
function stub.advance(dt)
	_time = _time + dt
end

-- class(): Dota's class helper (vlua) — tables with __index inheritance.
function class(base)
	local c = {}
	c.__index = c
	if base then
		setmetatable(c, { __index = base })
	end
	return c
end

function IsServer()
	return true
end
function IsClient()
	return false
end
function IsInToolsMode()
	return false
end
function Vector(x, y, z)
	return { x = x or 0, y = y or 0, z = z or 0 }
end
function RandomInt(lo, hi)
	return lo
end
function RandomFloat(lo, hi)
	return lo
end
function print(...) end -- keep test output clean; tests assert, they do not print
function Dynamic_Wrap(t, name)
	return t[name]
end
function LinkLuaModifier() end
function Msg(s) end
function Warning(s) end

GameRules = {
	GetGameTime = function()
		return _time
	end,
	GetDOTATime = function(_, _, _)
		return _time
	end,
}

-- A fake unit with just enough surface for modifier logic: modifiers by name, state flags.
local Unit = {}
Unit.__index = Unit
function stub.unit(name)
	local u = setmetatable(
		{ name = name or "npc", _mods = {}, _flags = {}, _alive = true, _health = 1000, _max = 1000 },
		Unit
	)
	return u
end
function Unit:GetUnitName()
	return self.name
end
function Unit:IsNull()
	return self._removed == true
end
function Unit:IsAlive()
	return self._alive
end
function Unit:GetHealth()
	return self._health
end
function Unit:GetMaxHealth()
	return self._max
end
function Unit:SetHealth(h)
	self._health = h
end
function Unit:IsChanneling()
	return self._flags.channeling == true
end
function Unit:IsStunned()
	return self._flags.stunned == true
end
function Unit:IsHexed()
	return self._flags.hexed == true
end
function Unit:IsCommandRestricted()
	return self._flags.restricted == true
end
function Unit:GetCurrentActiveAbility()
	return self._flags.active_ability
end
function Unit:HasModifier(n)
	return self._mods[n] ~= nil
end
function Unit:FindModifierByName(n)
	return self._mods[n]
end
function Unit:AddNewModifier(caster, ability, n, kv)
	local m = { name = n, parent = self, kv = kv }
	self._mods[n] = m
	return m
end
function Unit:RemoveModifierByName(n)
	self._mods[n] = nil
end
function Unit:set(flag, v)
	self._flags[flag] = v
end

-- Attach a modifier class instance to a unit the way the engine would (OnCreated etc. are
-- the module's business; tests call them explicitly).
function stub.attach(unit, modclass, kv)
	local m = setmetatable({ _parent = unit, _kv = kv or {}, _think = nil }, modclass)
	m.GetParent = function()
		return unit
	end
	m.StartIntervalThink = function(self, dt)
		self._think = dt
	end
	m.OnIntervalThink = modclass.OnIntervalThink
	return m
end

stub.Timers = { timers = {} }
Timers = {
	CreateTimer = function(_, a, b)
		local spec = type(a) == "table" and a or b
		table.insert(stub.Timers.timers, spec)
		return #stub.Timers.timers
	end,
	RemoveTimer = function(_, id)
		stub.Timers.timers[id] = nil
	end,
}

return stub
