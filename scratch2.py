from datetime import datetime, timedelta, timezone
right_now = datetime.now(timezone.utc)
print(right_now)
other_time = right_now - timedelta(days=1)
print(other_time)