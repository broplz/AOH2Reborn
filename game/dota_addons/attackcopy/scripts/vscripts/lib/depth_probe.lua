--- Temporary diagnostics for the playtest-3 "error in error handling" storm (recursion is
-- suspected; debug.sethook is not available in the Valve VM). probe(name, fn) returns fn wrapped
-- in a per-name depth counter: one Warning on the first call of each name (the log order shows
-- what ran before the storm) and one when its depth first exceeds DEPTH_LIMIT. An error inside fn
-- skips the decrement. Delete this file and its probe(...) lines once the recursion is found.
local DEPTH_LIMIT = 20

local depth = {}
local seen = {}
local reported = {}

local function leave(name, ...)
	depth[name] = depth[name] - 1
	return ...
end

local function probe(name, fn)
	depth[name] = 0
	return function(...)
		if not seen[name] then
			seen[name] = true
			Warning("[depth] first call " .. name .. "\n")
		end
		depth[name] = depth[name] + 1
		if depth[name] > DEPTH_LIMIT and not reported[name] then
			reported[name] = true
			Warning("[depth] " .. name .. " depth=" .. depth[name] .. "\n")
		end
		return leave(name, fn(...))
	end
end

return probe
