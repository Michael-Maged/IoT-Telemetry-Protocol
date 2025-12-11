#!/bin/bash

# REORDERING test

INTERFACE="lo"
DURATION=60
RESULTS_DIR="/home/saif/Desktop/IoT-Telemetry-Protocol-Saif/telemetry_tests/results/reorder_$(date +%Y%m%d_%H%M%S)"

mkdir -p "$RESULTS_DIR"

echo "[NETEM] Resetting network state..."
sudo tc qdisc del dev $INTERFACE root 2>/dev/null

echo "[NETEM] Applying packet reordering (30%)..."
sudo tc qdisc add dev $INTERFACE root netem reorder 50% 50%

echo "[INFO] Saving results to: $RESULTS_DIR"

echo "[SERVER] Starting server..."
python3 /home/saif/Desktop/IoT-Telemetry-Protocol-Saif/telemetry_tests/project/oop_server.py \
    --csv "$RESULTS_DIR/logging.csv" \
    > "$RESULTS_DIR/server.log" 2>&1 &
SERVER_PID=$!
sleep 1

echo "[CLIENT] Starting client..."
python3 /home/saif/Desktop/IoT-Telemetry-Protocol-Saif/telemetry_tests/project/oop_client.py \
    --mode single \
    > "$RESULTS_DIR/client.log" 2>&1 &
CLIENT_PID=$!

echo "[TEST] Running for $DURATION seconds..."
sleep $DURATION

echo "[STOP] Stopping processes..."
kill $CLIENT_PID 2>/dev/null
kill $SERVER_PID 2>/dev/null
sleep 1

echo "[NETEM] Removing network impairments..."
sudo tc qdisc del dev $INTERFACE root 2>/dev/null

echo "[ANALYSIS] Running metrics..."
python3 /home/saif/Desktop/IoT-Telemetry-Protocol-Saif/telemetry_tests/analysis/metrics.py \
    --csv "$RESULTS_DIR/logging.csv"

echo "===================================================="
echo "[DONE] REORDER test complete."
echo "===================================================="
