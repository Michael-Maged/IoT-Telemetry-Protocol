BASE_DIR="/home/saif/telemetry_tests/results"
mkdir -p "$BASE_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RUN_DIR="$BASE_DIR/loss_5pct_$TIMESTAMP"
mkdir -p "$RUN_DIR"

echo "[LOSS TEST] Results will be stored in: $RUN_DIR"

# --- CLEAN ANY OLD RULES ---
sudo tc qdisc del dev eth0 root 2>/dev/null

echo "[LOSS TEST] Applying 5% packet loss..."
sudo tc qdisc add dev eth0 root netem loss 5%

echo "[LOSS TEST] Starting UDP Telemetry Server..."
python3 "/home/saif/telemetry_tests/project/oop_server.py" \
    --csv "$RUN_DIR/logging.csv" \
    > "$RUN_DIR/server.log" 2>&1 &
SERVER_PID=$!
sleep 1

echo "[LOSS TEST] Starting Telemetry Client..."
python3 "/home/saif/telemetry_tests/project/oop_client.py" \
    > "$RUN_DIR/client.log" 2>&1 &
CLIENT_PID=$!
sleep 1

echo "[LOSS TEST] Running 5% packet loss scenario for 60 seconds..."
sleep 60

echo "[LOSS TEST] Stopping processes..."
kill $SERVER_PID 2>/dev/null
kill $CLIENT_PID 2>/dev/null
sleep 1

echo "[LOSS TEST] Removing packet loss rule..."
sudo tc qdisc del dev eth0 root 2>/dev/null

echo "[LOSS TEST] Test completed!"
echo "-------------------------------------------"
echo " SERVER LOG : $RUN_DIR/server.log"
echo " CLIENT LOG : $RUN_DIR/client.log"
echo " CSV OUTPUT : $RUN_DIR/logging.csv"
echo "-------------------------------------------"

echo "[ANALYSIS] Running metrics for this test..."
python3 /home/saif/telemetry_tests/analysis/metrics.py --csv "$RUN_DIR/logging.csv"
echo "[ANALYSIS] Completed."
echo "--------------------------------------------------"
