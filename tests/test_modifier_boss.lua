-- modifier_boss is the global class defined by the require below.
-- luacheck: read globals modifier_boss
require("modifiers/modifier_boss")
local M = {}

-- tests/dota_stub.lua is frozen for feature tasks (guard hook), so the stack-count surface the
-- engine gives every modifier is added here, on the instance.
local function boss()
	local u = T.stub.unit("boss")
	local m = T.stub.attach(u, modifier_boss)
	m._stacks = 0
	m.GetStackCount = function(self)
		return self._stacks
	end
	m.IncrementStackCount = function(self)
		self._stacks = self._stacks + 1
	end
	T.stub.setTime(0)
	m:OnCreated()
	return m, u
end

local function think(m, dt)
	T.stub.advance(dt)
	m:OnIntervalThink()
end

local function job(log)
	return {
		name = "test_job",
		telegraph = function()
			table.insert(log, "telegraph")
			return 0.5
		end,
		cast = function()
			table.insert(log, "cast")
			return true
		end,
		cast_timeout = 5,
		on_cancel = function()
			table.insert(log, "cancel")
		end,
	}
end

function M.test_think_interval()
	local m = boss()
	T.eq(m._think, 0.1)
end

function M.test_enrage_rate_unchanged()
	local m = boss()
	for i = 1, 45 do
		T.stub.setTime(i / 10) -- exact times: summing 0.1 drifts below 4.5
		m:OnIntervalThink()
	end
	T.eq(m:GetStackCount(), 2, "+1 stack per 2.25 s")
end

function M.test_submit_then_telegraph()
	local m = boss()
	local log = {}
	T.truthy(m:Submit(job(log)), "Submit returns an id")
	T.eq(#log, 0)
	think(m, 0.1)
	T.eq(log[1], "telegraph")
end

function M.test_confirm_ends_cast()
	local m = boss()
	local log = {}
	m:Submit(job(log))
	think(m, 0.1)
	think(m, 0.5)
	T.eq(log[2], "cast")
	T.eq(m.queue.active.phase, "cast")
	m:Confirm()
	think(m, 0.1)
	T.eq(m.queue.active, nil, "done after Confirm")
end

function M.test_lock_blocks_start()
	local m = boss()
	local log = {}
	local release = m:Lock()
	m:Submit(job(log))
	think(m, 0.1)
	T.eq(#log, 0, "locked: nothing starts")
	release()
	think(m, 0.1)
	T.eq(log[1], "telegraph")
end

function M.test_destroy_cancels_all()
	local m = boss()
	local log = {}
	m:Submit(job(log))
	think(m, 0.1)
	m:Submit(job(log))
	m:OnDestroy()
	T.eq(#log, 3, "telegraph + two cancels")
	T.eq(log[2], "cancel")
	T.eq(log[3], "cancel")
end

function M.test_legacy_tickets()
	local m = boss()
	T.eq(m:RequestTicket(), 0)
	T.eq(m:RequestTicket(), 1)
	T.truthy(m:QueryTicket(0))
	T.falsy(m:QueryTicket(1))
	m:ReleaseTicket()
	T.truthy(m:QueryTicket(1))
	T.eq(m:GetOpenTicket(), 1)
end

function M.test_legacy_lockout_blocks_queue()
	local m = boss()
	local log = {}
	m:RequestTicket()
	m:Lockout()
	m:Lockout()
	T.falsy(m:QueryTicket(0))
	m:Submit(job(log))
	think(m, 0.1)
	T.eq(#log, 0, "lockout blocks queue starts")
	m:ReleaseLockout()
	T.truthy(m:QueryTicket(0))
	think(m, 0.1)
	T.eq(log[1], "telegraph", "double Lockout holds a single queue lock")
end

return M
