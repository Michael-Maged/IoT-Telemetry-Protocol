import socket
import struct
import time
import csv
import os
import argparse

                #1B 2B 2B 4B 1B
HEADER_FORMAT = "!B H H I B"     # version+type, deviceID, seqNum, timestamp, flags
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
PORT = 9999
BUFFER = 2048
FORMAT = "utf-8"


# message types
initMsg = 0
dataMsg = 1
msgHeartBeat = 2

device_state = {} # dictinary to store the devices states by the Device ID... things like (seqNum, duplicates, gaps and time stamps)

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind(("", PORT))

def start():
    print("[SERVER READY] Waiting for messages...")
    while True:
        data, client_addr = server.recvfrom(BUFFER)
        arrivalTime = int(time.time() * 1000)  # in milliseconds

        if data == b"DISCOVER_SERVER":
            print(f"[DISCOVERY] from {client_addr}")
            server.sendto(b"SERVER_IP_RESPONSE", client_addr)
            continue


        if len(data) < HEADER_SIZE:
            print(f"[ERROR] Packet too small from {client_addr}")
            continue


        version_type, deviceID, seqNum, timestamp, flags = struct.unpack( HEADER_FORMAT, data[:HEADER_SIZE])
        version = version_type >> 4
        msgType = version_type & 0x0F
        payload = data[HEADER_SIZE:].decode(FORMAT, errors="ignore")


        if deviceID not in device_state:
            device_state[deviceID] = {
                "last_seq": None,
                "received_seqs": set(), # make a set that will store the recieved packets
                "duplicate_seqs": set(), # make a set that will store the duplicated packets
                "gaps": 0, 
                'last_heartbeat': None,
            }

        state = device_state[deviceID]

        if msgType == msgHeartBeat:
            state["last_heartbeat"] = arrivalTime
            print(f"[HEARTBEAT] Device {deviceID} is alive (seq={seqNum})")
            continue


        duplicate_flag = False
        if seqNum in state["received_seqs"]:
            duplicate_flag = True
            state["duplicate_seqs"].add(seqNum)
        else:
            state["received_seqs"].add(seqNum)


        gap_flag = False
        if state["last_seq"] is not None:
            expected = (state["last_seq"] + 1) & 0xFFFF # 2 bytes counter that increments on every new packet
            if seqNum != expected:
                gap_flag = True

                if seqNum > state["last_seq"]:
                    state["gaps"] += (seqNum - state["last_seq"] - 1) # if the last seq was 1 and the seqNum is 5 so we will count 5-1 -1 = 3 (seq: 2 3 4)
                else:
                    state["gaps"] += ((0xFFFF - state["last_seq"]) + seqNum) # if the last seq was 0xFFFC and the seqNum is 3 so we will count FFFF-FFFC + 3 = 5 (seq: FFFE FFFF 0 1 2)

        state["last_seq"] = seqNum

        print("====================================")
        print(f"[PACKET] from {client_addr}")
        print(f"Type     : {'INIT' if msgType == initMsg else 'DATA' if msgType == dataMsg else 'HEARTBEAT' if msgType == msgHeartBeat else msgType}")
        print(f"Version  : {version}")
        print(f"DeviceID : {deviceID}")
        print(f"SeqNum   : {seqNum}")
        print(f"TimeSent : {timestamp}")
        print(f"Arrival  : {arrivalTime}")
        print(f"Payload  : {payload if payload else '(no payload)'}")
        print("--- Tracking State ---")
        print(f"Duplicates: {state['duplicate_seqs']}")
        print(f"Gaps      : {state['gaps']}")
        print(f"Duplicate flag:  {duplicate_flag}")
        print(f"Gap flg:       {gap_flag}")
        print("====================================")


def main():
    print("[BOOT] Starting UDP Telemetry Server...")
    start()


if __name__ == "__main__":
    main()