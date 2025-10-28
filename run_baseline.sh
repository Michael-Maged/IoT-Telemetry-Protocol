#!/usr/bin/env bash
# run_baseline.sh -- runs server + 3 clients for baseline local test (60s, 1s interval)
set -e
OUTDIR=baseline_$(date +"%Y%m%d_%H%M%S")
mkdir -p "$OUTDIR"
echo "Output -> $OUTDIR"

# start tcpdump to capture loopback (requires sudo)
PCAP="$OUTDIR/baseline.pcap"
echo "Starting tcpdump (will capture UDP port 50000 to $PCAP). Press Ctrl-C to abort."
sudo timeout 70 tcpdump -i lo udp port 50000 -w "$PCAP" &
TCPDUMP_PID=$!

# start server (redirect logs)
python3 server.py > "$OUTDIR/server.log" 2>&1 &
SERVER_PID=$!
sleep 0.5

# start 3 clients (device ids 1,2,3)
python3 client.py --device_id 1 --interval 1 --duration 60 > "$OUTDIR/client1.log" 2>&1 &
python3 client.py --device_id 2 --interval 1 --duration 60 > "$OUTDIR/client2.log" 2>&1 &
python3 client.py --device_id 3 --interval 1 --duration 60 > "$OUTDIR/client3.log" 2>&1 &

# wait for clients to finish
wait

# give server a second to flush
sleep 1
# stop tcpdump
sudo kill $TCPDUMP_PID || true

# copy CSV result if created
cp received.csv "$OUTDIR"/received.csv || true

# kill server
kill $SERVER_PID || true

echo "Baseline run complete. Files in $OUTDIR"
