import pandas as pd
import glob
import os

def analyze_csv(csv_file):
    df = pd.read_csv(csv_file)
    
    if len(df) == 0:
        return None
    
    # Calculate metrics
    metrics = {
        'packets_received': len(df),
        'duplicate_rate': df['duplicate_flag'].sum() / len(df) if len(df) > 0 else 0,
        'sequence_gap_count': df['gap_flag'].sum(),
        'avg_payload_size': df['payload_size'].mean(),
        'total_data_bytes': df['payload_size'].sum(),
        'batch_percentage': (df['is_batch'].sum() / len(df)) * 100 if len(df) > 0 else 0,
    }
    
    # Calculate bytes_per_report
    # Header = 10 bytes, payload = avg from CSV
    header_size = 10
    metrics['bytes_per_report'] = header_size + metrics['avg_payload_size']
    
    return metrics

def analyze_scenario(scenario_name, csv_pattern):
    print(f"\n{'='*60}")
    print(f"SCENARIO: {scenario_name}")
    print(f"{'='*60}")
    
    csv_files = sorted(glob.glob(csv_pattern))
    
    if not csv_files:
        print(f"No CSV files found matching {csv_pattern}")
        return
    
    all_metrics = []
    
    for i, csv_file in enumerate(csv_files, 1):
        print(f"\nRun {i}: {os.path.basename(csv_file)}")
        metrics = analyze_csv(csv_file)
        
        if metrics:
            all_metrics.append(metrics)
            print(f"  Packets received:     {metrics['packets_received']}")
            print(f"  Duplicate rate:       {metrics['duplicate_rate']:.2%}")
            print(f"  Sequence gaps:        {metrics['sequence_gap_count']}")
            print(f"  Bytes per report:     {metrics['bytes_per_report']:.2f}")
            print(f"  Batch percentage:     {metrics['batch_percentage']:.1f}%")

if __name__ == "__main__":
    print("="*60)
    print("TELEMETRY PROTOCOL - METRICS ANALYSIS")
    print("="*60)
    
    # Analyze each scenario
    # analyze_scenario("BASELINE (No Impairment)", "")
    # analyze_scenario("LOSS 5%", "")
    # analyze_scenario("DELAY + JITTER (100ms ±10ms)", "")
    
    print("\n" + "="*60)
    print("Analysis complete!")
    print("="*60)