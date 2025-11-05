# Import modules for file handling, networking, binary packing, time, and random numbers
import os
import socket
import struct
import time
import random 

# Define packet header format and networking constants
HEADER_FORMAT = "!B H H I B" 
PORT = 9999 
FORMAT = 'utf-8'
SERVER = None   
ADDRESS = (SERVER, PORT)
BUFFER = 2048
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

# Create UDP socket and enable broadcasting
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

# Define protocol constants
version = 1
msgInit = 0 
msgData = 1
flags = 0 

# Generate and persist unique device ID
def get_next_device_id(base_id=1000, counter_file="client_ids.txt"):
    IpPath = os.path.join(os.path.dirname(__file__), counter_file)
    if not os.path.exists(IpPath):
        last_id = base_id
    else:
        with open(IpPath, "r") as f:
            last_id = int(f.read().strip() or base_id)
    new_id = last_id + 1
    with open(IpPath, "w") as f:
        f.write(str(new_id))
    return new_id

deviceID = get_next_device_id() 

# Pack header fields into binary format
def pack_header(version, msgType, deviceID, seqNum, timestamp, flags):
    version_type = (version << 4) | (msgType & 0x0F)
    return struct.pack(HEADER_FORMAT, version_type, deviceID & 0xFFFF, seqNum & 0xFFFF, timestamp & 0xFFFFFFFF, flags & 0xFF)

# Simulate sensor with random temperature
def virtual_sensor():
    return round(random.uniform(20.0, 30.0), 2)

# Main client logic
def main():
    global SERVER
    # Broadcast to discover server
    print(f"[CLIENT STARTED] Searching for server on port {PORT}...")
    client.sendto(b"DISCOVER_SERVER", ("255.255.255.255", PORT))
    client.settimeout(3)
    try:
        data, addr = client.recvfrom(BUFFER)
        if data == b"SERVER_IP_RESPONSE":
            SERVER = addr[0]
            print(f"[DISCOVERY SUCCESS] Server at {SERVER}:{PORT}")
        else:
            print("[DISCOVERY FAILED] Unexpected response.")
            return
    except socket.timeout:
        print("[DISCOVERY FAILED] No response from server.")
        return

    ADDRESS = (SERVER, PORT)
    print(f"[CLIENT CONNECTED] Sending to {ADDRESS}")

    # Send initialization packet
    seqNum = 0
    timestamp = int(time.time())
    header = pack_header(version, msgInit, deviceID, seqNum, timestamp, flags)
    client.sendto(header, ADDRESS)
    print(f"[INIT SENT] deviceID={deviceID}, seqNum={seqNum}")

    try:
        # Send sensor data packets in a loop
        while True:
            seqNum = (seqNum + 1) & 0xFFFF
            timestamp = int(time.time())
            header = pack_header(version, msgData, deviceID, seqNum, timestamp, flags)
            temp = virtual_sensor()
            payload = f"temp={temp}".encode(FORMAT) 
            packet = header + payload
            client.sendto(packet, ADDRESS)
            print(f"[PACKET SENT] address: {ADDRESS}")
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[CLIENT EXIT]")
    finally:
        client.close()

# Run the client
if __name__ == "__main__":
    main()