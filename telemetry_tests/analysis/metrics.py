import pandas as pd
import argparse
import os

# import matplotlib.pyplot as plt

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

    avg_payload = df["payload_size"].mean()
    bytes_per_report = 10 + avg_payload
    batch_percent = (df["is_batch"].sum() / packets) * 100

    # -------------------------
    # LATENCY CALCULATION
    # -------------------------
    df["latency"] = df["arrival_time"].diff().fillna(0)


    avg_latency = df["latency"].mean()
    max_latency = df["latency"].max()

    # -------------------------
    # JITTER CALCULATION
    # -------------------------
    latency_diff = df["latency"].diff().abs().dropna()
    avg_jitter = latency_diff.mean()

    print("\n--- JITTER ---")
    print(f"Avg jitter (ms)  : {avg_jitter:.2f}")

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


    print(f"Packets received  : {packets}")
    print(f"Duplicate rate    : {dup_rate:.2%}")
    print(f"Reorder rate      : {reorder_rate:.2%}")
    print(f"Sequence gaps     : {gaps}")
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


    # ---------------------------------------------------------------------------
    # ---------------------------------------------------------------------------
    #                               PLOTTING
    # ---------------------------------------------------------------------------
    # ---------------------------------------------------------------------------
    output_dir = os.path.dirname(csv_file)

    # 1. Latency Distribution
    plt.figure(figsize=(8, 5))
    plt.hist(df["latency"], bins=30, color='blue', alpha=0.7)
    plt.title("Latency Distribution")
    plt.xlabel("Latency (ms)")
    plt.ylabel("Frequency")
    plt.grid(True)
    plt.savefig(os.path.join(output_dir, "latency_distribution.png"))
    plt.close()

    # 2. Jitter Over Time
    plt.figure(figsize=(8, 5))
    plt.plot(latency_diff.values, color='purple')
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
    print(f"- latency_distribution.png")
    print(f"- jitter_over_time.png")
    print(f"- throughput_over_time.png")
    # print(f"- reorder_positions.png")
    print("Saved in:", output_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to CSV log file")
    args = parser.parse_args()

    analyze_csv(args.csv)
