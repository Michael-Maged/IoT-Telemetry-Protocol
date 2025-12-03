import socket
import struct
import time

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
    def __init__(self, port=PORT):
        self.port = port
        self.device_state = {}
        self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server.bind(("", port))
        self.server.settimeout(1.0)   # <--- IMPORTANT
        print(f"[BOOT] UDP Telemetry Server running on port {port}\n")

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
                except Exception as e:
                    print(f"[ERROR] {e}")
                    continue

                arrival = int(time.time() * 1000)

                if self.handle_discovery(data, client):
                    continue

                if len(data) < HEADER_SIZE:
                    print(f"[ERROR] Header too small from {client}")
                    continue

                header, payload = self.parse_packet(data)
                if not header:
                    continue

                version, msgType, deviceID, seq, timestamp, flags = header

                # Initialize state if new device
                state = self.device_state.setdefault(deviceID, DeviceState())

                if msgType == HEARTBEAT_MSG:
                    self.handle_heartbeat(deviceID, seq, state)
                    continue

                self.process_packet(deviceID, seq, timestamp, msgType, payload, flags, state, arrival)
                self.check_heartbeats()
        except KeyboardInterrupt:
            print ("\n[SHUTDOWN] Server stopping...")
            self.server.close()

    # ===========================================================
    #                       Packet Handling
    # ===========================================================
    def handle_discovery(self, data, client):
        if data == b"DISCOVER_SERVER":
            print(f"[DISCOVERY] From {client}")
            self.server.sendto(b"SERVER_IP_RESPONSE", client)
            return True
        return False

    def parse_packet(self, data):
        try:
            version_type, deviceID, seq, timestamp, flags = struct.unpack(
                HEADER_FORMAT, data[:HEADER_SIZE]
            )
        except struct.error:
            print("[ERROR] Failed to unpack header")
            return None, None

        version = version_type >> 4
        msgType = version_type & 0x0F
        payload = data[HEADER_SIZE:].decode(FORMAT, errors="ignore").strip()

        return (version, msgType, deviceID, seq, timestamp, flags), payload

    def handle_heartbeat(self, deviceID, seq, state):
        state.update_heartbeat()
        print(f"[HEARTBEAT] From Device {deviceID} | seq={seq}")

    def process_packet(self, deviceID, seq, timestamp, msgType, payload, flags, state, arrival):
        duplicate_flag = state.check_duplicate(seq)
        gap_flag = state.detect_gap(seq,flags)
        out_of_order_flag = state.detect_reordering(timestamp)

        if not out_of_order_flag:
            state.update_last_seen(seq, timestamp)

        readings = []
        if flags & FLAG_BATCH:
            readings = [r.strip() for r in payload.split(";") if r.strip()]
        else:
            if payload:
                readings = [payload]

        self.print_packet_info(
            deviceID, seq, timestamp, msgType, readings, payload, duplicate_flag, gap_flag, out_of_order_flag, arrival, state, flags
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

    def print_packet_info(self, deviceID, seq, timestamp, msgType, readings, payload, duplicate_flag, gap_flag, out_of_order_flag, arrival, state, flags):
        print("===================================")
        print(f"[PACKET] Device {deviceID}")
        print(f"Type     : {self.msgTypeName(msgType)}")
        print(f"SeqNum   : {seq}")
        print(f"Flags    : {flags:08b} {'(BATCH)' if flags & FLAG_BATCH else ''}")

        if duplicate_flag:
            print("DUPLICATE")
        if gap_flag:
            print("GAP DETECTED")
        if out_of_order_flag:
            print("OUT OF ORDER (timestamp)")

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
        return {INIT_MSG: "INIT", DATA_MSG: "DATA", HEARTBEAT_MSG: "HEARTBEAT"}.get(msgType, "UNKNOWN")


# ===========================================================
#                        Entry Point
# ===========================================================
if __name__ == "__main__":
    server = TelemetryServer()
    server.start()
