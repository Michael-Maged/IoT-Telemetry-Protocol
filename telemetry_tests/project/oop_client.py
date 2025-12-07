import socket
import struct
import time
import random
import os
import threading
import argparse

# ==============================
# CONFIGURATION
# ==============================

HEADER_FORMAT = "!B H H I B"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
PORT = 9999
BUFFER = 2048
FORMAT = "utf-8"

BATCH_SIZE = 5
VERSION = 1

MSG_INIT = 0
MSG_DATA = 1
MSG_HEARTBEAT = 2
MSG_CONFIG = 3

FLAG_BATCH = 0x04
HEARTBEAT_INTERVAL = 6.0

client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

# Shared mode variable (thread-safe)
current_mode = "batch"
mode_lock = threading.Lock()

# ==============================
# DEVICE ID HANDLING
# ==============================

def get_next_device_id(base_id=1000, counter_file="client_ids.txt"):
    dir_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(dir_path, counter_file)

    if not os.path.exists(file_path):
        last_id = base_id
    else:
        with open(file_path, "r") as f:
            content = f.read().strip()
            last_id = int(content) if content else base_id

    new_id = last_id + 1

    with open(file_path, "w") as f:
        f.write(str(new_id))

    return new_id

deviceID = get_next_device_id()

# ==============================
# PACK HEADER
# ==============================

def pack_header(version, msgType, deviceID, seqNum, timestamp, flags):
    version_type = (version << 4) | (msgType & 0x0F)
    return struct.pack(
        HEADER_FORMAT,
        version_type,
        deviceID & 0xFFFF,
        seqNum & 0xFFFF,
        timestamp & 0xFFFFFFFF,
        flags & 0xFF
    )

# ==============================
# SENSOR SIMULATOR
# ==============================

def virtual_sensor():
    return round(random.uniform(20.0, 30.0), 2)

# ==============================
# RECEIVE THREAD (CONFIG handler)
# ==============================

def config_listener(address):
    global current_mode

    while True:
        try:
            data, _ = client.recvfrom(BUFFER)
            if len(data) < HEADER_SIZE:
                continue

            version_type, devID, seq, ts, flags = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
            msgType = version_type & 0x0F

            if msgType == MSG_CONFIG:
                payload = data[HEADER_SIZE:].decode(FORMAT).strip()

                if payload.startswith("MODE="):
                    new_mode = payload.split("=")[1].lower()

                    with mode_lock:
                        current_mode = new_mode

                    print(f"\n[CONFIG RECEIVED] Server set mode to: {new_mode.upper()}\n")

        except Exception:
            continue

# ==============================
# HEARTBEAT THREAD
# ==============================

def heartbeat_loop(address, stop_event, seq_counter):
    while not stop_event.is_set():
        seqNum = next(seq_counter)
        timestamp = int(time.time() * 1000)

        header = pack_header(VERSION, MSG_HEARTBEAT, deviceID, seqNum, timestamp, 0)
        client.sendto(header, address)

        print(f"[HEARTBEAT SENT] seq={seqNum}")
        time.sleep(HEARTBEAT_INTERVAL)

# ==============================
# MAIN CLIENT LOOP
# ==============================

def start(reporting_interval=1, mode="batch"):
    global current_mode
    current_mode = mode  # initial mode before CONFIG arrives

    print(f"[CLIENT] Starting in mode = {mode}")

    # DISCOVERY
    print("[CLIENT] Searching for server...")
    client.sendto(b"DISCOVER_SERVER", ("255.255.255.255", PORT))
    client.settimeout(8)

    try:
        data, addr = client.recvfrom(BUFFER)
        if data != b"SERVER_IP_RESPONSE":
            print("[CLIENT ERROR] Invalid response from server.")
            return
        SERVER_IP = addr[0]
        print(f"[CLIENT] Server found at {SERVER_IP}:{PORT}")

    except socket.timeout:
        print("[CLIENT ERROR] No server response.")
        return

    ADDRESS = (SERVER_IP, PORT)

    # SEND INIT
    seqNum = 0
    timestamp = int(time.time() * 1000)
    header = pack_header(VERSION, MSG_INIT, deviceID, seqNum, timestamp, 0)
    client.sendto(header, ADDRESS)
    print(f"[INIT SENT] deviceID={deviceID}, seq={seqNum}")

    # SEQ generator
    seq_counter = iter(range(1, 0xFFFF))

    # START CONFIG LISTENER THREAD
    listener_thread = threading.Thread(target=config_listener, args=(ADDRESS,), daemon=True)
    listener_thread.start()

    # START HEARTBEAT THREAD
    stop_event = threading.Event()
    hb_thread = threading.Thread(target=heartbeat_loop, args=(ADDRESS, stop_event, seq_counter), daemon=True)
    hb_thread.start()

    # SENSOR LOOP
    batch = []

    try:
        while True:
            # read current mode safely
            with mode_lock:
                mode_now = current_mode

            if mode_now == "single":
                value = virtual_sensor()
                timestamp = int(time.time() * 1000)
                seqNum = next(seq_counter)
                payload = f"Reading={value}".encode(FORMAT)

                header = pack_header(VERSION, MSG_DATA, deviceID, seqNum, timestamp, 0)
                client.sendto(header + payload, ADDRESS)

                print(f"[SINGLE SENT] seq={seqNum}, value={value}")
                time.sleep(reporting_interval)

            else:  # BATCH MODE
                timestamp = int(time.time() * 1000)

                start_time = time.time()
                for i in range(BATCH_SIZE):
                    batch.append(virtual_sensor())

                seqNum = next(seq_counter)
                payload = ";".join(str(v) for v in batch).encode(FORMAT)

                header = pack_header(VERSION, MSG_DATA, deviceID, seqNum, timestamp, FLAG_BATCH)
                client.sendto(header + payload, ADDRESS)

                print(f"[BATCH SENT] seq={seqNum}, values={batch}")
                batch.clear()
                elapsed = time.time() - start_time
                sleep_time = max(0, reporting_interval - elapsed)
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        stop_event.set()
        hb_thread.join()

        print("\n[CLIENT EXIT]")


if __name__ == "__main__":
    start()

