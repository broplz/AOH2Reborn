-- luacheck: globals Warning class LoadKeyValues modifier_safe_call_test safe_call_runscript_test
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

function M.test_think_keeps_its_interval_after_an_error()
	local wrapped = safe_call.protect("OnThink", function()
		error("boom")
	end, 1.1)
	local lines = capture_warnings(function()
		T.eq(wrapped(), 1.1)
	end)
	T.eq(#lines, 1)
end

function M.test_failing_handler_still_reports()
	local wrapped = safe_call.protect("OnThink", function()
		error(setmetatable({}, {
			__tostring = function()
				error("bad tostring")
			end,
		}))
	end, 1.1)
	local lines = capture_warnings(function()
		T.eq(wrapped(), 1.1)
	end)
	T.eq(#lines, 1)
	T.truthy(lines[1]:find("^OnThink error: %(error could not be described%)"), lines[1])
end

local function failing()
	error("boom")
end

function M.test_protect_class_wraps_existing_and_later_methods()
	local c = class({})
	c.OnCreated = failing
	safe_call.protect_class(c, "modifier_t")
	c.GetModifierBonus = failing
	function c:Pair()
		return 1, nil, 3
	end
	local lines = capture_warnings(function()
		T.eq(c.OnCreated(), nil)
		T.eq(c.GetModifierBonus(), 0)
		local n, a, b, d = select("#", c:Pair()), c:Pair()
		T.eq(n, 3)
		T.eq(a, 1)
		T.eq(b, nil)
		T.eq(d, 3)
	end)
	T.eq(#lines, 2)
	T.truthy(lines[1]:find("^modifier_t:OnCreated error:"), lines[1])
	T.truthy(lines[2]:find("^modifier_t:GetModifierBonus error:"), lines[2])
end

-- Runs fn under protect_all with LoadKeyValues returning kv, then restores the globals it touched.
local function with_protect_all(kv, globals, fn)
	local saved_class, saved_mt, saved_load = class, getmetatable(_G), LoadKeyValues
	LoadKeyValues = function()
		return kv
	end
	safe_call.protect_all()
	local ok, err = pcall(fn)
	class, LoadKeyValues = saved_class, saved_load
	setmetatable(_G, saved_mt)
	for _, name in ipairs(globals) do
		rawset(_G, name, nil)
	end
	assert(ok, err)
end

function M.test_protect_all_covers_classes_stored_in_globals()
	with_protect_all({}, { "modifier_safe_call_test" }, function()
		modifier_safe_call_test = class({})
		modifier_safe_call_test.GetModifierBonus = failing
		local lines = capture_warnings(function()
			T.eq(modifier_safe_call_test.GetModifierBonus(), 0)
		end)
		T.eq(#lines, 1)
		T.truthy(lines[1]:find("^modifier_safe_call_test:GetModifierBonus error:"), lines[1])
	end)
end

function M.test_protect_all_covers_every_definition_of_a_runscript_function()
	local kv = {
		boss_x = {
			Modifiers = {
				modifier_x = {
					OnIntervalThink = {
						RunScript = {
							ScriptFile = "abilities/bosses/x.lua",
							Function = "safe_call_runscript_test",
						},
					},
				},
			},
		},
	}
	with_protect_all(kv, {}, function()
		safe_call_runscript_test = failing
		safe_call_runscript_test = function(keys)
			error("second " .. keys.n)
		end
		local lines = capture_warnings(function()
			T.eq(safe_call_runscript_test({ n = 2 }), nil)
		end)
		T.eq(#lines, 1)
		T.truthy(lines[1]:find("^RunScript safe_call_runscript_test error: .*second 2"), lines[1])
	end)
end

return M
