local Q = require("core/boss_queue")
local M = {}

local function job(name, prio, opts)
	local j = {
		name = name,
		prio = prio,
		telegraph = function()
			return 1.0
		end,
		cast = function()
			return true
		end,
		log = {},
	}
	for k, v in pairs(opts or {}) do
		j[k] = v
	end
	return j
end

function M.test_fifo_and_priority()
	local q, u = Q.new(), T.stub.unit("boss")
	q:submit(job("a", 0), 0)
	q:submit(job("b", 0), 0)
	q:submit(job("c", 5), 0)
	T.eq(q:tick(u, 0), "started")
	T.eq(q.active.name, "c", "highest prio first")
	q:tick(u, 1.0) -- telegraph over → cast
	q:confirm()
	T.eq(q:tick(u, 1.1), "done")
	T.eq(q:tick(u, 1.2), "started")
	T.eq(q.active.name, "a", "then FIFO")
end

function M.test_cast_timeout_never_locks_forever()
	local q, u = Q.new(), T.stub.unit("boss")
	q:submit(job("stuck", 0, { cast_timeout = 0.5 }), 0)
	q:tick(u, 0)
	T.eq(q:tick(u, 1.0), "cast")
	T.eq(q:tick(u, 1.2), "waiting")
	T.eq(q:tick(u, 1.6), "done", "unconfirmed cast ends after cast_timeout")
	T.falsy(q.active)
end

function M.test_expired_jobs_are_cancelled()
	local q, u = Q.new(), T.stub.unit("boss")
	local cancelled = false
	q:submit(
		job("old", 0, {
			deadline = 2,
			on_cancel = function()
				cancelled = true
			end,
		}),
		0
	)
	u:set("stunned", true)
	T.eq(q:tick(u, 1), "idle")
	T.eq(q:tick(u, 3), "idle")
	T.truthy(cancelled, "deadline passed while stunned")
	T.eq(#q.queue, 0)
end

function M.test_lock_is_refcounted_and_idempotent()
	local q, u = Q.new(), T.stub.unit("boss")
	q:submit(job("x", 0), 0)
	local r1, r2 = q:lock(), q:lock()
	T.eq(q:tick(u, 0), "idle")
	r1()
	r1()
	T.eq(q.locks, 1, "double release counts once")
	T.eq(q:tick(u, 0), "idle")
	r2()
	T.eq(q:tick(u, 0), "started")
end

function M.test_iterations_repeat_telegraph()
	local q, u = Q.new(), T.stub.unit("boss")
	local casts = 0
	q:submit(
		job("multi", 0, {
			iterations = 2,
			cast = function()
				casts = casts + 1
				return true
			end,
		}),
		0
	)
	q:tick(u, 0)
	q:tick(u, 1.0)
	q:confirm()
	T.eq(q:tick(u, 1.1), "started", "second iteration telegraphs again")
	q:tick(u, 2.1)
	q:confirm()
	T.eq(q:tick(u, 2.2), "done")
	T.eq(casts, 2)
end

function M.test_clear_cancels_everything()
	local q, u = Q.new(), T.stub.unit("boss")
	local n = 0
	q:submit(
		job("a", 0, {
			on_cancel = function()
				n = n + 1
			end,
		}),
		0
	)
	q:submit(
		job("b", 0, {
			on_cancel = function()
				n = n + 1
			end,
		}),
		0
	)
	q:tick(u, 0)
	q:clear()
	T.eq(n, 2)
	T.eq(q.locks, 0)
end

return M
