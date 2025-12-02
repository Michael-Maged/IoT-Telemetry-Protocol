# Import modules for networking, binary packing, CSV logging, file operations, and argument parsing
import socket
import struct
import time
import csv
import os
import argparse

# Define packet header format and constants
HEADER_FORMAT = "!B H H I B"  # 10 Bytes
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
PORT = 9999
SERVER_IP = socket.gethostbyname(socket.gethostname())
ADDRESS = (SERVER_IP, PORT)
FORMAT = 'utf-8'
BUFFER = 2048
LOG_PATH = "telemetry_log.csv"
AUTO_LOG_PATH = "auto_script.csv"
COUNTER_FILE = os.path.join(os.path.dirname(__file__), "client_ids.txt")

# Message type constants
initMsg = 0
dataMsg = 1

# Reset client ID counter file
def reset_device_id_counter():
    try:
        os.remove(COUNTER_FILE)
        print("[SERVER] client_ids.txt reset")
    except FileNotFoundError:
        pass

# Log packet data to CSV files
def write_csv(log_path, deviceID, seqNum, timestamp, arrivalTime, msgType, message, test_ids=None):
    file_exists = os.path.exists(log_path)
    with open(log_path, mode='a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(['DeviceID', 'SeqNum', 'Timestamp', 'ArrivalTime', 'MsgType', 'Message', 'Delay'])
        writer.writerow([deviceID, seqNum, timestamp, arrivalTime, msgType, message, (arrivalTime - timestamp)])
    if test_ids and deviceID in test_ids:
        auto_file_exists = os.path.exists(AUTO_LOG_PATH)
        with open(AUTO_LOG_PATH, mode='a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            if not auto_file_exists:
                writer.writerow(['DeviceID', 'SeqNum', 'Timestamp', 'ArrivalTime', 'MsgType', 'Message', 'Delay'])
            writer.writerow([deviceID, seqNum, timestamp, arrivalTime, msgType, message, (arrivalTime - timestamp)])

# Create and bind UDP server socket
server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind(("", PORT))

# Main server function
def start(test_ids=None):
    print("[SERVER READY] Waiting for messages...")
    print(f"Server IP: {SERVER_IP}, Host: {socket.gethostname()}")
    if test_ids:
        print(f"[SERVER] Logging test messages for device IDs {test_ids} to {AUTO_LOG_PATH}")

    while True:
        data, client_addr = server.recvfrom(BUFFER)
        arrivalTime = time.time()
        # Handle server discovery request
        if data == b"DISCOVER_SERVER":
            print(f"[DISCOVERY] request from {client_addr}")
            server.sendto(b"SERVER_IP_RESPONSE", client_addr)
            continue

        # Validate packet size
        if len(data) < HEADER_SIZE:
            print(f"[ERROR] Packet too short from {client_addr}")
            continue

        # Unpack header
        version_type, deviceID, seqNum, timestamp, flags = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
        version = version_type >> 4
        msgType = version_type & 0x0F
        message = data[HEADER_SIZE:].decode(FORMAT, errors="ignore") if data[HEADER_SIZE:] else ""

        # Log packet details
        print("==========================================")
        print(f"[{'DATA' if msgType == dataMsg else 'INIT' if msgType == initMsg else f'UNKNOWN type={msgType}'}] from {client_addr}")
        print(f"version={version}, deviceID={deviceID}, seqNum={seqNum}, timestamp={timestamp}, flags={flags}")
        if message:
            print(f"Message: {message}")
        print(f"Arrival time: {arrivalTime}")
        print("==========================================")

        # Write to CSV logs
        write_csv(LOG_PATH, deviceID, seqNum, timestamp, arrivalTime, msgType, message, test_ids)

# Parse arguments and start server
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-ids", default="", help="Comma-separated device IDs for test logging")
    args = parser.parse_args()
    test_ids = [int(id) for id in args.test_ids.split(",") if id.strip().isdigit()] if args.test_ids else None
    reset_device_id_counter()
    print(f"[SERVER] Starting on port {PORT}, logging to {LOG_PATH}")
    start(test_ids)