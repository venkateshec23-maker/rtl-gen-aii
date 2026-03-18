"""
Token Usage Tracker for RTL-Gen AII.
Monitors API usage and estimates costs.
"""

import json
from pathlib import Path
from datetime import datetime

from python.config import TOKEN_COST_PER_MILLION, LOGS_DIR


class TokenTracker:
    """Track token usage and costs across API calls."""

    def __init__(self, log_file=None):
        self.log_file = Path(log_file) if log_file else (LOGS_DIR / 'token_usage.json')
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.usage_data = self._load()

    def _load(self):
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {'calls': [], 'daily_totals': {}}

    def _save(self):
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.usage_data, f, indent=2)
        except IOError:
            pass

    def log_usage(self, model, prompt_tokens, completion_tokens,
                  success=True, error=None):
        """Log token usage for an API call."""
        total = prompt_tokens + completion_tokens
        cpm = TOKEN_COST_PER_MILLION.get(model, TOKEN_COST_PER_MILLION['default'])
        cost = (total / 1_000_000) * cpm

        entry = {
            'timestamp': datetime.now().isoformat(),
            'model': model,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total,
            'cost': round(cost, 6),
            'success': success,
            'error': error
        }
        self.usage_data['calls'].append(entry)

        date = entry['timestamp'][:10]
        if date not in self.usage_data['daily_totals']:
            self.usage_data['daily_totals'][date] = {
                'total_tokens': 0, 'total_cost': 0.0,
                'successful': 0, 'failed': 0
            }
        daily = self.usage_data['daily_totals'][date]
        daily['total_tokens'] += total
        daily['total_cost'] += cost
        daily['successful' if success else 'failed'] += 1
        self._save()

    def get_daily_stats(self, date=None):
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        return self.usage_data['daily_totals'].get(date, {
            'total_tokens': 0, 'total_cost': 0.0,
            'successful': 0, 'failed': 0
        })

    def get_total_stats(self):
        calls = self.usage_data['calls']
        if not calls:
            return {'total_calls': 0, 'total_tokens': 0, 'total_cost': 0}
        return {
            'total_calls': len(calls),
            'total_tokens': sum(c['total_tokens'] for c in calls),
            'total_cost': round(sum(c['cost'] for c in calls), 4),
            'successful': sum(1 for c in calls if c['success']),
            'failed': sum(1 for c in calls if not c['success'])
        }

    def reset(self):
        self.usage_data = {'calls': [], 'daily_totals': {}}
        self._save()


def get_token_tracker():
    return TokenTracker()


if __name__ == "__main__":
    print("Token Tracker Self-Test\n")
    tracker = TokenTracker()
    tracker.log_usage("deepseek-ai/deepseek-v3.2", 1000, 500)
    tracker.log_usage("deepseek-ai/deepseek-v3.2", 2000, 800)
    tracker.log_usage("deepseek-ai/deepseek-v3.2", 500, 200, False, "Rate limit")

    print(f"Daily: {tracker.get_daily_stats()}")
    print(f"Total: {tracker.get_total_stats()}")
    print("Self-test complete ✓")
