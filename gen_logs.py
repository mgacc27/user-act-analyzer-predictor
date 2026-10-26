import csv, random
from datetime import datetime, timedelta
random.seed(42)
types = ["click", "view", "purchase", "session_start"]
start = datetime(2026, 8, 1)
with open("logs.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["event_ts", "user_id", "event_type", "session_id", "session_duration_sec"])
    for d in range(60):
        day = start + timedelta(days=d)
        count = int((100 + 40 * (day.weekday() >= 5)) * random.uniform(0.95, 1.05))
        if d == 40:
            count *= 8
        for i in range(count):
            t = types[i % 4]
            w.writerow([
                (day + timedelta(hours=i % 24, minutes=random.randint(0, 59))).strftime("%Y-%m-%d %H:%M:%S"),
                f"u{random.randint(0, 149)}",
                t,
                f"s{d}-{i}" if t == "session_start" else "",
                random.randint(30, 300) if t == "session_start" else "",
            ])
print("logs.csv готов")