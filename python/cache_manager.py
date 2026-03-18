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
        self.index_file = self.cache_dir / 'cache_index.json'
        self.index = self._load_index()
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

    def get_stats(self):
        """Get cache statistics."""
        total = len(self.index)
        hits = sum(i.get('hits', 0) for i in self.index.values())
        tokens = sum(i.get('tokens_saved', 0) for i in self.index.values())
        size = sum(f.stat().st_size for f in self.cache_dir.glob("*.json"))
        return {
            'entries': total,
            'hits': hits,
            'tokens_saved': tokens,
            'size_kb': round(size / 1024, 1)
        }


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
