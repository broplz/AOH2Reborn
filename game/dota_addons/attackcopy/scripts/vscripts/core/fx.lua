-- Particle helpers: every particle created here is released or destroyed (aoh-rules 7).
local M = {}

local function create(name, attach, owner)
	return ParticleManager:CreateParticle(name, attach, owner)
end

-- controls: cp -> Vector, or { ent = unit, attach = PATTACH_*, point = "attach_hitloc" }
local function apply(idx, controls)
	for cp, v in pairs(controls or {}) do
		if v.ent then
			ParticleManager:SetParticleControlEnt(idx, cp, v.ent, v.attach, v.point, v.ent:GetAbsOrigin(), true)
		else
			ParticleManager:SetParticleControl(idx, cp, v)
		end
	end
end

local function make(name, attach, owner, controls)
	local idx = create(name, attach, owner)
	apply(idx, controls)
	return idx
end

-- Fire-and-forget effect.
function M.once(name, attach, owner, controls)
	ParticleManager:ReleaseParticleIndex(make(name, attach, owner, controls))
end

-- Long-lived effect; the caller must call M.stop(index) later.
function M.attach(name, attach, owner, controls)
	return make(name, attach, owner, controls)
end

function M.stop(index, immediate)
	if not index then
		return
	end
	ParticleManager:DestroyParticle(index, immediate == true)
	ParticleManager:ReleaseParticleIndex(index)
end

-- Effect owned by a modifier: the engine destroys it with the modifier.
function M.bind(modifier, name, attach, owner, controls)
	local idx = make(name, attach, owner, controls)
	modifier:AddParticle(idx, false, false, -1, false, false)
	return idx
end

return M
