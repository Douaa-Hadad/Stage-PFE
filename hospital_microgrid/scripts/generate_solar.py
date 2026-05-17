import pandas as pd
import numpy as np
from pathlib import Path

def generate_solar():
    # Set seed for reproducibility
    np.random.seed(42)
    
    # Paths
    base_path = Path(__file__).parent.parent
    weather_file = base_path / "data" / "weather" / "meteo_casablanca.csv"
    output_file = base_path / "data" / "supply" / "solar_supply.csv"
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Load data
    df = pd.read_csv(weather_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Constants
    CAPACITY_KW = 120.0
    NOCT = 45.0
    T_REF = 25.0
    DERATING_COEFF = 0.004  # 0.4% per °C
    INVERTER_EFF = 0.96
    DUST_LOSS_FACTOR = 0.98  # 2% loss
    DEGRADATION_FACTOR_2023 = 0.995  # 0.5% degradation
    
    # 1. Base Output
    # Base output = solar_potential * 120 kW
    base_output = df['solar_potential'] * CAPACITY_KW
    
    # 2. Panel Cell Temperature
    # T_cell = T_air + (NOCT - 20) * (Radiation / 800)
    # Radiation is shortwave_radiation
    df['panel_temp_c'] = df['temperature_2m'] + (NOCT - 20) * (df['shortwave_radiation'] / 800.0)
    
    # 3. Temperature Derating Factor
    # Factor = 1 - 0.4%/°C above 25°C
    df['derating_factor'] = df['panel_temp_c'].apply(lambda t: max(0.0, 1.0 - DERATING_COEFF * (t - T_REF)) if t > T_REF else 1.0)
    
    # 4. Losses and Degradation
    # Year-2 degradation (2023)
    df['year'] = df['timestamp'].dt.year
    degradation_mask = df['year'] == 2023
    df['degradation_loss'] = 0.0
    df.loc[degradation_mask, 'degradation_loss'] = 1.0 - DEGRADATION_FACTOR_2023
    
    # 5. Inverter Loss
    # We'll calculate the potential before inverter and then the loss
    pre_inverter_kw = base_output * df['derating_factor'] * DUST_LOSS_FACTOR * (1.0 - df['degradation_loss'])
    df['inverter_loss_kw'] = pre_inverter_kw * (1.0 - INVERTER_EFF)
    
    # 6. Solar Output kW
    df['solar_output_kw'] = pre_inverter_kw * INVERTER_EFF
    
    # Night forced to 0
    df.loc[df['is_daytime'] == 0, 'solar_output_kw'] = 0.0
    
    # 7. Curtailment (~15 events/year)
    # Total ~30 events for 2 years
    df['is_curtailed'] = 0
    df['curtailment_kw'] = 0.0
    
    # Generate random events
    num_events = 30
    event_start_indices = np.random.choice(df.index, size=num_events, replace=False)
    for idx in event_start_indices:
        duration = np.random.randint(1, 5)  # 1-4 timesteps
        end_idx = min(idx + duration, len(df))
        df.loc[idx:end_idx-1, 'is_curtailed'] = 1
        
    # Apply curtailment (assume full loss for curtailed timesteps)
    df.loc[df['is_curtailed'] == 1, 'curtailment_kw'] = df['solar_output_kw']
    df['net_solar_kw'] = df['solar_output_kw'] - df['curtailment_kw']
    
    # Status
    df['status'] = 'normal'
    df.loc[df['is_curtailed'] == 1, 'status'] = 'curtailed'
    df.loc[df['is_daytime'] == 0, 'status'] = 'night'
    
    # Select columns
    cols = ['timestamp', 'solar_potential', 'panel_temp_c', 'derating_factor', 
            'inverter_loss_kw', 'degradation_loss', 'solar_output_kw', 
            'is_curtailed', 'curtailment_kw', 'net_solar_kw', 'status']
    
    final_df = df[cols]
    final_df.to_csv(output_file, index=False)
    
    # Validation Summary
    print(f"Solar Supply Generation Complete: {output_file}")
    print(f"Total Rows: {len(final_df)}")
    print(f"Max Solar Output: {final_df['net_solar_kw'].max():.2f} kW")
    print(f"Mean Solar Output: {final_df['net_solar_kw'].mean():.2f} kW")
    print(f"Total Curtailment Events: {num_events}")
    print(f"Night Timesteps: {len(final_df[final_df['status'] == 'night'])}")
    print("-" * 30)

if __name__ == "__main__":
    generate_solar()
