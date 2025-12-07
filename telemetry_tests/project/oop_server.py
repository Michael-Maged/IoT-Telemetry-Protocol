import socket
import struct
import time
import csv
import os
import threading
from datetime import datetime

# ====== Protocol Constants ======
HEADER_FORMAT = "!B H H I B"     # version+type | deviceID | seqNum | timestamp | flags
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
PORT = 9999
BUFFER = 2048
FORMAT = "utf-8"

# Message types
INIT_MSG = 0
DATA_MSG = 1
HEARTBEAT_MSG = 2
CONFIG_MSG = 3

# Flags
FLAG_BATCH = 0x04

# Heartbeat monitoring
HEARTBEAT_INTERVAL_MS = 6000      # clients send heartbeat every 6s
MAX_MISSED_HEARTBEATS = 5         # disconnect after 5 missed heartbeats

# ===========================================================
#   Device State Class (tracks seqs, gaps, timestamps, HB)
# ===========================================================
class DeviceState:
    def __init__(self):
        self.last_seq = None
        self.last_timestamp = None
        self.received_seqs = set()
        self.duplicate_seqs = set()
        self.gaps = 0
        self.last_heartbeat = None
        self.missed_heartbeats = 0
        self.connected = True
        self.mode = "unknown"

    def update_heartbeat(self):
        self.last_heartbeat = int(time.time() * 1000)
        self.missed_heartbeats = 0
        self.connected = True

    def check_duplicate(self, seq):
        if seq in self.received_seqs:
            self.duplicate_seqs.add(seq)
            return True
        self.received_seqs.add(seq)
        return False

    def detect_gap(self, seq, flags=None):
        BATCH_FLAG = 0x04

        if self.last_seq is None:
            return False

        # If this packet is a batch, DO NOT count the jump as a gap
        if flags is not None and (flags & BATCH_FLAG):
            # Only detect impossible wrap errors
            if seq <= self.last_seq and (self.last_seq - seq) < 30000:
                self.gaps += 1
                return True
            return False

        # Normal gap detection
        expected = (self.last_seq + 1) & 0xFFFF
        if seq == expected:
            return False

        # Real gap
        if seq > self.last_seq:
            self.gaps += (seq - self.last_seq - 1)
        else:  # wrap-around
            self.gaps += ((0xFFFF - self.last_seq) + seq)
        return True

    def detect_reordering(self, timestamp):
        if self.last_timestamp is not None and timestamp < self.last_timestamp:
            return True
        return False

    def update_last_seen(self, seq, timestamp):
        self.last_seq = seq
        self.last_timestamp = timestamp

