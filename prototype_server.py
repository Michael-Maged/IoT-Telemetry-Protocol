import socket
import struct
import time

HEADER_FORMAT = "!B H H I B" # format lel10 bytes
HEADER_SIZE = struct.calcsize(HEADER_FORMAT) # 10 bytes
PORT = 9999 #ay rakam 8albn bs lazem tkoon damen eno port number fady bs
SERVER_IP = socket.gethostbyname(socket.gethostname()) #hat elip address bta3ak
ADDRESS = (SERVER_IP, PORT)
FORMAT = 'utf-8'
BUFFER = 2048 #content elmessage bt3tk max yb2a kam byte

initMsg = 0
dataMsg = 1


print(SERVER_IP)
print(socket.gethostname())

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #by3ml UPD socket y2dr y3ml interaction m4 elclients belIP address V4 
#server.bind(ADDRESS) #erbot elsocket bta3ak b address elserver 
server.bind(("", PORT))

def start():
    print("[SERVER READY] Waiting for messages...")
    print(SERVER_IP)
    print(socket.gethostname())

    while True:
        data, client_addr = server.recvfrom(BUFFER)
        arrivalTime = time.time()
        if data == b"DISCOVER_SERVER":
            print(f"[DISCOVERY] request from {client_addr}")
            server.sendto(b"SERVER_IP_RESPONSE", client_addr)
            continue


        if len(data) < HEADER_SIZE:
            print(f"[ERROR] Packet too short from {client_addr}")
            continue

        version_type, deviceID, seqNum, timestamp, flags = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
        version = version_type >> 4
        msgType = version_type & 0x0F

        message_encoded = data[HEADER_SIZE:]
        if message_encoded:
            message = message_encoded.decode(FORMAT, errors="ignore")
        else:
            print("no message sent")
            message = ""

        if msgType == dataMsg:
            print("==========================================")
            print(f"[DATA] from {client_addr}")
            print(f"version={version}, deviceID={deviceID}, seqNum={seqNum}, timestamp={timestamp}, flags={flags}")
            print(f"Message: {message}")
            print(f"Arrival time: {arrivalTime}")
            print("==========================================")
        elif msgType == initMsg:
            print("==========================================")
            print(f"[INIT] from {client_addr} ")
            print(f"version={version}, deviceID={deviceID}, seqNum={seqNum}, timestamp={timestamp}, flags={flags}")
            print(f"Arrival time: {arrivalTime}")
            print("==========================================")
        else:
            print("==========================================")
            print(f"[UNKNOWN type={msgType}] from {client_addr}")
            print(f"version={version}, deviceID={deviceID}, seqNum={seqNum}, timestamp={timestamp}, flags={flags}")
            if message:
                print(f"Data (raw): {message}")
            print(f"Arrival time: {arrivalTime}")
            print("==========================================")
        

print(f'The server is starting... port: {PORT}')
start()