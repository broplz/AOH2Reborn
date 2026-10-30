require("lib/my")

-- Fixes the magic res str gives. Check if it is a hero before calling.
function fix_atr_for_hero(hero)
	if not hero:HasAbility("hero_attribute_fix") then
		local ability = hero:AddAbility("hero_attribute_fix")
		ability:SetLevel(1)
	end
end

-- Temporary playtest-3 diagnostics (lib/depth_probe); the legacy global trips W111/W113.
-- luacheck: push ignore 111 113
fix_atr_for_hero = require("lib/depth_probe")("fix_atr_for_hero", fix_atr_for_hero)
-- luacheck: pop