# ===========================================================
#                   Telemetry Server Class
# ===========================================================
class TelemetryServer:
    def __init__(self, port=PORT, csv_filename=None):
        self.port = port
        self.device_state = {}
        self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server.bind(("", port))
        self.server.settimeout(1.0)   # 1 second timeout for periodic checks
        
        # ===== CSV LOGGING SETUP =====
        # Create unique filename with timestamp if not provided
        # If script did not pass a path, auto-create a unique CSV in /results
        if csv_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_dir = "/home/saif/telemetry_tests/results"
            os.makedirs(base_dir, exist_ok=True)
            csv_filename = os.path.join(base_dir, f"telemetry_log_{timestamp}.csv")

        # Ensure directory exists
        os.makedirs(os.path.dirname(csv_filename), exist_ok=True)

        self.csv_filename = csv_filename
        self.csv_file = open(self.csv_filename, "w", newline="")
        self.csv_writer = csv.writer(self.csv_file)
        
        # Write CSV header with required fields
        self.csv_writer.writerow([
            "device_id", "seq", "timestamp", "arrival_time",
            "duplicate_flag", "gap_flag", "payload_size", "is_batch", "mode"
        ])
        
        print(f"[BOOT] UDP Telemetry Server running on port {port}")
        print(f"[CSV] Logging to {csv_filename}\n")

    # ===========================================================
    #                  SEND CONFIG MESSAGE TO CLIENT
    # ===========================================================
    def send_config(self, deviceID, mode):
        """
        Sends a CONFIG message to a specific device.
        mode must be 'single' or 'batch'
        """

        # Validate mode
        mode = mode.lower()
        if mode not in ("single", "batch"):
            print(f"[CONFIG ERROR] Invalid mode '{mode}'")
            return

        # Check if device exists
        if deviceID not in self.device_state:
            print(f"[CONFIG ERROR] Device {deviceID} not known to server")
            return

        state = self.device_state[deviceID]

        # Check if server has seen the client's address
        if not hasattr(state, "address") or state.address is None:
            print(f"[CONFIG ERROR] No network address stored for Device {deviceID}")
            print("                (Device must send at least 1 packet first)")
            return

        client_addr = state.address

        # Build payload
        payload_str = f"MODE={mode}"
        payload = payload_str.encode(FORMAT)

        # Build header
        seq = 0  # CONFIG does not need sequence tracking
        timestamp = int(time.time() * 1000)
        msgType = CONFIG_MSG
        flags = 0

        version_type = (1 << 4) | (msgType & 0x0F)

        header = struct.pack(
            HEADER_FORMAT,
            version_type,
            deviceID & 0xFFFF,
            seq & 0xFFFF,
            timestamp & 0xFFFFFFFF,
            flags & 0xFF
        )

        packet = header + payload

        # Send it
        self.server.sendto(packet, client_addr)

        print(f"[CONFIG SENT] → Device {deviceID} | MODE={mode.upper()} | Address={client_addr}")


    # ---------------------------
    #   Main server loop
    # ---------------------------
    def start(self):
        try:
            while True:
                try:
                    data, client = self.server.recvfrom(BUFFER)
                except socket.timeout:
                    self.check_heartbeats()
                    continue

                arrival_time = int(time.time() * 1000)

                # Discovery
                if self.handle_discovery(data, client):
                    continue

                if len(data) < HEADER_SIZE:
                    print(f"[ERROR] Packet too small from {client}")
                    continue

                header, payload = self.parse_packet(data)
                if not header:
                    continue

                version, msgType, deviceID, seq, timestamp, flags = header

                state = self.device_state.setdefault(deviceID, DeviceState())
                state.address = client # store (IP, port) for CONFIG responses

                # CONFIG MESSAGE PROCESSING
                if msgType == CONFIG_MSG:
                    self.handle_config(deviceID, payload, state)
                    continue

                # HEARTBEAT
                if msgType == HEARTBEAT_MSG:
                    self.handle_heartbeat(deviceID, seq, state)
                    continue

                # Regular DATA packet
                self.process_packet(deviceID, seq, timestamp, msgType, payload, flags, state, arrival_time)
                self.check_heartbeats()

        except KeyboardInterrupt:
            print("\n[SHUTDOWN] Closing server...")
            self.csv_file.close()
            self.server.close()
            print(f"[CSV] Log saved to {self.csv_filename}")

    # ===========================================================
    #                       Packet Handling
    # ===========================================================
    def handle_discovery(self, data, client):
        if data == b"DISCOVER_SERVER":
            print(f"[DISCOVERY] from {client}")
            self.server.sendto(b"SERVER_IP_RESPONSE", client)
            return True
        return False

    def parse_packet(self, data):
        try:
            version_type, deviceID, seq, timestamp, flags = struct.unpack(
                HEADER_FORMAT, data[:HEADER_SIZE]
            )
        except struct.error:
            print("[ERROR] Could not decode header")
            return None, None

        version = version_type >> 4
        msgType = version_type & 0x0F

        payload = data[HEADER_SIZE:].decode(FORMAT, errors="ignore").strip()

        return (version, msgType, deviceID, seq, timestamp, flags), payload

    # NEW: handle CONFIG messages
    def handle_config(self, deviceID, payload, state):
       
        if payload.startswith("MODE="):
            mode = payload.split("=")[1].lower()
            state.mode = mode
            print(f"[CONFIG] Device {deviceID} set to mode: {mode.upper()}")
        else:
            print(f"[CONFIG] Invalid CONFIG payload from {deviceID}: {payload}")

    # HEARTBEAT packets
    def handle_heartbeat(self, deviceID, seq, state):
        state.update_heartbeat()
        print(f"[HEARTBEAT] Device {deviceID} | seq={seq}")

    # Main DATA packet handling
    def process_packet(self, deviceID, seq, timestamp, msgType, payload, flags, state, arrival):
        duplicate_flag = state.check_duplicate(seq)
        gap_flag = state.detect_gap(seq, flags)
        out_of_order_flag = state.detect_reordering(timestamp)

        if not out_of_order_flag:
            state.update_last_seen(seq, timestamp)

        readings = []
        if flags & FLAG_BATCH:
            readings = [r.strip() for r in payload.split(";") if r.strip()]
        else:
            if payload:
                readings = [payload]

        payload_size = len(payload.encode(FORMAT))
        is_batch = 1 if (flags & FLAG_BATCH) else 0

        # CSV Logging
        self.csv_writer.writerow([
            deviceID, seq, timestamp, arrival,
            int(duplicate_flag), int(gap_flag),
            payload_size, is_batch, state.mode
        ])
        self.csv_file.flush()

        self.print_packet_info(
            deviceID, seq, timestamp, msgType, readings, payload,
            duplicate_flag, gap_flag, out_of_order_flag, arrival, state, flags
        )

    # ===========================================================
    #                     Monitoring / Debug Output
    # ===========================================================
    def check_heartbeats(self):
        now = int(time.time() * 1000)
        for dev, st in self.device_state.items():
            if st.last_heartbeat is None:
                continue
            delta = now - st.last_heartbeat
            if delta > HEARTBEAT_INTERVAL_MS:
                st.missed_heartbeats += delta // HEARTBEAT_INTERVAL_MS
            else:
                st.missed_heartbeats = 0  
            if st.missed_heartbeats >= MAX_MISSED_HEARTBEATS and st.connected:
                st.connected = False
                print(f"[DISCONNECT] Device {dev} missed {st.missed_heartbeats} heartbeats. Marked as disconnected.")

    def print_packet_info(self, deviceID, seq, timestamp, msgType, readings, payload,
                          duplicate_flag, gap_flag, out_of_order_flag, arrival, state, flags):

        print("===================================")
        print(f"[PACKET] Device {deviceID} | Mode: {state.mode.upper()}")
        print(f"Type     : {self.msgTypeName(msgType)}")
        print(f"SeqNum   : {seq}")
        print(f"Flags    : {flags:08b} {'(BATCH)' if flags & FLAG_BATCH else ''}")

        if duplicate_flag: print("DUPLICATE")
        if gap_flag:       print("GAP DETECTED")
        if out_of_order_flag: print("OUT OF ORDER")

        print(f"Sent     : {timestamp} ms")
        print(f"Arrival  : {arrival} ms")
        print(f"Delay    : {arrival - timestamp} ms")

        if readings:
            print(f"Readings : {' | '.join(readings)}")
        else:
            print(f"Payload  : {payload or '(empty)'}")

        print("--- Device Stats ---")
        print(f"Gaps         : {state.gaps}")
        print(f"Duplicates   : {len(state.duplicate_seqs)}")
        print(f"Last HB      : {state.last_heartbeat}")
        print(f"Missed HBs   : {state.missed_heartbeats}")
        print(f"Connected    : {state.connected}")

    def msgTypeName(self, msgType):
        return {
            INIT_MSG: "INIT",
            DATA_MSG: "DATA",
            HEARTBEAT_MSG: "HEARTBEAT",
            CONFIG_MSG: "CONFIG"
        }.get(msgType, "UNKNOWN")


# ===========================================================
#                        Entry Point
# ===========================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=str, default=None,
                        help="Full path to CSV output file")
    args = parser.parse_args()

    server = TelemetryServer(csv_filename=args.csv)
    server.start()
