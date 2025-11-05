import os
import socket
import struct
import time
import random 

HEADER_FORMAT = "!B H H I B" 
PORT = 9999 #ay rakam enta damen en m7d4 48al 3leeh
FORMAT = 'utf-8'
SERVER = None   # auto detect later
ADDRESS = (SERVER, PORT)
BUFFER = 2048
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)



version = 1 # e7na kda kda 3mleen version wa7ed bs mn elprotocol ely hwa version 1 (0.5 byte)
msgInit= 0 # elmessage type ely btetb3et awel ma elclient bta3ak yconnect lelserver (0.5 byte)
msgData = 1 # elmessage type ely btetb3et t3rf elserver en ely gylo da data (0.5 byte)
flags = 0 # m4 3aref eldoctor 3ayez mnena eh seka w do8ry b2a bs hwa taleb flag (1 byte)

#3ndk eltimestamp da (4 bytes) w el seqNum deeh (2 bytes) fa kda kolo 10 bytes

def get_next_device_id(base_id = 1000, counter_file="client_ids.txt"):

    IpPath = os.path.join(os.path.dirname(__file__), counter_file)

    # if file doesn't exist → start fresh (reset)
    if not os.path.exists(IpPath):
        last_id = base_id
    else:
        with open(IpPath, "r") as f:
            try:
                last_id = int(f.read().strip() or base_id)
            except ValueError:
                last_id = base_id

    new_id = last_id + 1
    with open(IpPath, "w") as f:
        f.write(str(new_id))

    return new_id

deviceID = get_next_device_id() #3mlna base id kol client y connect y increment b 1 


def pack_header(version, msgType, deviceID, seqNum, timestamp, flags):
    version_type = (version << 4) | (msgType & 0x0F)
    return struct.pack(HEADER_FORMAT, version_type, deviceID & 0xFFFF, seqNum & 0xFFFF, timestamp & 0xFFFFFFFF, flags & 0xFF)


def virtual_sensor():
    # eb3t ay sensor reading ya 3m mtwg34 dema8na
    random_reading = round(random.uniform(20.0, 30.0), 2)
    return random_reading


def main():
    global SERVER
    # Broadcast to discover server
    print(f"[CLIENT STARTED] Searching for server on port {PORT}...\n")
    client.sendto(b"DISCOVER_SERVER", ("255.255.255.255", PORT))
    client.settimeout(3)
    try:
        data, addr = client.recvfrom(BUFFER)
        if data == b"SERVER_IP_RESPONSE":
            SERVER = addr[0]
            print(f"[DISCOVERY SUCCESS] Server found at {SERVER}:{PORT}")
        else:
            print("[DISCOVERY FAILED] Unexpected response.")
            return
    except socket.timeout:
        print("[DISCOVERY FAILED] No response from server.")
        return

    ADDRESS = (SERVER, PORT)
    print(f"[CLIENT CONNECTED] Sending to {ADDRESS}\n")


    seqNum = 0
    timestamp = int(time.time())
    header = pack_header(version, msgInit, deviceID, seqNum, timestamp, flags)
    client.sendto(header, ADDRESS)
    print(f"[INIT SENT] deviceID={deviceID}, seqNum={seqNum}, timestamp={timestamp}")
    try:
        while True:
            seqNum = (seqNum + 1) & 0xFFFF
            timestamp = int(time.time())

            header = pack_header(version, msgData, deviceID, seqNum, timestamp, flags)

            
            temp = virtual_sensor()
            

            payload = f"temp={temp}".encode(FORMAT) # elpayload da hwa ely hy4eel elmessage bt3tk b3d kda w hyb2a feeha 4o8l elbatch azon

            packet = header + payload
            client.sendto(packet, ADDRESS)
            print(f"[PACKET SENT] address: {ADDRESS}")

            time.sleep(1) # delay sanya

    except KeyboardInterrupt:
        print("\n[CLIENT EXIT]")
    finally:
        client.close()


if __name__ == "__main__":
    main()