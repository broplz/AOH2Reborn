-- Tiny test runner: `lua tests/run.lua [pattern]` runs tests/test_*.lua whose name matches.
-- Each test file returns a table of functions `test_xxx`; `assert`-style helpers below.
package.path = "./?.lua;./tests/?.lua;./game/dota_addons/attackcopy/scripts/vscripts/?.lua;" .. package.path
local pattern = arg[1] or ""
local stub = require("dota_stub")

T = {} -- helpers visible to test files
function T.eq(a, b, msg)
	if a ~= b then
		error((msg or "") .. " expected " .. tostring(b) .. ", got " .. tostring(a), 2)
	end
end
function T.truthy(v, msg)
	if not v then
		error((msg or "") .. " expected truthy, got " .. tostring(v), 2)
	end
end
function T.falsy(v, msg)
	if v then
		error((msg or "") .. " expected falsy, got " .. tostring(v), 2)
	end
end
T.stub = stub

local function listdir(dir)
	local p = io.popen('ls "' .. dir .. '"')
	local out = {}
	for line in p:lines() do
		out[#out + 1] = line
	end
	p:close()
	table.sort(out)
	return out
end

local files, passed, failed = 0, 0, {}
for _, f in ipairs(listdir("tests")) do
	if f:match("^test_.*%.lua$") and f:find(pattern, 1, true) then
		files = files + 1
		local mod = dofile("tests/" .. f)
		local names = {}
		for k, v in pairs(mod) do
			if type(v) == "function" and k:match("^test_") then
				names[#names + 1] = k
			end
		end
		table.sort(names)
		for _, name in ipairs(names) do
			stub.setTime(0)
			stub.Timers.timers = {}
			local ok, err = pcall(mod[name])
			if ok then
				passed = passed + 1
			else
				failed[#failed + 1] = f .. ":" .. name .. ": " .. tostring(err)
			end
		end
	end
end
for _, e in ipairs(failed) do
	io.stderr:write("FAIL " .. e .. "\n")
end
io.write(string.format("tests: %d files, %d passed, %d failed\n", files, passed, #failed))
os.exit(#failed == 0 and 0 or 1)
