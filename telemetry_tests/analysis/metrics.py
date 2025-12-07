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
    dup_rate = df["duplicate_flag"].sum() / packets
    gaps = df["gap_flag"].sum()
    avg_payload = df["payload_size"].mean()
    bytes_per_report = 10 + avg_payload
    batch_percent = (df["is_batch"].sum() / packets) * 100

    print(f"Packets received : {packets}")
    print(f"Duplicate rate   : {dup_rate:.2%}")
    print(f"Sequence gaps    : {gaps}")
    print(f"Bytes/report     : {bytes_per_report:.2f}")
    print(f"Batch %          : {batch_percent:.1f}%")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to CSV log file")
    args = parser.parse_args()

    analyze_csv(args.csv)
