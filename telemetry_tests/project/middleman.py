import socket
import random
import time
import argparse

BUFFER = 2048


def udp_proxy(listen_ip, listen_port, server_ip, server_port,
              loss_rate=0.0, duplicate_rate=0.0, delay_ms=0, reorder_rate=0.0):

    print("\n===============================")
    print(" UDP IMPAIRMENT PROXY STARTED ")
    print("===============================")
    print(f"Listening on       {listen_ip}:{listen_port}")
    print(f"Forwarding to      {server_ip}:{server_port}")
    print(f"Loss rate          = {loss_rate * 100}%")
    print(f"Duplicate rate     = {duplicate_rate * 100}%")
    print(f"Reorder rate       = {reorder_rate * 100}%")
    print(f"Delay per packet   = {delay_ms} ms")
    print("================================\n")

    # Socket to receive from client
    proxy = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    proxy.bind((listen_ip, listen_port))

    # Socket to forward to server
    forwarder = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    reorder_buffer = None

    print("[READY] Waiting for packets...\n")

    while True:
        data, addr = proxy.recvfrom(BUFFER)

        # --------- LOSS ----------
        if random.random() < loss_rate:
            print("[DROP] Packet dropped")
            continue

        # --------- DELAY ----------
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
            print(f"[DELAY] {delay_ms} ms")

        # --------- REORDER ----------
        if random.random() < reorder_rate:
            if reorder_buffer is None:
                reorder_buffer = data
                print("[REORDER] Packet held for later")
                continue
            else:
                print("[REORDER] Releasing stored packet")
                forwarder.sendto(reorder_buffer, (server_ip, server_port))
                reorder_buffer = data
                continue

        # --------- DUPLICATE ----------
        if random.random() < duplicate_rate:
            print("[DUPLICATE] Sending 2 copies")
            forwarder.sendto(data, (server_ip, server_port))
            forwarder.sendto(data, (server_ip, server_port))
        else:
            print("[FORWARD] Normal packet")
            forwarder.sendto(data, (server_ip, server_port))

        # (Optional) You can flush reorder buffer occasionally
        # but not required for now.


def main():
    parser = argparse.ArgumentParser(description="UDP impairment middleman proxy")

    parser.add_argument("--listen_ip", required=True)
    parser.add_argument("--listen_port", type=int, required=True)
    parser.add_argument("--server_ip", required=True)
    parser.add_argument("--server_port", type=int, required=True)
    parser.add_argument("--loss", type=float, default=0.0)
    parser.add_argument("--duplicate", type=float, default=0.0)
    parser.add_argument("--delay", type=int, default=0)
    parser.add_argument("--reorder", type=float, default=0.0)

    args = parser.parse_args()

    udp_proxy(
        args.listen_ip,
        args.listen_port,
        args.server_ip,
        args.server_port,
        args.loss,
        args.duplicate,
        args.delay,
        args.reorder
    )


if __name__ == "__main__":
    main()
