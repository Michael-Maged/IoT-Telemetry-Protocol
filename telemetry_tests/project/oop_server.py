import socket
import struct
import time
import csv
import os
from datetime import datetime

# ===========================================================
# PROTOCOL CONSTANTS
# ===========================================================
HEADER_FORMAT = "!B H H I B"   # version+type | deviceID | seq | timestamp | flags
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
PORT = 8576
BUFFER = 2048
FORMAT = "utf-8"

# Message Types
INIT_MSG = 0
DATA_MSG = 1
HEARTBEAT_MSG = 2
CONFIG_MSG = 3

# Flags
FLAG_BATCH = 0x04

# Heartbeat monitoring
HEARTBEAT_INTERVAL_MS = 6000
MAX_MISSED_HEARTBEATS = 5


# ===========================================================
# DEVICE STATE
# ===========================================================
class DeviceState:
    def __init__(self):
        self.last_seq = None
        self.last_timestamp = None
        self.last_full_timestamp = None
        self.received_seqs = set()
        self.duplicate_seqs = set()
        self.gaps = 0
        self.mode = "unknown"
        self.address = None

        self.last_heartbeat = None
        self.missed_heartbeats = 0
        self.connected = True

    def update_last(self, seq, timestamp):
        self.last_seq = seq
        self.last_timestamp = timestamp


    def detect_gap(self, seq, flags=None):
        BATCH_FLAG = 0x04

        if self.last_seq is None:
            return False

        # Batch packets: ignore normal jumps
        if flags is not None and (flags & BATCH_FLAG):
            # Only detect wrap-around or backward jumps
            if seq <= self.last_seq and (self.last_seq - seq) < 30000:
                self.gaps += 1
                return True
            return False

        # Normal (single-mode) expected behaviour
        expected = (self.last_seq + 1) & 0xFFFF

        if seq == expected:
            return False

        # Real forward gap
        if seq > self.last_seq:
            self.gaps += (seq - self.last_seq - 1)
        else:
            # wrap-around
            self.gaps += ((0xFFFF - self.last_seq) + seq)

        return True


