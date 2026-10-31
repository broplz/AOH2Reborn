-- luacheck: globals Warning
local safe_call = require("lib/safe_call")

local M = {}

local function capture_warnings(fn)
	local saved, lines = Warning, {}
	Warning = function(s)
		lines[#lines + 1] = s
	end
	local ok, err = pcall(fn)
	Warning = saved
	assert(ok, err)
	return lines
end

function M.test_passes_args_and_result_through()
	local wrapped = safe_call.protect("f", function(a, b, c)
		return tostring(a) .. tostring(b) .. tostring(c)
	end)
	local lines = capture_warnings(function()
		T.eq(wrapped(1, nil, 3), "1nil3")
	end)
	T.eq(#lines, 0)
end

function M.test_error_is_reported_with_name_and_swallowed()
	local wrapped = safe_call.protect("entity_killed", function()
		error({ code = 7 })
	end)
	local lines = capture_warnings(function()
		T.eq(wrapped(), nil)
	end)
	T.eq(#lines, 1)
	T.truthy(lines[1]:find("^entity_killed error: table:"), lines[1])
end

return M
