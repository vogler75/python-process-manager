import time
import sys

print("Test Program 2 started - simulating 50% CPU usage")
sys.stdout.flush()

count = 0
while True:
    count += 1
    if count % 10 == 0:
        print(f"Test Program 2: Heartbeat {count} (50% CPU target)")
        sys.stdout.flush()

    # Work for 0.5s (busy loop)
    start = time.time()
    while time.time() - start < 0.5:
        # CPU-intensive work
        _ = sum(i**2 for i in range(1000))

    # Sleep for 0.5s (idle)
    time.sleep(0.5)
