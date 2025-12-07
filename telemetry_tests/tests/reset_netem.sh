#!/bin/bash
sudo tc qdisc del dev eth0 root 2>/dev/null
sudo tc qdisc del dev eth0 ingress 2>/dev/null
sudo tc qdisc del dev eth0 clsact 2>/dev/null
echo "[NETEM] Current qdisc:"
tc qdisc show dev eth0
