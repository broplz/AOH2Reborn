-- Takes care of all of the timing and skills for applicable abilities. Tickets are granted and incremented by abilties, it's up to
-- the abilities to make sure that tickets are properly released and checked. Lockouts are used by abilities to force lock the ability
-- queue.
-- The engine needs the modifier class as a global (ADR-0002 rule 1).
-- luacheck: globals modifier_boss
modifier_boss = class({})

function modifier_boss:IsBuff()
	return true
end
function modifier_boss:IsHidden()
	return false
end

function modifier_boss:GetTexture()
	return "earth_spirit_rolling_boulder"
end

function modifier_boss:IsPurgable()
	return false
end

function modifier_boss:DeclareFunctions()
	local funcs = {
		MODIFIER_PROPERTY_DAMAGEOUTGOING_PERCENTAGE,
		MODIFIER_PROPERTY_MOVESPEED_BONUS_PERCENTAGE,
	}
	return funcs
end

function modifier_boss:GetModifierDamageOutgoing_Percentage()
	return self:GetStackCount()
end
function modifier_boss:GetModifierMoveSpeedBonus_Percentage()
	return self:GetStackCount() * 0.33
end

if IsServer() then
	local Q = require("core/boss_queue")
	local STACK_INTERVAL = 2.25

	function modifier_boss:OnCreated()
		self.parent = self:GetParent()
		self.available_ticket = 0
		self.open_ticket = 0
		self.lockout = false
		self.lockout_release = nil
		self.queue = Q.new()
		self.next_stack_at = GameRules:GetGameTime() + STACK_INTERVAL
		self:StartIntervalThink(0.1)
	end

	function modifier_boss:OnDestroy()
		self.lockout_release = nil
		self.queue:clear()
	end

	-- Cast queue (ADR-0002 §5): see core/boss_queue.lua for the job shape.
	function modifier_boss:Submit(job)
		return self.queue:submit(job, GameRules:GetGameTime())
	end

	function modifier_boss:Lock()
		return self.queue:lock()
	end

	function modifier_boss:Confirm()
		self.queue:confirm()
	end

	function modifier_boss:RequestTicket()
		local ticket = self.available_ticket
		self.available_ticket = self.available_ticket + 1
		return ticket
	end

	function modifier_boss:GetOpenTicket()
		return self.open_ticket
	end

	function modifier_boss:QueryTicket(key)
		if key == self.open_ticket and self.lockout ~= true then
			return true
		else
			return false
		end
	end

	function modifier_boss:ReleaseTicket()
		self.open_ticket = self.open_ticket + 1
	end

	-- Legacy lockout also holds one queue lock, so ticket users and queue jobs never overlap.
	function modifier_boss:Lockout()
		self.lockout = true
		self.lockout_release = self.lockout_release or self.queue:lock()
	end
	function modifier_boss:ReleaseLockout()
		self.lockout = false
		if self.lockout_release then
			self.lockout_release()
			self.lockout_release = nil
		end
	end

	function modifier_boss:OnIntervalThink()
		local now = GameRules:GetGameTime()
		if now >= self.next_stack_at then
			self:IncrementStackCount()
			self.next_stack_at = self.next_stack_at + STACK_INTERVAL
		end
		self.queue:tick(self.parent, now)
	end
end
