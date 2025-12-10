#!/bin/bash
set -e

BASE_DIR="$(dirname "$(dirname "$(realpath "$0")")")/results"
mkdir -p "$BASE_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RUN_DIR="$BASE_DIR/delay_jitter_$TIMESTAMP"
mkdir -p "$RUN_DIR"

# Auto-detect network interface
IFACE=$(ip route | grep default | awk '{print $5}' | head -1)
if [ -z "$IFACE" ]; then
    IFACE="eth0"
fi

echo "=========================================="
echo "[DELAY/JITTER TEST] Starting..."
echo "=========================================="
echo "[DELAY/JITTER] Results will be stored in: $RUN_DIR"
echo "[DELAY/JITTER] Using interface: $IFACE"

# Clean any existing rules
sudo tc qdisc del dev $IFACE root 2>/dev/null || true
sleep 0.5

echo "[DELAY/JITTER] Applying 100ms delay ±10ms jitter..."
sudo tc qdisc add dev $IFACE root netem delay 100ms 10ms distribution normal
sleep 0.5

echo "[DELAY/JITTER] Network rules applied:"
tc qdisc show dev $IFACE

# Start Server
echo "[DELAY/JITTER] Starting UDP Telemetry Server..."
python3 "$(dirname "$(dirname "$(realpath "$0")")")/project/oop_server.py" \
    --csv "$RUN_DIR/logging.csv" \
    > "$RUN_DIR/server.log" 2>&1 &
SERVER_PID=$!

sleep 1

# Start Client
echo "[DELAY/JITTER] Starting UDP Telemetry Client..."
python3 "$(dirname "$(dirname "$(realpath "$0")")")/project/oop_client.py" \
    --mode single \
    > "$RUN_DIR/client.log" 2>&1 &
CLIENT_PID=$!

echo "[DELAY/JITTER] Waiting for startup..."
sleep 2

echo "[DELAY/JITTER] Running test for 60 seconds..."
sleep 60

echo "[DELAY/JITTER] Stopping processes..."
kill -9 $CLIENT_PID 2>/dev/null || true
kill -9 $SERVER_PID 2>/dev/null || true
sleep 1

echo "[DELAY/JITTER] Removing network impairments..."
sudo tc qdisc del dev $IFACE root 2>/dev/null || true

echo "[DELAY/JITTER] Test completed!"
echo "=========================================="
echo " Results Summary:"
echo " SERVER LOG : $RUN_DIR/server.log"
echo " CLIENT LOG : $RUN_DIR/client.log"
echo " CSV OUTPUT : $RUN_DIR/logging.csv"
echo "=========================================="

echo "[ANALYSIS] Running metrics for this test..."
python3 "$(dirname "$(dirname "$(realpath "$0")")")/analysis/metrics.py" --csv "$RUN_DIR/logging.csv" 2>/dev/null || echo "[WARNING] Metrics analysis failed"

echo "[DELAY/JITTER] ✓ Delay/Jitter test completed!"
