--- Error visibility for code the engine calls directly (ListenToGameEvent, Set*Filter), where the
-- xpcall in lib/timers does not reach and an error vanishes without a trace.
--
--   local safe_call = require("lib/safe_call")
--   ListenToGameEvent("entity_killed", safe_call.protect("entity_killed", Dynamic_Wrap(X, "OnKilled")), self)
--
-- protect() only reports: a failed call returns nothing, which a filter reads as false, as before.
local M = {}

-- Must never throw: an error inside an xpcall handler surfaces only as "error in error
-- handling" and the original error is lost. Errors are not always strings (engine errors,
-- error(table)), and the VScript sandbox does not guarantee the debug library.
function M.traceback(err)
	local text = tostring(err)
	if debug and debug.traceback then
		return debug.traceback(text, 2)
	end
	return text
end

function M.protect(name, fn)
	return function(...)
		local n, args = select("#", ...), { ... }
		local ok, result = xpcall(function()
			return fn(unpack(args, 1, n))
		end, M.traceback)
		if ok then
			return result
		end
		Warning(name .. " error: " .. result .. "\n")
	end
end

return M
