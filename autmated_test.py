import argparse
import os
import csv
import sys
import time
import subprocess
import pathlib
import signal

SERVER = pathlib.Path(__file__).parent.resolve() / "prototype_server.py"
CLIENT = pathlib.Path(__file__).parent.resolve() / "prototype_client.py"
LOG = pathlib.Path(__file__).parent.resolve() / "telemetry_log.csv"


def start_server():
    test_dir = pathlib.Path(__file__).parent.resolve()/"test_logs"
    test_dir.mkdir(exist_ok=True)
    runDate = int(time.time())
    log_path = test_dir / f"server_log_{runDate}.log"

    log_fp = open(log_path, "w", buffering=1, encoding="utf-8")

    proc = subprocess.Popen(
        [sys.executable, "-u", str(SERVER)],
        stdout=log_fp,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc, log_fp, log_path

def start_client():

    test_dir = pathlib.Path(__file__).parent.resolve()/"test_logs"
    test_dir.mkdir(exist_ok=True)
    runDate = int(time.time())
    log_path = test_dir / f"client_log_{runDate}.log"

    log_fp = open(log_path, "w", buffering=1, encoding="utf-8")

    proc = subprocess.Popen(
        [sys.executable, "-u", str(CLIENT)],
        stdout=log_fp,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc, log_fp, log_path

def reset_device_id_counter():
    counter_file = pathlib.Path(__file__).parent.resolve() / "client_ids.txt"
    try:
        os.remove(counter_file)
        print("[TEST] client_ids.txt reset", flush=True)
    except FileNotFoundError:
        pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clients", type=int, default=2, help="number of clients to launch")
    parser.add_argument("--stagger", type=float, default=0.25, help="seconds between client launches")
    parser.add_argument("--no-reset", action="store_true", help="do not reset client_ids.txt on start")
    args = parser.parse_args()

    if not args.no_reset:
        reset_device_id_counter()

    
    # 48l elserver
    print("[RUN] Launching server…")
    server_proc, server_log_fp, server_log_path = start_server()
    print(f"[RUN] Server started. PID={server_proc.pid}")
    print(f"[RUN] Server log: {server_log_path}")
    print("[INFO] Press Ctrl+C to stop.")

    time.sleep(2)

    #48l elclients
    clients = []
    print(f"[RUN] Launching {args.clients} client(s)…")
    for i in range(args.clients):
        cli_proc, cli_log_fp, cli_log_path = start_client()
        print(f"[RUN] Client {i+1}/{args.clients} started. PID={cli_proc.pid}")
        print(f"[RUN] Client log: {cli_log_path}")
        clients.append((cli_proc, cli_log_fp, cli_log_path))
        time.sleep(args.stagger)

    print("[INFO] Press Ctrl+C to stop all.") #2e2fel abo elcode (ana m4 fahem eh ely kan gayebly error fa n2lt el7eta elgya serf)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[RUN] Stopping server and clients…")
        try:
            if os.name == "nt":
                # Windows: terminate all
                for (p, _, _) in clients: p.terminate()
                server_proc.terminate()
            else:
                # POSIX: send SIGINT for graceful shutdown
                for (p, _, _) in clients: p.send_signal(signal.SIGINT)
                server_proc.send_signal(signal.SIGINT)

            # Wait for exit
            for (p, _, _) in clients: p.wait(timeout=5)
            server_proc.wait(timeout=5)
        except Exception:
            # Force kill on timeout/errors
            for (p, _, _) in clients:
                try: p.kill()
                except Exception: pass
            try: server_proc.kill()
            except Exception: pass
    finally:
        # Close all logs
        for (_, fp, _) in clients:
            try: fp.close()
            except Exception: pass
        try: server_log_fp.close()
        except Exception: pass
        print("[RUN] Server and clients stopped cleanly.")

if __name__ == "__main__":
    main()