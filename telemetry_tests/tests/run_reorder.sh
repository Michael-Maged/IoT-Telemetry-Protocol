BASE_DIR="/home/saif/telemetry_tests/results"
mkdir -p "$BASE_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RUN_DIR="$BASE_DIR/reorder_$TIMESTAMP"
mkdir -p "$RUN_DIR"

echo "[REORDER] Results will be stored in: $RUN_DIR"

# --- CLEAN ANY OLD RULES ---
echo "[REORDER] Resetting network state..."
sudo tc qdisc del dev eth0 root 2>/dev/null

# --- APPLY REORDERING ---
echo "[REORDER] Applying 25% reordering with 50% correlation..."
sudo tc qdisc add dev eth0 root netem delay 50ms reorder 25% 50%

echo "[NETEM STATUS]"
tc qdisc show dev eth0

# --- START SERVER ---
echo "[REORDER] Starting Telemetry Server..."
python3 /home/saif/telemetry_tests/project/oop_server.py \
    --csv "$RUN_DIR/logging.csv" \
    > "$RUN_DIR/server.log" 2>&1 &

SERVER_PID=$!
sleep 1

# --- START CLIENT ---
echo "[REORDER] Starting Telemetry Client..."
python3 /home/saif/telemetry_tests/project/oop_client.py \
    --mode single \
    > "$RUN_DIR/client.log" 2>&1 &

CLIENT_PID=$!
sleep 1

# --- RUN TEST ---
echo "[REORDER] Running test for 60 seconds..."
sleep 60

# --- STOP ---
echo "[STOP] Killing server and client..."
kill $SERVER_PID 2>/dev/null
kill $CLIENT_PID 2>/dev/null

echo "[REORDER] Removing netem rules..."
sudo tc qdisc del dev eth0 root 2>/dev/null

echo "[ANALYSIS] Running metrics..."
python3 /home/saif/telemetry_tests/analysis/metrics.py --csv "$RUN_DIR/logging.csv"

echo "============================================"
echo " REORDER TEST COMPLETE!"
echo " CSV:        $RUN_DIR/logging.csv"
echo " Server log: $RUN_DIR/server.log"
echo " Client log: $RUN_DIR/client.log"
echo "============================================"
