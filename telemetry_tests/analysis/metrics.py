import pandas as pd
import argparse
import os

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
    df["latency_shift"] = df["latency"].shift(1)
    df["jitter"] = (df["latency"] - df["latency_shift"]).abs()

    avg_jitter = df["jitter"][1:].mean()   # skip first NaN

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to CSV log file")
    args = parser.parse_args()

    analyze_csv(args.csv)
