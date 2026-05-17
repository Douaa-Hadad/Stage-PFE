import pandas as pd
import numpy as np
from pathlib import Path

def generate_wind():
    # Set seed for reproducibility
    np.random.seed(42)
    
    # Paths
    base_path = Path(__file__).parent.parent
    weather_file = base_path / "data" / "weather" / "meteo_casablanca.csv"
    output_file = base_path / "data" / "supply" / "wind_supply.csv"
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Load data
    df = pd.read_csv(weather_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Constants
    TOTAL_CAPACITY_KW = 80.0
    HUB_HEIGHT = 30.0
    MEASUREMENT_HEIGHT = 10.0
    HELLMANN_ALPHA = 0.14
    CUT_IN_MS = 3.0
    RATED_MS = 12.0
    CUT_OUT_MS = 25.0
    WAKE_LOSS_FACTOR = 0.95  # 5% loss
    AVAILABILITY_FACTOR = 0.97
    
    # 1. Scale Wind Speed
    # Convert km/h to m/s
    df['wind_speed_ms'] = (df['windspeed_10m'] / 3.6) * (HUB_HEIGHT / MEASUREMENT_HEIGHT)**HELLMANN_ALPHA
    
    # 2. Air Density Correction
    # rho = 1.292 / (1 + 0.00367 * T)
    # Factor relative to standard rho (1.225 or just use as multiplier if curve is at std)
    # We'll use it as a multiplier for potential
    df['air_density_factor'] = 1.292 / (1 + 0.00367 * df['temperature_2m'])
    # Normalize air density factor (assuming rated power is at rho=1.225)
    df['air_density_factor'] = df['air_density_factor'] / 1.225
    
    # 3. Gross Wind Power (Power Curve)
    def power_curve(v):
        if v < CUT_IN_MS:
            return 0.0
        elif v < RATED_MS:
            return ((v - CUT_IN_MS) / (RATED_MS - CUT_IN_MS))**3 * TOTAL_CAPACITY_KW
        elif v < CUT_OUT_MS:
            return TOTAL_CAPACITY_KW
        else:
            return 0.0
            
    df['gross_wind_kw'] = df['wind_speed_ms'].apply(power_curve) * df['air_density_factor']
    
    # 4. Wake Loss
    df['wake_loss_kw'] = df['gross_wind_kw'] * (1.0 - WAKE_LOSS_FACTOR)
    net_after_wake = df['gross_wind_kw'] * WAKE_LOSS_FACTOR
    
    # 5. Availability (97% random)
    df['availability_factor'] = np.random.choice([0.0, 1.0], size=len(df), p=[1-AVAILABILITY_FACTOR, AVAILABILITY_FACTOR])
    
    # 6. Maintenance (2 events/year, 8h each)
    df['is_maintenance'] = 0
    # ~4 events for 2 years
    for _ in range(4):
        start_idx = np.random.randint(0, len(df) - 16)
        df.loc[start_idx:start_idx+15, 'is_maintenance'] = 1
        
    # Apply maintenance and availability
    df['net_wind_kw'] = net_after_wake * df['availability_factor']
    df.loc[df['is_maintenance'] == 1, 'net_wind_kw'] = 0.0
    
    # Wind Potential column (normalized 0-1)
    df['wind_potential'] = df['gross_wind_kw'] / TOTAL_CAPACITY_KW
    
    # Status
    df['status'] = 'normal'
    df.loc[df['availability_factor'] == 0, 'status'] = 'unavailable'
    df.loc[df['is_maintenance'] == 1, 'status'] = 'maintenance'
    
    # Select columns
    cols = ['timestamp', 'wind_speed_ms', 'wind_potential', 'air_density_factor', 
            'gross_wind_kw', 'wake_loss_kw', 'is_maintenance', 
            'availability_factor', 'net_wind_kw', 'status']
    
    final_df = df[cols]
    final_df.to_csv(output_file, index=False)
    
    # Validation Summary
    print(f"Wind Supply Generation Complete: {output_file}")
    print(f"Total Rows: {len(final_df)}")
    print(f"Max Wind Output: {final_df['net_wind_kw'].max():.2f} kW")
    print(f"Mean Wind Output: {final_df['net_wind_kw'].mean():.2f} kW")
    print(f"Maintenance Timesteps: {df['is_maintenance'].sum()}")
    print(f"Unavailable Timesteps: {len(df[df['availability_factor'] == 0])}")
    print("-" * 30)

if __name__ == "__main__":
    generate_wind()
