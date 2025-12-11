echo "[NETEM] Resetting network state..."
sudo tc qdisc del dev enp0s3 root 2>/dev/null || true
sudo tc qdisc replace dev enp0s3 root pfifo_fast

echo "[NETEM] Applying 20% packet loss..."
sudo tc qdisc add dev enp0s3 root netem loss 20%

tc qdisc show dev enp0s3

RESULTS_DIR="/home/saif/Desktop/networks_project/results/loss_5_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"
echo "[INFO] Saving results to: $RESULTS_DIR"


echo "[SERVER] Starting server..."
python3 /home/saif/Desktop/networks_project/project/oop_server.py \
    --csv "$RESULTS_DIR/logging.csv" \
    > "$RESULTS_DIR/server.log" 2>&1 &
SERVER_PID=$!
sleep 1


echo "[CLIENT] Starting client in SINGLE mode..."
python3 /home/saif/Desktop/networks_project/project/oop_client.py \
    --mode single \
    > "$RESULTS_DIR/client.log" 2>&1 &
CLIENT_PID=$!

echo "[TEST] Running for 60 seconds..."
sleep 60


echo "[STOP] Killing client and server..."
kill $CLIENT_PID 2>/dev/null
kill $SERVER_PID 2>/dev/null
sleep 1


echo "[NETEM] Removing network impairments..."
sudo tc qdisc del dev eth0 root 2>/dev/null


echo "[ANALYSIS] Running metrics for this test..."
python3 /home/saif/Desktop/networks_project/analysis/metrics.py --csv "$RESULTS_DIR/logging.csv"
echo "[ANALYSIS] Completed."
echo "--------------------------------------------------"

echo "========================================"
echo "5% LOSS TEST COMPLETE!"
echo "CSV saved to:     $RESULTS_DIR/logging.csv"
echo "Server log:       $RESULTS_DIR/server.log"
echo "Client log:       $RESULTS_DIR/client.log"
echo "========================================"