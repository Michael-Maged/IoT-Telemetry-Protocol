BASE_DIR="/home/saif/Desktop/networks_project/results"
mkdir -p "$BASE_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RUN_DIR="$BASE_DIR/baseline_$TIMESTAMP"
mkdir -p "$RUN_DIR"

echo "[BASELINE] Results will be stored in: $RUN_DIR"

sudo tc qdisc del dev enp0s3 root 2>/dev/null

# Start Server
echo "[BASELINE] Starting UDP Telemetry Server on PORT 8576..."
python3 /home/saif/Desktop/networks_project/project/oop_server.py \
    --csv "$RUN_DIR/logging.csv" \
    > "$RUN_DIR/server.log" 2>&1 &
SERVER_PID=$!

sleep 1

# Start Client
echo "[BASELINE] Starting UDP Telemetry Client..."
python3 /home/saif/Desktop/networks_project/project/oop_client.py \
    --mode single \
    > "$RUN_DIR/client.log" 2>&1 &
CLIENT_PID=$!

echo "[BASELINE] Waiting for server to start..."
while ! nc -zu localhost 8576 2>/dev/null; do
    sleep 0.2
done


echo "[BASELINE] Running baseline test for 60 seconds..."
sleep 60

echo "[BASELINE] Stopping processes..."
kill -9 $SERVER_PID 2>/dev/null
kill $CLIENT_PID 2>/dev/null
sleep 1

sudo tc qdisc del dev eth0 root 2>/dev/null

echo "[BASELINE] Baseline test completed!"
echo "-------------------------------------------"
echo " SERVER LOG : $RUN_DIR/server.log"
echo " CLIENT LOG : $RUN_DIR/client.log"
echo " CSV OUTPUT : $RUN_DIR/logging.csv"
echo "-------------------------------------------"

echo "[ANALYSIS] Running metrics for this test..."
python3 /home/saif/Desktop/networks_project/analysis/metrics.py --csv "$RUN_DIR/logging.csv"
echo "[ANALYSIS] Completed."
echo "--------------------------------------------------"
