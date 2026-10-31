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

local function pack(...)
	return select("#", ...), { ... }
end

-- All results pass through: class methods wrapped by protect_class may return several values.
local function wrap(name, fn, on_error)
	return function(...)
		local n, args = pack(...)
		local count, results = pack(xpcall(function()
			return fn(unpack(args, 1, n))
		end, M.traceback))
		if results[1] then
			return unpack(results, 2, count)
		end
		Warning(name .. " error: " .. results[2] .. "\n")
		return on_error
	end
end

function M.protect(name, fn, on_error)
	-- The log shows which engine-invoked handlers actually got wrapped.
	print("[safe_call] protect applied: " .. name)
	return wrap(name, fn, on_error)
end

-- A failing GetModifier* getter reads as 0, the engine's "no bonus"; any other method as nil.
local function class_method_on_error(key)
	if key:match("^GetModifier") then
		return 0
	end
	return nil
end

local function wrap_method(name, key, value)
	if type(value) == "function" and type(key) == "string" then
		return wrap(name .. ":" .. key, value, class_method_on_error(key))
	end
	return value
end

local protected_classes = setmetatable({}, { __mode = "k" })

-- Wraps every method of a class table, the ones it has now and the ones defined later
-- (`function modifier_x:OnCreated()` runs after `modifier_x = class({})`).
function M.protect_class(class_table, name)
	if protected_classes[class_table] then
		return
	end
	protected_classes[class_table] = true
	for key, value in pairs(class_table) do
		rawset(class_table, key, wrap_method(name, key, value))
	end
	-- A copy: class() may share one metatable between tables.
	local mt = {}
	for k, v in pairs(getmetatable(class_table) or {}) do
		mt[k] = v
	end
	mt.__newindex = function(t, key, value)
		rawset(t, key, wrap_method(name, key, value))
	end
	setmetatable(class_table, mt)
	print("[safe_call] protect_class applied: " .. name)
end

-- KV files whose datadriven RunScript blocks name global Lua functions.
local RUNSCRIPT_KV_FILES = {
	"scripts/npc/npc_abilities_custom.txt",
	"scripts/npc/npc_items_custom.txt",
}

local function collect_runscript_functions(kv, names)
	if type(kv) ~= "table" then
		return
	end
	if type(kv.ScriptFile) == "string" and type(kv.Function) == "string" then
		names[kv.Function] = true
	end
	for _, value in pairs(kv) do
		collect_runscript_functions(value, names)
	end
end

local function runscript_functions()
	local names = {}
	for _, path in ipairs(RUNSCRIPT_KV_FILES) do
		collect_runscript_functions(LoadKeyValues(path), names)
	end
	return names
end

-- Diagnostic layer, on the global table because the engine loads ability, item, LinkLuaModifier
-- and RunScript files lazily:
-- * protect_class on every table made by class() once it is stored in a global. A global that
--   already exists is not new, so a class re-created by script_reload stays unwrapped.
-- * protect on every global function a RunScript names. These live in a shadow table read
--   through __index, so each redefinition (one name is shared by several ScriptFiles) passes
--   __newindex and is wrapped too.
function M.protect_all()
	-- luacheck: globals class
	local made_by_class = setmetatable({}, { __mode = "k" })
	local base_class = class
	class = function(...)
		local c = base_class(...)
		made_by_class[c] = true
		return c
	end
	local runscript = runscript_functions()
	local shadow = {}
	local mt = getmetatable(_G) or {}
	local base_newindex = mt.__newindex or rawset
	local base_index = mt.__index or function() end
	local function store_runscript(key, value)
		if shadow[key] == nil then
			print("[safe_call] protect applied: RunScript " .. key)
		end
		shadow[key] = type(value) == "function" and wrap("RunScript " .. key, value) or value
	end
	for key in pairs(runscript) do
		local value = rawget(_G, key)
		if value ~= nil then
			rawset(_G, key, nil)
			store_runscript(key, value)
		end
	end
	mt.__index = function(t, key)
		if runscript[key] then
			return shadow[key]
		end
		return base_index(t, key)
	end
	mt.__newindex = function(t, key, value)
		if runscript[key] then
			store_runscript(key, value)
			return
		end
		base_newindex(t, key, value)
		if made_by_class[value] then
			M.protect_class(value, tostring(key))
		end
	end
	setmetatable(_G, mt)
end

return M
