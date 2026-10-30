--- Temporary diagnostics for the playtest-3 "error in error handling" storm (recursion is
-- suspected; debug.sethook is not available in the Valve VM). probe(name, fn) returns fn wrapped
-- in a per-name depth counter: one Warning on the first call of each name (the log order shows
-- what ran before the storm) and one when its depth first exceeds DEPTH_LIMIT. fn runs under
-- pcall: its first error per name is logged with the parent's class (when the first argument is
-- a modifier) and the call returns nil. Delete this file and its probe(...) lines once the
-- recursion is found.
local DEPTH_LIMIT = 20

local depth = {}
local seen = {}
local reported = {}
local errored = {}

local function parent_class(self)
	local ok, class = pcall(function()
		return self:GetParent():GetClassname()
	end)
	return ok and class or "?"
end

local function leave(name, self, ok, ...)
	depth[name] = depth[name] - 1
	if ok then
		return ...
	end
	if errored[name] then
		return nil
	end
	errored[name] = true
	Warning("[depth] " .. name .. " error: " .. tostring(...) .. " parent=" .. parent_class(self) .. "\n")
	return nil
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
		return leave(name, (...), pcall(fn, ...))
	end
end

return probe
