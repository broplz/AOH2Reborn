require("lib/timers")

function courier_spell(keys)
	local caster = keys.caster
	keys.ability:ApplyDataDrivenModifier(caster, caster, "modifier_courier_invincibility", {})
end

-- playtest diag (0058): RunScript errors surface only as "error in error handling"; wrap in the
-- RunScript scope (getfenv(1), not _G), as generic.lua does.
require("lib/safe_call").protect_scope(getfenv(1), { "courier_spell" })
