import time
import sys

print("Test Program 3 started - simulating 90% CPU usage")
sys.stdout.flush()

count = 0
while True:
    count += 1
    if count % 10 == 0:
        print(f"Test Program 3: Heartbeat {count} (90% CPU target)")
        sys.stdout.flush()

    # Work for 0.9s (busy loop)
    start = time.time()
    while time.time() - start < 0.9:
        # CPU-intensive work
        _ = sum(i**2 for i in range(1000))

    # Sleep for 0.1s (idle)
    time.sleep(0.1)
