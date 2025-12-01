import socket
import struct
import time
import random
import os


HEADER_FORMAT = "!B H H I B"   # (10 bytes)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
PORT = 9999
BUFFER = 2048
FORMAT = "utf-8"


version = 1
msgInit = 0
msgData = 1
msgHeartBeat = 2
flags = 0


client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)


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



def start():
    print("[CLIENT] Starting...")


    print("[CLIENT] Searching for server...")
    client.sendto(b"DISCOVER_SERVER", ("255.255.255.255", PORT))

    client.settimeout(3)
    try:
        data, addr = client.recvfrom(BUFFER)
        if data == b"SERVER_IP_RESPONSE":
            SERVER_IP = addr[0]
            print(f"[CLIENT] Server found at {SERVER_IP}:{PORT}")
        else:
            print("[CLIENT ERROR] Invalid response.")
            return
    except socket.timeout:
        print("[CLIENT ERROR] No server response.")
        return

    ADDRESS = (SERVER_IP, PORT)

    # Send initialization packet
    seqNum = 0
    timestamp = int(time.time() * 1000)   # ms
    header = pack_header(version, msgInit, deviceID, seqNum, timestamp, flags)
    client.sendto(header, ADDRESS)

    print(f"[INIT SENT] deviceID={deviceID}, seq={seqNum}")

    last_sent = None

    try:
        # Send sensor data packets in a loop
        while True:
            seqNum = (seqNum + 1) & 0xFFFF
            timestamp = int(time.time() * 1000)

            current_sent = virtual_sensor()

            if current_sent == last_sent:
                header = pack_header(version, msgHeartBeat, deviceID, seqNum, timestamp, flags)
                client.sendto(header, ADDRESS)
                print(f"[HEARTBEAT SENT] seq={seqNum}")
            else:
                payload = f"Reading={current_sent}".encode(FORMAT)

                header = pack_header(version, msgData, deviceID, seqNum, timestamp, flags)
                packet = header + payload

                client.sendto(packet, ADDRESS)
                last_sent = current_sent
                print(f"[DATA SENT] seq={seqNum}, Reading={current_sent}")

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[CLIENT EXIT]")
    finally:
        client.close()



def main():
    start()


if __name__ == "__main__":
    main()
