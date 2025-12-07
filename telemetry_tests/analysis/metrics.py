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

    # Duplicate rate
    dup_rate = df["duplicate_flag"].sum() / packets

    # Gaps
    total_gaps = df["gap_flag"].sum()

    # Reordering
    if "reorder_flag" in df.columns:
        reordered_packets = df["reorder_flag"].sum()
        reorder_rate = reordered_packets / packets
    else:
        reordered_packets = 0
        reorder_rate = 0.0

    # Payload
    avg_payload = df["payload_size"].mean()
    bytes_per_report = 10 + avg_payload  # header + payload

    # Batch %
    batch_percent = (df["is_batch"].sum() / packets) * 100

    # ===== DISPLAY RESULTS =====
    print(f"Packets received : {packets}")
    print(f"Duplicate rate   : {dup_rate:.2%}")
    print(f"Sequence gaps    : {total_gaps}")
    print(f"Reordered pkts   : {reordered_packets}")
    print(f"Reorder rate     : {reorder_rate:.2%}")
    print(f"Bytes/report     : {bytes_per_report:.2f}")
    print(f"Batch %          : {batch_percent:.1f}%")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to CSV log file")
    args = parser.parse_args()

    analyze_csv(args.csv)
