require("lib/my")
require("AOHGameMode")

ancient_increase_stats = class({})

function ancient_increase_stats:GetIntrinsicModifierName()
	return "modifier_ancient_increase_stats"
end

LinkLuaModifier(
	"modifier_ancient_increase_stats",
	"abilities/other/ancient_increase_stats.lua",
	LUA_MODIFIER_MOTION_NONE
)
modifier_ancient_increase_stats = class({})

if IsServer() then
	function modifier_ancient_increase_stats:OnCreated()
		self.parent = self:GetParent()
		local ability = self:GetAbility()
		self.health_base = ability:GetSpecialValueFor("health_base")
		self.health_per_round = ability:GetSpecialValueFor("health_per_round")
		self.armor_base = ability:GetSpecialValueFor("armor_base")
		self.armor_per_round = ability:GetSpecialValueFor("armor_per_round")
		self.round = 0
		self:StartIntervalThink(2)
	end
	-- Playtest: a zero max HP means the specials read as 0; log what each getter returns.
	local function warn_zero_max_health(modifier, round, maxHealth)
		local ability = modifier:GetAbility()
		Warning(
			string.format(
				"ancient_increase_stats: round %d max HP %.0f <= 0, HP left as is; level %d, cached base/per_round %s/%s, "
					.. "GetSpecialValueFor %s/%s, GetLevelSpecialValueFor(0) %s/%s\n",
				round,
				maxHealth,
				ability:GetLevel(),
				tostring(modifier.health_base),
				tostring(modifier.health_per_round),
				tostring(ability:GetSpecialValueFor("health_base")),
				tostring(ability:GetSpecialValueFor("health_per_round")),
				tostring(ability:GetLevelSpecialValueFor("health_base", 0)),
				tostring(ability:GetLevelSpecialValueFor("health_per_round", 0))
			)
		)
	end
	local function rescale_health(modifier, round)
		local parent = modifier.parent
		local maxHealth = modifier.health_base + (modifier.health_per_round * round)
		if maxHealth <= 0 then
			warn_zero_max_health(modifier, round, maxHealth)
			return
		end
		local ratio = parent:GetHealth() / parent:GetMaxHealth()
		local health = math.max(1, math.floor(maxHealth * ratio))
		-- Playtest: this rescale is the only SetHealth on the ancient; log it to match a HP jump.
		Warning(
			string.format(
				"ancient_increase_stats: round %d HP %d/%d -> %d/%.0f\n",
				round,
				parent:GetHealth(),
				parent:GetMaxHealth(),
				health,
				maxHealth
			)
		)
		parent:SetMaxHealth(maxHealth)
		parent:SetBaseMaxHealth(maxHealth)
		parent:SetHealth(health)
	end
	function modifier_ancient_increase_stats:OnIntervalThink()
		if self.parent and not self.parent:IsNull() and self.parent:IsAlive() then
			local round = GameRules.GLOBAL_roundNumber
			if round and round > self.round then
				self.parent:AddNewModifier(self.parent, nil, "modifier_ancient_regen", { duration = 5 })
				rescale_health(self, round)

				-- Armor
				local armor = self.armor_base + (self.armor_per_round * round)
				self.parent:SetPhysicalArmorBaseValue(armor)
				--

				self.round = round
			end
		end
	end
end

function modifier_ancient_increase_stats:IsHidden()
	return true
end
function modifier_ancient_increase_stats:IsPurgable()
	return false
end

LinkLuaModifier("modifier_ancient_regen", "abilities/other/ancient_increase_stats.lua", LUA_MODIFIER_MOTION_NONE)
modifier_ancient_regen = class({})
function modifier_ancient_regen:IsBuff()
	return true
end
function modifier_ancient_regen:IsHidden()
	return true
end
function modifier_ancient_regen:IsPurgable()
	return false
end
function modifier_ancient_regen:DeclareFunctions()
	return {
		MODIFIER_PROPERTY_HEALTH_REGEN_PERCENTAGE,
	}
end

function modifier_ancient_regen:GetModifierHealthRegenPercentage()
	return 3
end
