import socket
import struct
import time
import random
import os
import threading
import argparse
from itertools import count

data_seq = count(1)       # for DATA packets only
hb_seq = count(50000)     # heartbeat in separate range to avoid conflict
cfg_seq = count(60000)    # config replies


# ==============================
# CONFIGURATION
# ==============================

HEADER_FORMAT = "!B H H I B"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
PORT = 8576                     # Server port
BUFFER = 2048
FORMAT = "utf-8"

BATCH_SIZE = 5
VERSION = 1

MSG_INIT = 0
MSG_DATA = 1
MSG_HEARTBEAT = 2
MSG_CONFIG = 3

FLAG_BATCH = 0x04
HEARTBEAT_INTERVAL = 5.0

# --- UDP CLIENT SETUP ---
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

# IMPORTANT FIX:
# Do NOT bind to port 9999 (server port). Let OS choose a free one.
client.bind(("", 0))
print(f"[CLIENT] Using local UDP port {client.getsockname()[1]}", flush=True)

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
# RECEIVE THREAD - CONFIG Handler
# ==============================

def config_listener():
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
                        if new_mode != current_mode:
                            current_mode = new_mode
                            print(f"\n[CONFIG RECEIVED] Server set mode to: {new_mode.upper()}\n", flush=True)

        except Exception:
            continue

# ==============================
# HEARTBEAT THREAD
# ==============================

def heartbeat_loop(address, stop_event, last_data_time):
    while not stop_event.is_set():
        time.sleep(1)  # Check every second
        
        # Send heartbeat only if no data sent for 5+ seconds
        if time.time() - last_data_time[0] >= HEARTBEAT_INTERVAL:
            seqNum = next(hb_seq)
            timestamp = int(time.time() * 1000) & 0xFFFFFFFF

            header = pack_header(VERSION, MSG_HEARTBEAT, deviceID, seqNum, timestamp, 0)
            client.sendto(header, address)

            print(f"[HEARTBEAT SENT] seq={seqNum}", flush=True)
            last_data_time[0] = time.time()  # Reset timer

# ==============================
# MAIN CLIENT LOOP
# ==============================

def start(reporting_interval=1, mode="batch"):
    global current_mode
    current_mode = mode

    print(f"[CLIENT] Starting in mode = {mode}", flush=True)

    # ---------- FIXED: DIRECT CONNECTION ----------
    SERVER_IP = "172.25.25.147"    # your laptop IP
    SERVER_PORT = 8576             # your fixed server port
    ADDRESS = (SERVER_IP, SERVER_PORT)

    print(f"[CLIENT] Connecting directly to {SERVER_IP}:{SERVER_PORT}", flush=True)



    # ---------- SEND INIT ----------
    seqNum = 0
    timestamp = int(time.time() * 1000) & 0xFFFFFFFF
    header = pack_header(VERSION, MSG_INIT, deviceID, seqNum, timestamp, 0)
    client.sendto(header, ADDRESS)

    print(f"[INIT SENT] deviceID={deviceID}, seq={seqNum}", flush=True)

    # SEQ generator
    seq_counter = iter(range(1, 0xFFFF))

    # ---------- SEND INITIAL CONFIG ----------
    timestamp = int(time.time() * 1000) & 0xFFFFFFFF
    seq_cfg = next(cfg_seq)
    payload_str = f"MODE={current_mode}"  # or mode, same value
    payload = payload_str.encode(FORMAT)

    header = pack_header(VERSION, MSG_CONFIG, deviceID, seq_cfg, timestamp, 0)
    client.sendto(header + payload, ADDRESS)
    print(f"[CLIENT] Sent initial CONFIG: MODE={current_mode.upper()}", flush=True)

    # START CONFIG LISTENER
    threading.Thread(target=config_listener, daemon=True).start()

    # START HEARTBEAT
    stop_event = threading.Event()
    last_data_time = [time.time()]  # Mutable reference for thread sharing
    hb_thread = threading.Thread(target=heartbeat_loop, args=(ADDRESS, stop_event, last_data_time), daemon=True)
    hb_thread.start()

    # SENSOR LOOP
    batch = []

    try:
        while True:
            with mode_lock:
                mode_now = current_mode

            if mode_now == "single":
                value = virtual_sensor()
                timestamp = int(time.time() * 1000) & 0xFFFFFFFF
                seq = next(data_seq)
                payload = f"Reading={value}".encode(FORMAT)

                header = pack_header(VERSION, MSG_DATA, deviceID, seq, timestamp, 0)
                client.sendto(header + payload, ADDRESS)
                print(f"[CLIENT SINGLE] seq={seq} value={value}", flush=True)
                last_data_time[0] = time.time()  # Update last data time

                time.sleep(reporting_interval)

            else:  # BATCH MODE
                timestamp = int(time.time() * 1000) & 0xFFFFFFFF

                for _ in range(BATCH_SIZE):
                    batch.append(virtual_sensor())

                seq = next(seq_counter)
                payload = ";".join(str(v) for v in batch).encode(FORMAT)

                header = pack_header(VERSION, MSG_DATA, deviceID, seq, timestamp, FLAG_BATCH)
                client.sendto(header + payload, ADDRESS)

                print(f"[CLIENT BATCH] seq={seq} values={batch}", flush=True)
                last_data_time[0] = time.time()  # Update last data time

                batch.clear()
                time.sleep(reporting_interval)

    except KeyboardInterrupt:
        stop_event.set()
        hb_thread.join()
        print("\n[CLIENT EXIT]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, default="batch",
                        choices=["batch", "single"],
                        help="Initial sending mode for the client")
    parser.add_argument("--interval", type=float, default=1.0,
                        help="Reporting interval in seconds")
    args = parser.parse_args()

    start(reporting_interval=args.interval, mode=args.mode)
