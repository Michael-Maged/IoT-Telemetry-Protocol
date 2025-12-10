#!/bin/bash
set -e

BASE_DIR="$(dirname "$(dirname "$(realpath "$0")")")/results"
mkdir -p "$BASE_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RUN_DIR="$BASE_DIR/reorder_$TIMESTAMP"
mkdir -p "$RUN_DIR"

# Auto-detect network interface
IFACE=$(ip route | grep default | awk '{print $5}' | head -1)
if [ -z "$IFACE" ]; then
    IFACE="eth0"
fi

echo "=========================================="
echo "[REORDER TEST] Starting..."
echo "=========================================="
echo "[REORDER] Results will be stored in: $RUN_DIR"
echo "[REORDER] Using interface: $IFACE"

# Clean any existing rules
sudo tc qdisc del dev $IFACE root 2>/dev/null || true
sleep 0.5

# Apply reordering with delay
echo "[REORDER] Applying 25% reordering with 50% correlation and 50ms delay..."
sudo tc qdisc add dev $IFACE root netem delay 50ms reorder 25% 50%
sleep 0.5

echo "[REORDER] Network rules applied:"
tc qdisc show dev $IFACE

# Start Server
echo "[REORDER] Starting UDP Telemetry Server..."
python3 "$(dirname "$(dirname "$(realpath "$0")")")/project/oop_server.py" \
    --csv "$RUN_DIR/logging.csv" \
    > "$RUN_DIR/server.log" 2>&1 &
SERVER_PID=$!

sleep 1

# Start Client
echo "[REORDER] Starting UDP Telemetry Client in SINGLE mode..."
python3 "$(dirname "$(dirname "$(realpath "$0")")")/project/oop_client.py" \
    --mode single \
    > "$RUN_DIR/client.log" 2>&1 &
CLIENT_PID=$!

echo "[REORDER] Waiting for startup..."
sleep 2

echo "[REORDER] Running test for 60 seconds..."
sleep 60

echo "[REORDER] Stopping processes..."
kill -9 $CLIENT_PID 2>/dev/null || true
kill -9 $SERVER_PID 2>/dev/null || true
sleep 1

echo "[REORDER] Removing network impairments..."
sudo tc qdisc del dev $IFACE root 2>/dev/null || true

echo "[REORDER] Test completed!"
echo "=========================================="
echo " Results Summary:"
echo " SERVER LOG : $RUN_DIR/server.log"
echo " CLIENT LOG : $RUN_DIR/client.log"
echo " CSV OUTPUT : $RUN_DIR/logging.csv"
echo "=========================================="

echo "[ANALYSIS] Running metrics for this test..."
python3 "$(dirname "$(dirname "$(realpath "$0")")")/analysis/metrics.py" --csv "$RUN_DIR/logging.csv" 2>/dev/null || echo "[WARNING] Metrics analysis failed"

echo "[REORDER] ✓ Reorder test completed!"

echo "[ANALYSIS] Running metrics..."
python3 "$(dirname "$(dirname "$(realpath "$0")")")/analysis/metrics.py" --csv "$RUN_DIR/logging.csv"

echo "============================================"
echo " REORDER TEST COMPLETE!"
echo " CSV:        $RUN_DIR/logging.csv"
echo " Server log: $RUN_DIR/server.log"
echo " Client log: $RUN_DIR/client.log"
echo "============================================"
