import pandas as pd
import numpy as np
import argparse
import os
import matplotlib.pyplot as plt

def analyze_csv(csv_file):
    df = pd.read_csv(csv_file)

    if len(df) == 0:
        print("Empty CSV!")
        return

    print("\n==============================")
    print(f" ANALYZING: {csv_file}")
    print("==============================")

    packets = len(df)

    # -------------------------
    # BASIC STATS
    # -------------------------
    dup_rate = df["duplicate_flag"].sum() / packets
    gaps = df["gap_flag"].sum()
    reorder_rate = df["reorder_flag"].sum() / packets

    # Calculate packet loss based on gap_flag (server-detected gaps)
    # Each gap_flag=1 indicates missing packet(s)
    # Packet loss = number of gaps / (gaps + packets received) * 100
    total_gaps = gaps
    packet_loss_pct = (total_gaps / (total_gaps + packets)) * 100 if (total_gaps + packets) > 0 else 0

    # Alternative calculation: based on sequence range
    max_seq = df["seq"].max()
    min_seq = df["seq"].min()
    expected_packets = max_seq - min_seq + 1
    sequence_based_loss = (expected_packets - packets) / expected_packets * 100 if expected_packets > 0 else 0

    avg_payload = df["payload_size"].mean()
    bytes_per_report = 10 + avg_payload
    batch_percent = (df["is_batch"].sum() / packets) * 100

    # -------------------------
    # LATENCY CALCULATION (per device)
    # -------------------------
    # Calculate inter-packet arrival time for each device separately
    if "device_id" in df.columns:
        latencies = []
        for device in df["device_id"].unique():
            device_df = df[df["device_id"] == device].sort_values("seq")
            if len(device_df) > 1:
                device_latency = device_df["arrival_time"].diff().dropna()
                latencies.extend(device_latency.values)
        latencies = np.array(latencies)
        avg_latency = np.mean(latencies) if len(latencies) > 0 else 0
        max_latency = np.max(latencies) if len(latencies) > 0 else 0
    else:
        latencies = []
        avg_latency = 0
        max_latency = 0

    # -------------------------
    # JITTER CALCULATION
    # -------------------------
    if len(latencies) > 1:
        latency_diff = np.abs(np.diff(latencies))
        avg_jitter = np.mean(latency_diff)
    else:
        avg_jitter = 0

    # -------------------------
    # THROUGHPUT (bytes per second)
    # -------------------------
    total_bytes = df["payload_size"].sum()
    
    # total test duration in seconds
    start_time = df["arrival_time"].min()
    end_time = df["arrival_time"].max()
    duration_ms = end_time - start_time
    duration_sec = max(duration_ms / 1000, 1e-9)

    throughput = total_bytes / duration_sec

    print(f"\nPackets received  : {packets}")
    print(f"Expected packets  : {expected_packets}")
    print(f"Gap-based loss    : {packet_loss_pct:.2f}%")
    print(f"Seq-based loss    : {sequence_based_loss:.2f}%")
    print(f"Detected gaps     : {gaps}")
    print(f"Duplicate rate    : {dup_rate:.2%}")
    print(f"Reorder rate      : {reorder_rate:.2%}")
    print(f"Avg payload bytes : {avg_payload:.2f}")
    print(f"Bytes/report      : {bytes_per_report:.2f}")
    print(f"Batch %           : {batch_percent:.1f}%")

    print("\n--- LATENCY ---")
    print(f"Avg latency (ms)  : {avg_latency:.2f}")
    print(f"Max latency (ms)  : {max_latency:.2f}")

    print("\n--- JITTER ---")
    print(f"Avg jitter (ms)   : {avg_jitter:.2f}")

    print("\n--- THROUGHPUT ---")
    print(f"Throughput (bytes/sec): {throughput:.2f}")
    print(f"Test duration (sec): {duration_sec:.2f}")


    # ---------------------------------------------------------------------------
    # ---------------------------------------------------------------------------
    #                               PLOTTING
    # ---------------------------------------------------------------------------
    # ---------------------------------------------------------------------------
    output_dir = os.path.dirname(csv_file)

    # 1. Latency Distribution
    if len(latencies) > 0:
        plt.figure(figsize=(8, 5))
        plt.hist(latencies, bins=30, color='blue', alpha=0.7)
        plt.title("Latency Distribution")
        plt.xlabel("Latency (ms)")
        plt.ylabel("Frequency")
        plt.grid(True)
        plt.savefig(os.path.join(output_dir, "latency_distribution.png"))
        plt.close()

    # 2. Jitter Over Time
    if len(latencies) > 1:
        plt.figure(figsize=(8, 5))
        plt.plot(latency_diff, color='purple')
        plt.title("Jitter Over Time")
        plt.xlabel("Packet Index")
        plt.ylabel("Jitter (ms)")
        plt.grid(True)
        plt.savefig(os.path.join(output_dir, "jitter_over_time.png"))
        plt.close()

    # 3. Throughput Over Time (Sliding window)
    window_size = 20
    df["throughput_window"] = df["payload_size"].rolling(window_size).sum() * (1000 / window_size)

    plt.figure(figsize=(8, 5))
    plt.plot(df["throughput_window"], color='green')
    plt.title("Throughput Over Time")
    plt.xlabel("Packet Index")
    plt.ylabel("Bytes/sec")
    plt.grid(True)
    plt.savefig(os.path.join(output_dir, "throughput_over_time.png"))
    plt.close()

    # 4. Reorder Visualization
    reorder_indices = df.index[df["reorder_flag"] == 1]

    plt.figure(figsize=(8, 5))
    plt.stem(reorder_indices, np.ones_like(reorder_indices), linefmt='red', markerfmt='ro')
    plt.title("Reordered Packet Positions")
    plt.xlabel("Packet Index")
    plt.ylabel("Reordered? (1 = yes)")
    plt.grid(True)
    plt.savefig(os.path.join(output_dir, "reorder_positions.png"))
    plt.close()

    print("\n[GRAPHS GENERATED]")
    print("- latency_distribution.png")
    print("- jitter_over_time.png")
    print("- throughput_over_time.png")
    # print("- reorder_positions.png")
    print("Saved in:", output_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to CSV log file")
    args = parser.parse_args()

    analyze_csv(args.csv)
