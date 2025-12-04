import socket
import struct
import time
import random
import os
import argparse
#####################################

HEADER_FORMAT = "!B H H I B"   # (10 bytes)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
PORT = 9999
BUFFER = 2048
FORMAT = "utf-8"
Batch_Size = 5 # For batching mode
#################################################

# print(HEADER_SIZE)


version = 1
msgInit = 0
msgData = 1
msgHeartBeat = 2
flags = 0


client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

# Funcion to give each client id
def get_next_device_id(base_id=1000, counter_file="../Test/client_ids.txt"):
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

    client.settimeout(8)
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
    reading_batch = []


    try:
        last_heartbeat = time.time()
        heartbeat_interval = 1  # Send heartbeat every 1 second if no data sent
        # Send sensor data packets in a loop
        while True:
            seqNum = (seqNum + 1) & 0xFFFF
            timestamp = int(time.time() * 1000)
            current_sent = virtual_sensor()

            if current_sent == last_sent:
                if not reading_batch:
                    header = pack_header(version, msgHeartBeat, deviceID, seqNum, timestamp, flags)
                    client.sendto(header, ADDRESS)
                    print(f"[HEARTBEAT SENT] seq={seqNum}")
                    last_heartbeat = time.time() 
                
            else:
                # Add reading to batch
                reading_batch.append((current_sent))
                last_sent = current_sent
                
            # If batch full, send all readings together
            if len(reading_batch) >= Batch_Size:
                payload_str = ";".join([f"Reading={r}" for r in reading_batch])
                payload = payload_str.encode(FORMAT)

                header = pack_header(version, msgData, deviceID, seqNum, timestamp, flags)
                packet = header + payload
                client.sendto(packet, ADDRESS)

                print(f"[BATCH DATA SENT] seq={seqNum}, Readings={reading_batch}")
                reading_batch.clear()  # reset batch
                last_heartbeat = time.time()

            elif time.time() - last_heartbeat >= heartbeat_interval:
                # Send heartbeat if no data sent recently
                header = pack_header(version, msgHeartBeat, deviceID, seqNum, timestamp, flags)
                client.sendto(header, ADDRESS)
                print(f"[HEARTBEAT SENT] seq={seqNum}")   
                last_heartbeat = time.time()    
            time.sleep(1)  

       

    except KeyboardInterrupt:
        if reading_batch:
            payload_str = ";".join([f"Reading={r}" for r in reading_batch])
            payload = payload_str.encode(FORMAT)
            header = pack_header(version, msgData, deviceID, seqNum, timestamp, flags)
            packet = header + payload
            client.sendto(packet, ADDRESS)
            print(f"[FINAL BATCH DATA SENT] seq={seqNum}, Readings={reading_batch}")
        print("\n[CLIENT EXIT]")
    finally:
        client.close()



def main():
    start()


if __name__ == "__main__":
    main()
