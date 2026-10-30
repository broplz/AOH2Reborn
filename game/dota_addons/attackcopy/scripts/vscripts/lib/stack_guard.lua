--- Temporary diagnostics for the playtest-3 "error in error handling" storm (stack overflow is
-- suspected). A "call" hook watches the Lua stack depth; the first call deeper than DEPTH_LIMIT
-- levels prints one traceback via Warning and removes the hook. Delete this file and its require
-- in aohgamemode.lua once the recursion is found.
local M = {}

local DEPTH_LIMIT = 200
-- Inside a hook level 1 is the hook itself and level 2 the function being called, so the called
-- function sits deeper than DEPTH_LIMIT exactly when level DEPTH_LIMIT + 2 exists.
local PROBE_LEVEL = DEPTH_LIMIT + 2

local function on_call()
	if debug.getinfo(PROBE_LEVEL, "l") == nil then
		return
	end
	debug.sethook()
	Warning("[stack_guard] call depth > " .. DEPTH_LIMIT .. ", hook removed\n" .. debug.traceback("", 2) .. "\n")
end

local function arm()
	debug.sethook(on_call, "c")
end

function M.install()
	if not (debug and debug.sethook and debug.getinfo and debug.traceback) then
		Warning("[stack_guard] debug.sethook/getinfo/traceback not available in this VM, guard disabled\n")
		return
	end
	-- pcall: the sandbox may expose sethook as a stub that throws.
	local ok, err = pcall(arm)
	if not ok then
		Warning("[stack_guard] debug.sethook failed, guard disabled: " .. tostring(err) .. "\n")
		return
	end
	print("[stack_guard] armed, depth limit " .. DEPTH_LIMIT)
end

return M
