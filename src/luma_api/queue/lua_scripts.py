"""Redis Lua scripts for atomic operations."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redis.asyncio import Redis

# Sliding window rate limit check and increment
# Keys: [rate_limit_key]
# Args: [window_seconds, limit, current_time, request_id]
# Returns: [allowed (0/1), remaining, reset_timestamp]
RATE_LIMIT_SCRIPT = """
local key = KEYS[1]
local window = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local request_id = ARGV[4]

-- Remove expired entries (older than window)
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)

-- Count current requests in window
local count = redis.call('ZCARD', key)

if count < limit then
    -- Add this request
    redis.call('ZADD', key, now, request_id)
    -- Set expiry to clean up old keys
    redis.call('EXPIRE', key, window * 2)
    return {1, limit - count - 1, math.floor(now + window)}
else
    -- Rate limited
    -- Get oldest request time to calculate reset
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local reset_at = now + window
    if oldest and #oldest >= 2 then
        reset_at = tonumber(oldest[2]) + window
    end
    return {0, 0, math.floor(reset_at)}
end
"""

# Atomic queue enqueue with position calculation
# Keys: [queue_key]
# Args: [job_id, score (timestamp)]
# Returns: [position]
QUEUE_ENQUEUE_SCRIPT = """
local key = KEYS[1]
local job_id = ARGV[1]
local score = tonumber(ARGV[2])

-- Add to sorted set
redis.call('ZADD', key, score, job_id)

-- Get position (0-indexed, convert to 1-indexed)
local position = redis.call('ZRANK', key, job_id)
return position + 1
"""

# Atomic queue dequeue (pop lowest score item)
# Keys: [queue_key]
# Args: none
# Returns: [job_id] or nil
QUEUE_DEQUEUE_SCRIPT = """
local key = KEYS[1]

-- Get the item with lowest score (oldest/highest priority)
local items = redis.call('ZRANGE', key, 0, 0)

if #items == 0 then
    return nil
end

local job_id = items[1]

-- Remove it from the queue
redis.call('ZREM', key, job_id)

return job_id
"""

# Get queue position for a job
# Keys: [queue_key]
# Args: [job_id]
# Returns: [position] or -1 if not found
QUEUE_POSITION_SCRIPT = """
local key = KEYS[1]
local job_id = ARGV[1]

local position = redis.call('ZRANK', key, job_id)

if position == false then
    return -1
end

return position + 1
"""

# Increment usage counter with daily/monthly tracking
# Keys: [daily_key, monthly_key]
# Args: [amount]
# Returns: [daily_count, monthly_count]
USAGE_INCREMENT_SCRIPT = """
local daily_key = KEYS[1]
local monthly_key = KEYS[2]
local amount = tonumber(ARGV[1])

local daily = redis.call('INCRBY', daily_key, amount)
local monthly = redis.call('INCRBY', monthly_key, amount)

-- Set expiry on daily key (25 hours to handle timezone edge cases)
redis.call('EXPIRE', daily_key, 90000)

-- Set expiry on monthly key (32 days)
redis.call('EXPIRE', monthly_key, 2764800)

return {daily, monthly}
"""


class LuaScripts:
    """Manager for Lua script SHA hashes."""

    def __init__(self) -> None:
        self.rate_limit_sha: str | None = None
        self.queue_enqueue_sha: str | None = None
        self.queue_dequeue_sha: str | None = None
        self.queue_position_sha: str | None = None
        self.usage_increment_sha: str | None = None
        self._loaded = False

    async def load(self, redis_client: "Redis") -> None:
        """Load all scripts into Redis and store SHA hashes."""
        if self._loaded:
            return

        self.rate_limit_sha = await redis_client.script_load(RATE_LIMIT_SCRIPT)
        self.queue_enqueue_sha = await redis_client.script_load(QUEUE_ENQUEUE_SCRIPT)
        self.queue_dequeue_sha = await redis_client.script_load(QUEUE_DEQUEUE_SCRIPT)
        self.queue_position_sha = await redis_client.script_load(QUEUE_POSITION_SCRIPT)
        self.usage_increment_sha = await redis_client.script_load(USAGE_INCREMENT_SCRIPT)
        self._loaded = True

    def reset(self) -> None:
        """Reset loaded state (for testing)."""
        self._loaded = False
        self.rate_limit_sha = None
        self.queue_enqueue_sha = None
        self.queue_dequeue_sha = None
        self.queue_position_sha = None
        self.usage_increment_sha = None


# Global instance
lua_scripts = LuaScripts()
