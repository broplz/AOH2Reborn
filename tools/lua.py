#!/usr/bin/env python3
"""Fallback Lua 5.1 interpreter for tests when no `lua5.1`/`luajit` binary is installed:
runs a script through lupa's bundled LuaJIT (pip install lupa). `arg` is set like the C
interpreter does, so `tools/lua.py tests/run.lua [pattern]` behaves like `lua tests/run.lua`.
"""
import sys

try:
    from lupa.luajit21 import LuaRuntime
except ImportError:  # older lupa
    from lupa.lua51 import LuaRuntime  # type: ignore

script = sys.argv[1]
rt = LuaRuntime(unpack_returned_tuples=True)
g = rt.globals()
argt = rt.table()
argt[0] = script
for i, a in enumerate(sys.argv[2:], 1):
    argt[i] = a
g["arg"] = argt
code = rt.eval('function(path) local f, err = loadfile(path); if not f then error(err) end; return f() end')
try:
    code(script)
except Exception as e:  # noqa: BLE001
    msg = str(e)
    if "exit" in msg.lower():
        pass
    else:
        sys.stderr.write(msg + "\n")
        sys.exit(1)
