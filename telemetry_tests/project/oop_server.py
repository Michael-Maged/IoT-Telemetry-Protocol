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


# ===========================================================
# TELEMETRY SERVER CLASS
# ===========================================================
class TelemetryServer:
    def __init__(self, port=PORT, csv_filename=None):
        self.port = port
        self.device_state = {}

        # UDP server
        self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server.bind(("0.0.0.0", self.port))
        print(f"[SERVER] Listening on UDP port {self.port}")


        # CSV SETUP
        if csv_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base = "/home/saif/telemetry_tests/results"
            os.makedirs(base, exist_ok=True)
            csv_filename = os.path.join(base, f"telemetry_log_{timestamp}.csv")

        os.makedirs(os.path.dirname(csv_filename), exist_ok=True)
        self.csv_file = open(csv_filename, "w", newline="")
        self.csv_writer = csv.writer(self.csv_file)

        self.csv_writer.writerow([
            "device_id", "seq", "timestamp", "arrival_time",
            "duplicate_flag", "gap_flag", "payload_size",
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
    # SERVER LOOP
    # =======================================================
    def start(self):
        try:
            while True:
                try:
                    data, client = self.server.recvfrom(BUFFER)
                except socket.timeout:
                    continue  # allow heartbeat updates later

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

                print(f"[RECV] Packet from {client} | type={msgType} seq={seq} flags={flags}")

                payload = data[HEADER_SIZE:].decode(FORMAT, errors="ignore").strip()

                # ---------- INIT ----------
                if msgType == INIT_MSG:
                    # Do NOT force a default mode. Client will send its own.
                    print(f"[INIT] Device {deviceID} connected.")
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
                duplicate = seq in state.received_seqs
                if duplicate:
                    state.duplicate_seqs.add(seq)
                state.received_seqs.add(seq)

                is_batch = 1 if flags & FLAG_BATCH else 0
                payload_size = len(payload.encode(FORMAT))

                # log
                self.csv_writer.writerow([
                    deviceID, seq, timestamp, arrival,
                    int(duplicate), 0,
                    payload_size, is_batch, state.mode
                ])
                print(f"[CSV] Logged packet seq={seq} mode={state.mode} is_batch={is_batch}")
                self.csv_file.flush()

                print(f"[DATA] Dev={deviceID} seq={seq} mode={state.mode} batch={is_batch}")

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