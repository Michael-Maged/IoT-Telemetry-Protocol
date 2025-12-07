IFACE="eth0"
DURATION=60
LOG_DIR="baseline_$(date +%Y%m%d_%H%M%S)"


echo "[BASELINE] creating log directory: $LOG_DIR"
mkdir -p "$LOG_DIR"

echo "[BASELINE] making sure the netem settings are reset to normal"
sudo tc qdisc del dev $IFACE root 2>/dev/null || true

echo "[BASELINE] Starting UDP Telemetry Server..."
python3 "/mnt/d/Uni projects/senior 1/networks/Project/IoT-Telemetry-Protocol/oop/oop_server.py" > "$LOG_DIR/server.log" 2>&1 & > "$LOG_DIR/server.log" 2>&1 &
SERVER_PID=$!

sleep 2

echo "[BASELINE] Starting Telemetry Client..."
python3 "/mnt/d/Uni projects/senior 1/networks/Project/IoT-Telemetry-Protocol/oop/oop_client.py" > "$LOG_DIR/client.log" 2>&1 &
CLIENT_PID=$!

echo "[BASELINE] Running baseline test for $DURATION seconds..."
sleep $DURATION

echo "[BASELINE] Stopping processes..."
kill $CLIENT_PID 2>/dev/null || true
kill $SERVER_PID 2>/dev/null || true

echo "[BASELINE] Test complete!"
echo "-------------------------------------------"
echo " Logs saved in:  $LOG_DIR/"
echo " CSV output:     check telemetry CSV file created by server"
echo "-------------------------------------------"
