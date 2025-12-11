#!/bin/bash

# DELAY + JITTER test

INTERFACE="lo"
DURATION=60
RESULTS_DIR="/home/saif/Desktop/IoT-Telemetry-Protocol-Saif/telemetry_tests/results/delay_jitter_$(date +%Y%m%d_%H%M%S)"

mkdir -p "$RESULTS_DIR"

echo "[NETEM] Resetting network state..."
sudo tc qdisc del dev $INTERFACE root 2>/dev/null

echo "[NETEM] Applying delay 100ms ± 20ms..."
sudo tc qdisc add dev $INTERFACE root netem delay 5000ms 500ms distribution normal

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
echo "[DONE] DELAY+JITTER test complete."
echo "===================================================="
