# Import modules for argument parsing, file operations, timing, subprocess handling, and path manipulation
import argparse
import os
import time
import subprocess
import pathlib
import sys

# Define paths for server and client scripts
SERVER = pathlib.Path(__file__).parent.resolve() / "../oop/oop_server.py"
CLIENT = pathlib.Path(__file__).parent.resolve() / "../oop/oop_client.py"

# Generate expected device IDs based on number of clients
def get_expected_device_ids(num_clients, base_id=1000):
    counter_file = pathlib.Path(__file__).parent.resolve() / "client_ids.txt"
    last_id = base_id
    if counter_file.exists():
        try:
            with open(counter_file, "r") as f:
                last_id = int(f.read().strip() or base_id)
        except (ValueError, FileNotFoundError):
            pass
    return list(range(last_id + 1, last_id + 1 + num_clients))

# Reset client ID counter file
def reset_device_id_counter():
    counter_file = pathlib.Path(__file__).parent.resolve() / "client_ids.txt"
    try:
        os.remove(counter_file)
        print("[TEST] Reset client_ids.txt")
    except FileNotFoundError:
        pass

# Start server process with logging
def start_server(device_ids):
    test_dir = pathlib.Path(__file__).parent.resolve() / "test_logs"
    test_dir.mkdir(exist_ok=True)
    run_date = int(time.time())
    log_path = test_dir / f"server_log_{run_date}.log"
    log_fp = open(log_path, "w", buffering=1, encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-u", str(SERVER), "--test-ids", ",".join(map(str, device_ids))],
        stdout=log_fp,
        stderr=subprocess.STDOUT,
        text=True,
    )
    print(f"[RUN] Server started. PID={proc.pid}, Log={log_path}")
    return proc, log_fp

# Start a client process with logging
def start_client(index, total):
    test_dir = pathlib.Path(__file__).parent.resolve() / "test_logs"
    test_dir.mkdir(exist_ok=True)
    run_date = int(time.time())
    log_path = test_dir / f"client_{index + 1}_log_{run_date}.log"
    log_fp = open(log_path, "w", buffering=1, encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-u", str(CLIENT)],
        stdout=log_fp,
        stderr=subprocess.STDOUT,
        text=True,
    )
    print(f"[RUN] Client {index + 1}/{total} started. PID={proc.pid}, Log={log_path}")
    return proc, log_fp

# Main function to run the test
def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Automated test for client-server communication")
    parser.add_argument("--clients", type=int, default=2, help="Number of clients to launch")
    parser.add_argument("--stagger", type=float, default=0.25, help="Seconds between client launches")
    parser.add_argument("--no-reset", action="store_true", help="Do not reset client_ids.txt")
    args = parser.parse_args()

    # Reset client IDs unless specified otherwise
    if not args.no_reset:
        reset_device_id_counter()

    # Get expected device IDs
    device_ids = get_expected_device_ids(args.clients)
    print(f"[TEST] Expected device IDs: {device_ids}")

    # Start server
    server_proc, server_log_fp = start_server(device_ids)
    time.sleep(2)  # Wait for server to initialize

    # Start clients with staggered launches
    clients = []
    print(f"[TEST] Launching {args.clients} client(s)...")
    for i in range(args.clients):
        client_proc, client_log_fp = start_client(i, args.clients)
        clients.append((client_proc, client_log_fp))
        time.sleep(args.stagger)

    # Run until interrupted
    print("[TEST] Running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[TEST] Stopping server and clients...")
        try:
            # Terminate processes gracefully
            if os.name == "nt":
                server_proc.terminate()
                for proc, _ in clients:
                    proc.terminate()

            server_proc.wait(timeout=5)
            for proc, _ in clients:
                proc.wait(timeout=5)
        except Exception as e:
            print(f"[ERROR] Failed to stop processes gracefully: {e}")
            server_proc.kill()
            for proc, _ in clients:
                proc.kill()
    finally:
        # Close log files
        server_log_fp.close()
        for _, client_log_fp in clients:
            client_log_fp.close()
        print("[TEST] Stopped. Messages logged to auto_script.csv")

# Entry point
if __name__ == "__main__":
    main()