class TelemetryServer:
    def __init__(self, port=PORT, csv_filename=None):
        self.port = port
        self.device_state = {}
        print("[SERVER] State cleared.")

        # UDP server
        self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server.bind(("0.0.0.0", self.port))
        self.server.settimeout(1.0)
        print(f"[SERVER] Listening on UDP port {self.port}")


        # CSV SETUP
        if csv_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base = "D:/Uni projects/senior 1/networks/Project/IoT-Telemetry-Protocol/telemetry_tests/project"
            os.makedirs(base, exist_ok=True)
            csv_filename = os.path.join(base, f"telemetry_log_{timestamp}.csv")

        os.makedirs(os.path.dirname(csv_filename), exist_ok=True)
        self.csv_file = open(csv_filename, "w", newline="")
        self.csv_writer = csv.writer(self.csv_file)

        self.csv_writer.writerow([
            "device_id", "seq", "timestamp", "arrival_time",
            "duplicate_flag", "gap_flag", "reorder_flag", "payload_size",
            "is_batch", "mode"
        ])

        print(f"[CSV] Logging to {csv_filename}\n")

    # =======================================================
    # SEND CONFIG REPLY TO CLIENT
    # =======================================================
    def send_config(self, deviceID, mode):
        """
        Sends confirmation back to the client.
        Used ONLY as a reply (server does not choose the mode).
        """

        if deviceID not in self.device_state:
            print(f"[CONFIG ERROR] Device {deviceID} not recognized")
            return

        state = self.device_state[deviceID]
        if state.address is None:
            print(f"[CONFIG ERROR] No client address saved for {deviceID}")
            return

        payload = f"MODE={mode}".encode(FORMAT)
        timestamp = int(time.time() * 1000) & 0xFFFFFFFF

        header = struct.pack(
            HEADER_FORMAT,
            (1 << 4) | CONFIG_MSG,        # version + msgType
            deviceID,
            0,                             # seq not needed
            timestamp,
            0
        )

        self.server.sendto(header + payload, state.address)
        print(f"[CONFIG SENT] Device {deviceID} → MODE={mode.upper()}")

    # =======================================================
    # Unwrap the timestamp
    # =======================================================
    def unwrap_timestamp(self, state, wrapped_ts):
        # Convert 32-bit wraparound timestamp into full timeline
        if state.last_full_timestamp is None:
            state.last_full_timestamp = wrapped_ts
            return wrapped_ts

        # If wrapped_ts looks too small (wraparound)
        if wrapped_ts < (state.last_full_timestamp & 0xFFFFFFFF):
            # add 2^32 to move to next wrap window
            state.last_full_timestamp += (1 << 32)

        # update lower 32 bits
        state.last_full_timestamp = (state.last_full_timestamp & ~0xFFFFFFFF) | wrapped_ts

        return state.last_full_timestamp


    # =======================================================
    # SERVER LOOP
    # =======================================================
    def start(self):
        try:
            while True:
                try:
                    data, client = self.server.recvfrom(BUFFER)
                except socket.timeout:
                    continue

                arrival = int(time.time() * 1000)

                # ---------- DISCOVERY ----------
                if data == b"DISCOVER_SERVER":
                    response = f"SERVER_IP_RESPONSE:{self.port}".encode()
                    self.server.sendto(response, client)
                    continue

                if len(data) < HEADER_SIZE:
                    continue

                version_type, deviceID, seq, timestamp, flags = struct.unpack(
                    HEADER_FORMAT, data[:HEADER_SIZE]
                )
                msgType = version_type & 0x0F

                # get or create state
                state = self.device_state.setdefault(deviceID, DeviceState())
                state.address = client
                timestamp_full = self.unwrap_timestamp(state, timestamp)

                print(f"[RECV] Packet from {client} | type={msgType} seq={seq} flags={flags}")

                payload = data[HEADER_SIZE:].decode(FORMAT, errors="ignore").strip()

                # ---------- INIT ----------
                if msgType == INIT_MSG:
                    print(f"[INIT] Device {deviceID} connected.")

                    # RESET STATE FOR THIS DEVICE
                    state.last_seq = seq      # seq=0
                    state.last_timestamp = timestamp
                    state.received_seqs = set([seq])  # reset received seqs
                    state.gaps = 0
                    state.duplicate_seqs = set()

                    continue



                # ---------- CONFIG FROM CLIENT ----------
                if msgType == CONFIG_MSG:
                    if payload.startswith("MODE="):
                        new_mode = payload.split("=")[1].lower()
                        state.mode = new_mode

                        print(f"[CONFIG REQUEST] Device {deviceID} → MODE={new_mode.upper()}")
                        self.send_config(deviceID, new_mode)
                    continue

                # ---------- HEARTBEAT ----------
                if msgType == HEARTBEAT_MSG:
                    state.last_heartbeat = arrival
                    state.missed_heartbeats = 0
                    continue

                # ---------- DATA PACKET ----------
                # 1) Duplicate detection
                duplicate_flag = seq in state.received_seqs
                if duplicate_flag:
                    state.duplicate_seqs.add(seq)
                state.received_seqs.add(seq)

                # 2) REORDERING detection (seq < last_seq)
                if state.last_seq is not None and not duplicate_flag:
                    reordered_flag = seq < state.last_seq
                else:
                    reordered_flag = False

                # 3) GAP DETECTION (only if not duplicate AND not reordered)
                if msgType == DATA_MSG and not duplicate_flag and not reordered_flag:
                    gap_flag = state.detect_gap(seq, flags)
                else:
                    gap_flag = False

                # 4) Update last_seq/timestamp only if not duplicate AND not reordered
                if msgType == DATA_MSG and not duplicate_flag and not reordered_flag:
                    state.update_last(seq, timestamp)

                # 5) Batch flag & payload size
                is_batch = 1 if (flags & FLAG_BATCH) else 0
                payload_size = len(payload.encode(FORMAT))

                # 6) WRITE CSV
                self.csv_writer.writerow([
                    deviceID, seq, timestamp_full, arrival,
                    int(duplicate_flag), int(gap_flag), int(reordered_flag),
                    payload_size, is_batch, state.mode
                ])
                self.csv_file.flush()

                print(f"[DATA] Dev={deviceID} seq={seq} mode={state.mode} REORDER={reordered_flag} is_batch={is_batch} GAP={gap_flag}")

        except KeyboardInterrupt:
            print("\n[SHUTDOWN]")
            self.csv_file.close()
            self.server.close()


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