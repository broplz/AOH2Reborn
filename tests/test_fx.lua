local fx = require("core/fx")
local M = {}

-- Installs a recording ParticleManager in _G, runs fn(log), restores the previous value.
local function with_pm(fn)
	local log = {}
	local pm = {}
	for _, name in ipairs({
		"CreateParticle",
		"SetParticleControl",
		"SetParticleControlEnt",
		"DestroyParticle",
		"ReleaseParticleIndex",
	}) do
		pm[name] = function(_, ...)
			log[#log + 1] = { name, ... }
			return name == "CreateParticle" and 7 or nil
		end
	end
	local prev = rawget(_G, "ParticleManager")
	rawset(_G, "ParticleManager", pm)
	local ok, err = pcall(fn, log)
	rawset(_G, "ParticleManager", prev)
	assert(ok, err)
end

function M.test_once_releases()
	with_pm(function(log)
		T.eq(fx.once("p.vpcf", 1, nil), nil)
		T.eq(#log, 2)
		T.eq(log[1][1], "CreateParticle")
		T.eq(log[2][1], "ReleaseParticleIndex")
		T.eq(log[2][2], 7)
	end)
end

function M.test_once_applies_vector_and_ent_controls()
	with_pm(function(log)
		local u = T.stub.unit("x")
		function u:GetAbsOrigin()
			return "origin"
		end
		local v = Vector(1, 2, 3)
		fx.once("p.vpcf", 1, u, { [0] = v, [1] = { ent = u, attach = 5, point = "attach_hitloc" } })
		T.eq(#log, 4)
		local seen = {}
		for _, c in ipairs(log) do
			seen[c[1]] = c
		end
		T.eq(seen.SetParticleControl[3], 0)
		T.eq(seen.SetParticleControl[4], v)
		T.eq(seen.SetParticleControlEnt[3], 1)
		T.eq(seen.SetParticleControlEnt[4], u)
		T.eq(seen.SetParticleControlEnt[6], "attach_hitloc")
		T.eq(seen.SetParticleControlEnt[7], "origin")
		T.eq(log[4][1], "ReleaseParticleIndex")
	end)
end

function M.test_attach_returns_index_without_release()
	with_pm(function(log)
		T.eq(fx.attach("p.vpcf", 1, nil), 7)
		T.eq(#log, 1)
		T.eq(log[1][1], "CreateParticle")
	end)
end

function M.test_stop_destroys_then_releases()
	with_pm(function(log)
		fx.stop(7, true)
		fx.stop(8)
		T.eq(#log, 4)
		T.eq(log[1][1], "DestroyParticle")
		T.eq(log[1][3], true)
		T.eq(log[2][1], "ReleaseParticleIndex")
		T.eq(log[3][3], false)
	end)
end

function M.test_stop_nil_is_noop()
	with_pm(function(log)
		fx.stop(nil)
		T.eq(#log, 0)
	end)
end

function M.test_bind_registers_with_modifier()
	with_pm(function(log)
		local args
		local mod = {
			AddParticle = function(_, ...)
				args = { ... }
			end,
		}
		T.eq(fx.bind(mod, "p.vpcf", 1, nil), 7)
		T.eq(#log, 1)
		T.eq(args[1], 7)
		T.eq(args[4], -1)
	end)
end

return M
