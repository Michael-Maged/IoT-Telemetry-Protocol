#!/bin/bash
set -e

BASE_DIR="$(dirname "$(dirname "$(realpath "$0")")")/results"
mkdir -p "$BASE_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RUN_DIR="$BASE_DIR/baseline_$TIMESTAMP"
mkdir -p "$RUN_DIR"

# Auto-detect network interface
IFACE=$(ip route | grep default | awk '{print $5}' | head -1)
if [ -z "$IFACE" ]; then
    IFACE="eth0"
fi

echo "=========================================="
echo "[BASELINE TEST] Starting..."
echo "=========================================="
echo "[BASELINE] Results will be stored in: $RUN_DIR"
echo "[BASELINE] Using interface: $IFACE"

# Clean any existing rules
sudo tc qdisc del dev $IFACE root 2>/dev/null || true
sleep 0.5

echo "[BASELINE] No network impairments applied (baseline)"

# Start Server
echo "[BASELINE] Starting UDP Telemetry Server on PORT 8576..."
python3 "$(dirname "$(dirname "$(realpath "$0")")")/project/oop_server.py" \
    --csv "$RUN_DIR/logging.csv" \
    > "$RUN_DIR/server.log" 2>&1 &
SERVER_PID=$!

sleep 1

# Start Client
echo "[BASELINE] Starting UDP Telemetry Client in SINGLE mode..."
python3 "$(dirname "$(dirname "$(realpath "$0")")")/project/oop_client.py" \
    --mode single \
    > "$RUN_DIR/client.log" 2>&1 &
CLIENT_PID=$!

echo "[BASELINE] Waiting for server to start..."
sleep 2

echo "[BASELINE] Running baseline test for 60 seconds..."
sleep 60

echo "[BASELINE] Stopping processes..."
kill -9 $CLIENT_PID 2>/dev/null || true
kill -9 $SERVER_PID 2>/dev/null || true
sleep 1

echo "[BASELINE] Test completed!"
echo "=========================================="
echo " Results Summary:"
echo " SERVER LOG : $RUN_DIR/server.log"
echo " CLIENT LOG : $RUN_DIR/client.log"
echo " CSV OUTPUT : $RUN_DIR/logging.csv"
echo "=========================================="

echo "[ANALYSIS] Running metrics for this test..."
python3 "$(dirname "$(dirname "$(realpath "$0")")")/analysis/metrics.py" --csv "$RUN_DIR/logging.csv" 2>/dev/null || echo "[WARNING] Metrics analysis failed"

echo "[BASELINE] ✓ Baseline test completed!"
python3 "$(dirname "$(dirname "$(realpath "$0")")")/analysis/metrics.py" --csv "$RUN_DIR/logging.csv"
echo "[ANALYSIS] Completed."
echo "--------------------------------------------------"
