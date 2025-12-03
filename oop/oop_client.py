import socket
import struct
import time
import random
import os
import threading

# ==============================
# CONFIGURATION
# ==============================

HEADER_FORMAT = "!B H H I B"      # version+type | deviceID | seqNum | timestamp | flags
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
PORT = 9999
BUFFER = 2048
FORMAT = "utf-8"

BATCH_SIZE = 5
VERSION = 1

MSG_INIT = 0
MSG_DATA = 1
MSG_HEARTBEAT = 2

FLAGS = 0
FLAG_BATCH       = 0x04  # mark packet as batched

HEARTBEAT_INTERVAL = 6.0  # seconds

# ==============================
# UDP CLIENT SOCKET
# ==============================

client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

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
# SIMULATED SENSOR
# ==============================

def virtual_sensor():
    return round(random.uniform(20.0, 30.0), 2)

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

def start():
    print("[CLIENT] Starting...")

    # DISCOVERY
    print("[CLIENT] Searching for server...")
    client.sendto(b"DISCOVER_SERVER", ("255.255.255.255", PORT))
    client.settimeout(8)
    try:
        data, addr = client.recvfrom(BUFFER)
        if data != b"SERVER_IP_RESPONSE":
            print("[CLIENT ERROR] Invalid server response.")
            return
        SERVER_IP = addr[0]
        print(f"[CLIENT] Server found at {SERVER_IP}:{PORT}")
    except socket.timeout:
        print("[CLIENT ERROR] Discovery timed out.")
        return

    ADDRESS = (SERVER_IP, PORT)

    # SEND INIT PACKET
    seqNum = 0
    timestamp = int(time.time() * 1000)
    init_header = pack_header(VERSION, MSG_INIT, deviceID, seqNum, timestamp, 0)
    client.sendto(init_header, ADDRESS)
    print(f"[INIT SENT] deviceID={deviceID}, seq={seqNum}")

    # SEQUENCE COUNTER
    seq_counter = iter(range(seqNum + 1, 0xFFFF))

    # START HEARTBEAT THREAD
    stop_event = threading.Event()
    hb_thread = threading.Thread(target=heartbeat_loop, args=(ADDRESS, stop_event, seq_counter), daemon=True)
    hb_thread.start()

    # SENSOR DATA LOOP
    batch = []
    try:
        while True:
            mode = random.choice(["single" , "batch"])
            if mode == "single":
                value = virtual_sensor()
                timestamp = int(time.time() * 1000)
                payload = f"Reading={value}".encode(FORMAT)
                seqNum = next(seq_counter)
                header = pack_header(VERSION, MSG_DATA, deviceID, seqNum, timestamp, 0x00)
                packet = header + payload
                client.sendto(packet, ADDRESS)
                print(f"[SINGLE SENT] seq={seqNum}, value={value}")
                time.sleep(1)

            else :
                timestamp = int(time.time() * 1000)
                for x in range(BATCH_SIZE):       
                    value = virtual_sensor()
                    batch.append(value)
                
                payload_str = ";".join(str(v) for v in batch)
                payload = payload_str.encode(FORMAT)
                seqNum = next(seq_counter)
                header = pack_header(VERSION, MSG_DATA, deviceID, seqNum, timestamp, FLAG_BATCH)
                packet = header + payload
                client.sendto(packet, ADDRESS)
                print(f"[BATCH SENT] seq={seqNum}, values={batch}")
                batch.clear()
                time.sleep(1)

    except KeyboardInterrupt:
        # SEND ANY REMAINING BATCH
        if batch:
            seqNum = next(seq_counter)
            timestamp = int(time.time() * 1000)
            payload_str = ";".join(str(v) for v in batch)
            payload = payload_str.encode(FORMAT)
            header = pack_header(VERSION, MSG_DATA, deviceID, seqNum, timestamp, FLAG_BATCH)
            client.sendto(header + payload, ADDRESS)
            print(f"[FINAL BATCH SENT] seq={seqNum}, values={batch}")

        print("\n[CLIENT EXIT]")
        stop_event.set()
        hb_thread.join()
    finally:
        client.close()

# ==============================
# MAIN
# ==============================

if __name__ == "__main__":
    start()
