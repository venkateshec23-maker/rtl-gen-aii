"""
Rate Limiting for RTL-Gen AI

Prevents abuse by limiting requests per user/IP.

Usage:
    from python.rate_limiter import RateLimiter
    
    limiter = RateLimiter(max_requests=100, window_seconds=3600)
    
    if limiter.is_allowed(user_id):
        # Process request
    else:
        # Reject request
"""

import time
from collections import defaultdict
from typing import Dict, Optional
import threading


class RateLimiter:
    """
    Token bucket rate limiter.
    
    Limits number of requests per time window per user/IP.
    """
    
    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 3600,
        enable_burst: bool = True,
        burst_multiplier: float = 1.5
    ):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
            enable_burst: Allow burst requests
            burst_multiplier: Burst capacity multiplier
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.enable_burst = enable_burst
        self.burst_capacity = int(max_requests * burst_multiplier) if enable_burst else max_requests
        
        # Storage: user_id -> (tokens, last_update)
        self.buckets: Dict[str, tuple] = defaultdict(lambda: (self.burst_capacity, time.time()))
        
        # Lock for thread safety
        self.lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'allowed_requests': 0,
            'rejected_requests': 0,
        }
    
    def _refill_tokens(self, user_id: str) -> float:
        """
        Refill tokens based on elapsed time.
        
        Args:
            user_id: User identifier
            
        Returns:
            float: Current token count
        """
        tokens, last_update = self.buckets[user_id]
        
        # Calculate tokens to add
        now = time.time()
        elapsed = now - last_update
        
        # Refill rate: max_requests per window_seconds
        refill_rate = self.max_requests / self.window_seconds
        tokens_to_add = elapsed * refill_rate
        
        # Add tokens (up to burst capacity)
        new_tokens = min(self.burst_capacity, tokens + tokens_to_add)
        
        # Update bucket
        self.buckets[user_id] = (new_tokens, now)
        
        return new_tokens
    
    def is_allowed(self, user_id: str, cost: float = 1.0) -> bool:
        """
        Check if request is allowed.
        
        Args:
            user_id: User identifier (user ID, IP address, etc.)
            cost: Token cost of this request
            
        Returns:
            bool: True if allowed, False if rate limited
        """
        with self.lock:
            self.stats['total_requests'] += 1
            
            # Refill tokens
            tokens = self._refill_tokens(user_id)
            
            # Check if enough tokens
            if tokens >= cost:
                # Deduct tokens
                new_tokens, last_update = self.buckets[user_id]
                self.buckets[user_id] = (new_tokens - cost, last_update)
                
                self.stats['allowed_requests'] += 1
                return True
            else:
                self.stats['rejected_requests'] += 1
                return False
    
    def get_remaining(self, user_id: str) -> float:
        """
        Get remaining tokens for user.
        
        Args:
            user_id: User identifier
            
        Returns:
            float: Remaining tokens
        """
        with self.lock:
            tokens = self._refill_tokens(user_id)
            return tokens
    
    def reset(self, user_id: str):
        """Reset rate limit for user."""
        with self.lock:
            self.buckets[user_id] = (self.burst_capacity, time.time())
    
    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        with self.lock:
            rejection_rate = 0
            if self.stats['total_requests'] > 0:
                rejection_rate = (self.stats['rejected_requests'] / self.stats['total_requests']) * 100
            
            return {
                'total_requests': self.stats['total_requests'],
                'allowed': self.stats['allowed_requests'],
                'rejected': self.stats['rejected_requests'],
                'rejection_rate': rejection_rate,
                'active_users': len(self.buckets),
            }


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("Rate Limiter Self-Test\n")
    
    # Create limiter: 5 requests per 10 seconds
    limiter = RateLimiter(max_requests=5, window_seconds=10)
    
    user = "test_user"
    
    print("Testing rate limiting (5 requests per 10 seconds):\n")
    
    # Try 10 requests rapidly
    for i in range(10):
        allowed = limiter.is_allowed(user)
        remaining = limiter.get_remaining(user)
        
        status = "✓ ALLOWED" if allowed else "✗ BLOCKED"
        print(f"Request {i+1}: {status} (Remaining: {remaining:.2f})")
        
        time.sleep(0.5)
    
    print("\nWaiting 5 seconds for token refill...")
    time.sleep(5)
    
    print("\nTrying again after waiting:")
    for i in range(3):
        allowed = limiter.is_allowed(user)
        remaining = limiter.get_remaining(user)
        
        status = "✓ ALLOWED" if allowed else "✗ BLOCKED"
        print(f"Request {i+1}: {status} (Remaining: {remaining:.2f})")
    
    print("\nRate Limiter Statistics:")
    stats = limiter.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✓ Self-test complete")
