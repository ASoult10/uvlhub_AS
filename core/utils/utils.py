import random
from datetime import datetime, timezone, timedelta


# Generate a random datetime within a range
def random_datetime(start, end):
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)


# Example usage in your seeder:
created_at = random_datetime(
    datetime(2020, 1, 1, tzinfo=timezone.utc),
    datetime.now(timezone.utc)
)
