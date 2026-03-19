"""
Cache Manager for RTL-Gen AII.
Caches LLM responses to save tokens and speed up repeated requests.
"""

import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta

from python.config import CACHE_DIR, ENABLE_CACHING


class CacheManager:
    """Manages caching of LLM responses."""

    def __init__(self, cache_dir=None, ttl_days=30):
        self.cache_dir = Path(cache_dir) if cache_dir else (CACHE_DIR / 'responses')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_days = ttl_days
        self.ttl_hours = ttl_days * 24
        self.index_file = self.cache_dir / 'cache_index.json'
        self.index = self._load_index()
        self.hits = 0
        self.misses = 0
        self._clean_expired()

    def _load_index(self):
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_index(self):
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self.index, f, indent=2)
        except IOError:
            pass

    def _clean_expired(self):
        if not ENABLE_CACHING:
            return
        now = datetime.now()
        expired = []
        for key, info in self.index.items():
            ts = datetime.fromisoformat(info.get('timestamp', '2000-01-01'))
            if now - ts > timedelta(days=self.ttl_days):
                expired.append(key)
                cache_file = self.cache_dir / f"{key}.json"
                if cache_file.exists():
                    cache_file.unlink()
        for key in expired:
            del self.index[key]
        if expired:
            self._save_index()

    def _generate_key(self, prompt, **kwargs):
        unique_str = prompt + str(sorted(kwargs.items()))
        return hashlib.sha256(unique_str.encode()).hexdigest()[:16]

    def get(self, prompt, **kwargs):
        """Get cached response. Returns dict or None."""
        if not ENABLE_CACHING:
            return None
        key = self._generate_key(prompt, **kwargs)
        cache_file = self.cache_dir / f"{key}.json"
        if not cache_file.exists():
            self.misses += 1
            return None
        try:
            with open(cache_file, 'r') as f:
                entry = json.load(f)
            ts = datetime.fromisoformat(entry.get('timestamp', '2000-01-01'))
            if datetime.now() - ts > timedelta(days=self.ttl_days):
                cache_file.unlink()
                self.index.pop(key, None)
                self._save_index()
                return None
            if key in self.index:
                self.index[key]['hits'] = self.index[key].get('hits', 0) + 1
                self._save_index()
            self.hits += 1
            return entry.get('response')
        except (json.JSONDecodeError, IOError, KeyError):
            return None

    def set(self, prompt, response, tokens_saved=0, **kwargs):
        """Cache a response."""
        if not ENABLE_CACHING:
            return
        key = self._generate_key(prompt, **kwargs)
        cache_file = self.cache_dir / f"{key}.json"
        entry = {
            'key': key,
            'prompt': prompt[:100] + '...' if len(prompt) > 100 else prompt,
            'response': response,
            'timestamp': datetime.now().isoformat(),
            'tokens_saved': tokens_saved
        }
        try:
            with open(cache_file, 'w') as f:
                json.dump(entry, f, indent=2)
            self.index[key] = {
                'timestamp': entry['timestamp'],
                'hits': 1,
                'tokens_saved': tokens_saved
            }
            self._save_index()
        except IOError:
            pass

    def clear(self):
        """Clear all cache."""
        for f in self.cache_dir.glob("*.json"):
            f.unlink()
        self.index = {}
        self._save_index()

    def get_stats(self) -> dict:
        """Get detailed cache statistics."""
        total_keys = len(list(self.cache_dir.glob("*.json")))
        total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.json"))
        
        hit_rate = (self.hits / (self.hits + self.misses) * 100) if (self.hits + self.misses) > 0 else 0
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'total_cached_items': total_keys,
            'total_size_mb': total_size / 1024 / 1024,
            'cache_directory': str(self.cache_dir),
        }

    def cleanup_expired(self):
        """Remove all expired cache entries."""
        removed = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            if cache_file.name == 'cache_index.json':
                continue
            try:
                data = json.loads(cache_file.read_text())
                cache_time = datetime.fromisoformat(data['timestamp'])
                age_hours = (datetime.now() - cache_time).total_seconds() / 3600
                
                if age_hours > self.ttl_hours:
                    cache_file.unlink()
                    removed += 1
            except Exception:
                pass
        
        return removed

    def get_cache_size_limit(self) -> int:
        """Get max cache size in MB."""
        return 100  # 100 MB limit

    def enforce_size_limit(self):
        """
        Enforce cache size limit using LRU eviction.
        Removes oldest entries if cache exceeds size limit.
        """
        max_size_bytes = self.get_cache_size_limit() * 1024 * 1024
        
        # Get all cache files with their access times
        cache_files = []
        for cache_file in self.cache_dir.glob("*.json"):
            if cache_file.name == 'cache_index.json':
                continue
            try:
                stat = cache_file.stat()
                cache_files.append({
                    'path': cache_file,
                    'size': stat.st_size,
                    'atime': stat.st_atime,
                })
            except Exception:
                pass
        
        # Calculate total size
        total_size = sum(f['size'] for f in cache_files)
        
        if total_size <= max_size_bytes:
            return 0  # No cleanup needed
        
        # Sort by access time (oldest first)
        cache_files.sort(key=lambda x: x['atime'])
        
        # Remove files until under limit
        removed = 0
        for file_info in cache_files:
            if total_size <= max_size_bytes:
                break
            
            try:
                file_info['path'].unlink()
                total_size -= file_info['size']
                removed += 1
            except Exception:
                pass
        
        return removed

    def print_stats(self):
        """Print formatted cache statistics."""
        stats = self.get_stats()
        
        print("=" * 70)
        print("CACHE STATISTICS")
        print("=" * 70)
        print(f"Hits: {stats['hits']}")
        print(f"Misses: {stats['misses']}")
        print(f"Hit Rate: {stats['hit_rate']:.1f}%")
        print(f"Cached Items: {stats['total_cached_items']}")
        print(f"Cache Size: {stats['total_size_mb']:.2f} MB")
        print(f"Cache Directory: {stats['cache_directory']}")
        print("=" * 70)


def get_cache_manager():
    return CacheManager()


if __name__ == "__main__":
    print("Cache Manager Self-Test\n")
    cache = CacheManager()

    test_prompt = "Generate an 8-bit adder"
    test_response = {"code": "module adder...", "tokens": 100}

    cached = cache.get(test_prompt, model="test")
    print(f"Initial get (None): {cached is None}")

    cache.set(test_prompt, test_response, tokens_saved=100, model="test")
    print("Cache set ✓")

    cached = cache.get(test_prompt, model="test")
    print(f"Second get (hit): {cached is not None}")

    print(f"Stats: {cache.get_stats()}")
    cache.clear()
    print("Cache cleared ✓")
