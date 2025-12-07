#!/bin/bash

echo "[NETNS] Cleaning namespaces and veth links..."

ip netns del ns_client 2>/dev/null
ip netns del ns_server 2>/dev/null
ip link del veth-server 2>/dev/null
ip link del veth-client 2>/dev/null

echo "[NETNS] Cleanup complete."
