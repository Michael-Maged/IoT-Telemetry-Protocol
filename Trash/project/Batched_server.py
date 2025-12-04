import socket
import struct
import time

# Header format
HEADER_FORMAT = "!B H H I B"      # 1+2+2+4+1 = 10 bytes
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
PORT = 9999
BUFFER = 2048
FORMAT = "utf-8"

# Message types
initMsg = 0
dataMsg = 1
msgHeartBeat = 2

device_state = {}

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind(("", PORT))


def start():
    print("[SERVER READY] Waiting for messages on port 9999...\n")

    while True:
        data, client_addr = server.recvfrom(BUFFER)
        arrivalTime = int(time.time() * 1000)

        # === Discovery ===
        if data == b"DISCOVER_SERVER":
            print(f"[DISCOVERY] Request from {client_addr}")
            server.sendto(b"SERVER_IP_RESPONSE", client_addr)
            continue

        if len(data) < HEADER_SIZE:
            print(f"[ERROR] Packet too small from {client_addr}")
            continue

        # === Unpack header ===
        version_type, deviceID, seqNum, timestamp, flags = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
        version = version_type >> 4
        msgType = version_type & 0x0F
        payload = data[HEADER_SIZE:].decode(FORMAT, errors="ignore").strip()

        # === Parse batched readings ===
        readings = [r.strip() for r in payload.split(';') if r.strip()] if payload else []

        # === Initialize device state (FIRST TIME ONLY) ===
        if deviceID not in device_state:
            device_state[deviceID] = {
                "last_seq": None,
                "last_timestamp": None,      #  for reordering
                "received_seqs": set(),
                "duplicate_seqs": set(),
                "gaps": 0,
                "last_heartbeat": None
            }

        state = device_state[deviceID]

      
        if msgType == msgHeartBeat:
            state["last_heartbeat"] = arrivalTime
            print("====================================")
            print(f"[PACKET] from {client_addr[0]}:{client_addr[1]}")
            print(f"DeviceID : {deviceID}")
            print(f"Type     : HEARTBEAT")
            print(f"SeqNum   : {seqNum}")
            print(f"Arrival  : {arrivalTime} ms")
            print("====================================")
            continue

        # === Duplicate detection ===
        duplicate_flag = seqNum in state["received_seqs"]
        if duplicate_flag:
            state["duplicate_seqs"].add(seqNum)
        else:
            state["received_seqs"].add(seqNum)

        # === Gap detection ===
        gap_flag = False
        if state["last_seq"] is not None:
            expected = (state["last_seq"] + 1) & 0xFFFF
            if seqNum != expected:
                gap_flag = True
                if seqNum > state["last_seq"]:
                    state["gaps"] += (seqNum - state["last_seq"] - 1)
                else:  # wrap-around
                    state["gaps"] += ((0xFFFF - state["last_seq"]) + seqNum)

        # === Reordering detection (by timestamp) ===
        out_of_order = False
        if state["last_timestamp"] is not None and timestamp < state["last_timestamp"]:
            out_of_order = True

        # Only update "last seen" if this packet is newer by timestamp
        if not out_of_order:
            state["last_seq"] = seqNum
            state["last_timestamp"] = timestamp

        print("====================================")
        print(f"[PACKET]  from {client_addr[0]}:{client_addr[1]}")
        print(f"DeviceID : {deviceID}")
        print(f"Type     : {'INIT' if msgType == initMsg else 'DATA' if msgType == dataMsg else 'HEARTBEAT'}")
        print(f"SeqNum   : {seqNum}")
        print(f"Sent     : {timestamp} ms")
        print(f"Arrival  : {arrivalTime} ms")
        print(f"Delay    : {arrivalTime - timestamp} ms")

        if readings:
            print(f"Readings : {' | '.join(readings)}")
        else:
            print(f"Payload  : {payload if payload else '(no payload)'}")

        if duplicate_flag:
            print("DUPLICATE packet")
        if gap_flag:
            print("GAP DETECTED")
        if out_of_order:
            print("OUT OF ORDER (timestamp)")

        print("--- Device Stats ---")
        print(f"Gaps         : {state['gaps']}")
        print(f"Duplicates   : {len(state['duplicate_seqs'])}")
        print(f"Last HB      : {state['last_heartbeat']}")
        print("====================================")

        now_ms = int(time.time() * 1000)
        for dev_id, dev_state in device_state.items():
            hb = dev_state['last_heartbeat']
            if hb and (now_ms - hb) > 30000:
                print(f"[WARNING] Device {dev_id} missed heartbeat for >30s!")


def main():
    print("[BOOT]Starting UDP Telemetry Server...")
    start()


if __name__ == "__main__":
    main()