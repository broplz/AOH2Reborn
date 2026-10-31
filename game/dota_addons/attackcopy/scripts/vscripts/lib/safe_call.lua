--- Error visibility for code the engine calls directly (ListenToGameEvent, Set*Filter, SetThink,
-- CustomGameEventManager listeners), where the xpcall in lib/timers does not reach and an error
-- vanishes without a trace.
--
--   local safe_call = require("lib/safe_call")
--   ListenToGameEvent("entity_killed", safe_call.protect("entity_killed", Dynamic_Wrap(X, "OnKilled")), self)
--
-- protect() only reports: a failed call returns on_error, nothing by default, which a filter
-- reads as false, as before. A think passes its usual interval, so an error does not unschedule it.
local M = {}

-- Errors are not always strings (engine errors, error(table) with a failing __tostring), and
-- the VScript sandbox does not guarantee the debug library.
local function describe(err)
	local text = tostring(err)
	if debug and debug.traceback then
		-- Level 4 skips describe, pcall and traceback: the trace starts where the error was raised.
		return debug.traceback(text, 4)
	end
	return text
end

-- Must never throw: an error inside an xpcall handler surfaces only as "error in error
-- handling" and the original error is lost. print, not Warning: Warning may be what failed.
function M.traceback(err)
	local ok, text = pcall(describe, err)
	if ok then
		return text
	end
	print("safe_call handler failed: " .. tostring(text))
	return "(error could not be described)"
end

function M.protect(name, fn, on_error)
	-- The log shows which engine-invoked handlers actually got wrapped.
	print("[safe_call] protect applied: " .. name)
	return function(...)
		local n, args = select("#", ...), { ... }
		local ok, result = xpcall(function()
			return fn(unpack(args, 1, n))
		end, M.traceback)
		if ok then
			return result
		end
		Warning(name .. " error: " .. result .. "\n")
		return on_error
	end
end

return M
