--- Boss cast queue (ADR-0002 §5): the replacement for the ticket system in generic.lua.
-- Pure logic, no engine calls at load time, so tests/test_boss_queue.lua runs it on the stub.
-- modifier_boss owns one queue per boss and calls queue:tick(unit, now) from OnIntervalThink.
--
-- job = {
--   name      = "boss_x_fissure",        -- for logs
--   prio      = 0,                        -- higher first; equal prio = FIFO
--   deadline  = 6,                        -- seconds a job may wait in the queue before it is dropped
--   telegraph = function(job) ... return duration end,  -- show the warning; returns seconds until cast
--   cast      = function(job) ... return ok end,         -- issue the cast order; false = give up
--   cast_timeout = 1.5,                   -- seconds to wait for `confirmed` before moving on
--   iterations = 1,                       -- telegraph+cast repeats
--   on_cancel = function(job) end,        -- release particles / dummies
-- }
-- The target ability's OnSpellStart sets queue.active.confirmed = true (via modifier_boss:Confirm()).
local M = {}
M.__index = M

function M.new()
	return setmetatable({ queue = {}, active = nil, locks = 0, seq = 0 }, M)
end

local function busy(unit)
	return unit:IsChanneling()
		or unit:GetCurrentActiveAbility() ~= nil
		or unit:IsStunned()
		or unit:IsHexed()
		or unit:IsCommandRestricted()
end

local function sorted_insert(list, job)
	local i = #list + 1
	for k, other in ipairs(list) do
		if job.prio > other.prio then
			i = k
			break
		end
	end
	table.insert(list, i, job)
end

--- Submit a job; returns its id. `now` is GameRules:GetGameTime() (passed in for testability).
function M:submit(job, now)
	self.seq = self.seq + 1
	job.id = self.seq
	job.prio = job.prio or 0
	job.submitted = now
	job.expires = now + (job.deadline or 6)
	job.iterations = job.iterations or 1
	sorted_insert(self.queue, job)
	return job.id
end

--- Reference-counted lockout. Returns an idempotent release function.
function M:lock()
	self.locks = self.locks + 1
	local released = false
	return function()
		if not released then
			released = true
			self.locks = self.locks - 1
		end
	end
end

function M:confirm()
	if self.active then
		self.active.confirmed = true
	end
end

local function cancel(job)
	if job.on_cancel then
		job.on_cancel(job)
	end
end

--- Drop everything (boss died / removed).
function M:clear()
	if self.active then
		cancel(self.active)
	end
	for _, j in ipairs(self.queue) do
		cancel(j)
	end
	self.queue, self.active, self.locks = {}, nil, 0
end

--- One scheduler step. Returns what happened: "idle" | "waiting" | "started" | "cast" | "done" | "expired".
function M:tick(unit, now)
	for i = #self.queue, 1, -1 do
		local j = self.queue[i]
		if now > j.expires then
			table.remove(self.queue, i)
			cancel(j)
		end
	end
	local a = self.active
	if a then
		if a.phase == "telegraph" and now >= a.fire_at then
			a.phase, a.fire_at, a.confirmed = "cast", now + (a.cast_timeout or 1.5), false
			if not a.cast(a) then
				a.phase = "done"
			end
			if a.phase ~= "done" then
				return "cast"
			end
		elseif a.phase == "cast" and (a.confirmed or now >= a.fire_at) then
			a.iterations = a.iterations - 1
			if a.iterations > 0 then
				a.phase, a.fire_at = "telegraph", now + a.telegraph(a)
				return "started"
			end
			a.phase = "done"
		end
		if a.phase == "done" then
			self.active = nil
			return "done"
		end
		return "waiting"
	end
	if self.locks > 0 or #self.queue == 0 or busy(unit) then
		return "idle"
	end
	local j = table.remove(self.queue, 1)
	j.phase, j.fire_at = "telegraph", now + j.telegraph(j)
	self.active = j
	return "started"
end

return M
