import pandas as pd
import numpy as np
import uuid
from pathlib import Path

def generate_grid():
    # Set seed for reproducibility
    np.random.seed(42)
    
    # Paths
    base_path = Path(__file__).parent.parent
    weather_file = base_path / "data" / "weather" / "meteo_casablanca.csv"
    output_file = base_path / "data" / "supply" / "grid_supply.csv"
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Load data
    df = pd.read_csv(weather_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Constants
    CONTRACTED_CAPACITY_KW = 600.0
    
    # Initialize
    df['grid_available_kw'] = CONTRACTED_CAPACITY_KW
    df['grid_capacity_pct'] = 100.0
    df['event_type'] = 'none'
    df['event_id'] = 'STABLE'
    df['is_outage'] = 0
    df['voltage_stable'] = 1
    
    # 1. Winter Peak Reduction (Nov-Feb, 18h-21h, -15%)
    winter_months = [11, 12, 1, 2]
    peak_hours = (df['hour'] >= 18.0) & (df['hour'] < 21.0)
    winter_mask = df['month'].isin(winter_months) & peak_hours
    
    df.loc[winter_mask, 'grid_capacity_pct'] -= 15.0
    df.loc[winter_mask, 'event_type'] = 'winter_peak'
    
    # Helper to apply random events
    def apply_events(count_per_year, duration_range, capacity_pct_range, type_name, is_outage=False, is_sag=False, night_only=False):
        total_events = count_per_year * 2
        for _ in range(total_events):
            if night_only:
                # filter indices where is_daytime == 0
                eligible_indices = df[df['is_daytime'] == 0].index
                if len(eligible_indices) == 0: continue
                start_idx = np.random.choice(eligible_indices)
            else:
                start_idx = np.random.randint(0, len(df) - duration_range[1])
            
            duration = np.random.randint(duration_range[0], duration_range[1] + 1)
            end_idx = min(start_idx + duration, len(df))
            
            e_id = uuid.uuid4().hex[:8].upper()
            pct = np.random.uniform(capacity_pct_range[0], capacity_pct_range[1])
            
            df.loc[start_idx:end_idx-1, 'grid_capacity_pct'] = pct
            df.loc[start_idx:end_idx-1, 'event_type'] = type_name
            df.loc[start_idx:end_idx-1, 'event_id'] = e_id
            if is_outage:
                df.loc[start_idx:end_idx-1, 'is_outage'] = 1
            if is_sag:
                df.loc[start_idx:end_idx-1, 'voltage_stable'] = 0

    # 2. Voltage Sags (~40/year, 1-3 timesteps, 60-92% capacity)
    apply_events(40, (1, 3), (60, 92), 'voltage_sag', is_sag=True)
    
    # 3. Partial Outages (~12/year, 1-6 timesteps, 20-50%)
    apply_events(12, (1, 6), (20, 50), 'partial_outage', is_outage=True)
    
    # 4. Full Outages (~5/year, 2-16 timesteps, 0 kW)
    apply_events(5, (2, 16), (0, 0), 'full_outage', is_outage=True)
    
    # 5. Scheduled Maintenance (~2/year, 8-16 timesteps, night only, 0 kW)
    apply_events(2, (8, 16), (0, 0), 'maintenance', is_outage=True, night_only=True)
    
    # Final Calculation
    df['grid_available_kw'] = CONTRACTED_CAPACITY_KW * (df['grid_capacity_pct'] / 100.0)
    
    # Status
    df['status'] = 'stable'
    df.loc[df['event_type'] != 'none', 'status'] = df['event_type']
    
    # Select columns
    cols = ['timestamp', 'grid_available_kw', 'grid_capacity_pct', 'event_type', 
            'event_id', 'is_outage', 'voltage_stable', 'status']
    
    final_df = df[cols]
    final_df.to_csv(output_file, index=False)
    
    # Validation Summary
    print(f"Grid Supply Generation Complete: {output_file}")
    print(f"Total Rows: {len(final_df)}")
    print(f"Full Outages (0 kW): {len(final_df[final_df['grid_available_kw'] == 0])}")
    print(f"Voltage Sags: {len(final_df[final_df['voltage_stable'] == 0])}")
    print(f"Winter Peak Periods: {len(final_df[final_df['event_type'] == 'winter_peak'])}")
    print("-" * 30)

if __name__ == "__main__":
    generate_grid()
