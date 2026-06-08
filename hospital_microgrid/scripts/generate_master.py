import pandas as pd
import numpy as np
from pathlib import Path

def generate_master():
    # Paths
    base_path = Path(__file__).parent.parent
    weather_file = base_path / "data" / "weather" / "meteo_casablanca.csv"
    solar_file = base_path / "data" / "supply" / "solar_supply.csv"
    wind_file = base_path / "data" / "supply" / "wind_supply.csv"
    grid_file = base_path / "data" / "supply" / "grid_supply.csv"
    demand_file = base_path / "data" / "demand" / "demand_all_sections.csv"
    battery_dir = base_path / "data" / "batteries"
    trades_file = base_path / "data" / "trades" / "energy_trades.csv"
    output_file = base_path / "data" / "master_dataset.csv"
    
    # 1. Load Weather
    print("Loading weather data...")
    master = pd.read_csv(weather_file)
    weather_cols = ['timestamp', 'temperature_2m', 'cloud_cover', 'windspeed_10m', 
                    'precipitation', 'solar_potential', 'wind_potential', 
                    'is_daytime', 'is_weekend', 'season', 'hour']
    master = master[weather_cols]
    
    # 2. Load Supply
    print("Loading supply data...")
    solar = pd.read_csv(solar_file)[['timestamp', 'net_solar_kw', 'status']].rename(columns={'status': 'solar_status'})
    wind = pd.read_csv(wind_file)[['timestamp', 'net_wind_kw', 'status']].rename(columns={'status': 'wind_status'})
    grid = pd.read_csv(grid_file)[['timestamp', 'grid_available_kw', 'is_outage', 'event_type', 'event_id']]
    
    master = master.merge(solar, on='timestamp', how='left')
    master = master.merge(wind, on='timestamp', how='left')
    master = master.merge(grid, on='timestamp', how='left')
    
    # 2.5 Load generator data
    print("Loading generator data...")
    generator_dir = base_path / 'data' / 'supply' / 'generators'
    for gen_id in ['g1', 'g2', 'g3', 'g4']:
        gen_file = generator_dir / f'generator_{gen_id}.csv'
        if gen_file.exists():
            gdf = pd.read_csv(gen_file)[['timestamp', 'is_running', 'output_kw', 'fuel_level_pct', 'startup_delay_active']]
            gdf = gdf.rename(columns={
                'is_running': f'{gen_id}_running',
                'output_kw': f'{gen_id}_output_kw',
                'fuel_level_pct': f'{gen_id}_fuel_pct',
                'startup_delay_active': f'{gen_id}_starting'
            })
            master = master.merge(gdf, on='timestamp', how='left')
        else:
            master[f'{gen_id}_running'] = 0
            master[f'{gen_id}_starting'] = 0
            master[f'{gen_id}_output_kw'] = 0.0
            master[f'{gen_id}_fuel_pct'] = 0.0

    # 3. Load Demand (Aggregate)
    print("Aggregating demand data...")
    demand = pd.read_csv(demand_file)
    total_demand = demand.groupby('timestamp')['final_demand_kw'].sum().reset_index()
    total_demand.rename(columns={'final_demand_kw': 'total_hospital_kw'}, inplace=True)
    master = master.merge(total_demand, on='timestamp', how='left')
    
    # 4. Load Batteries
    print("Loading battery data...")
    battery_files = [
        "bat_reanimation.csv", "bat_bloc.csv", "bat_urgences.csv", 
        "bat_neonatologie.csv", "bat_dialyse.csv", "bat_maternite.csv", 
        "bat_laboratoire.csv", "bat_pharmacie.csv", "bat_radiologie.csv", 
        "bat_general.csv"
    ]
    bat_cols = []
    for bf in battery_files:
        section = bf.replace("bat_", "").replace(".csv", "")
        col_name = f"bat_{section}_pct"
        bat_cols.append(col_name)
        b_df = pd.read_csv(battery_dir / bf)[['timestamp', 'charge_pct']].rename(columns={'charge_pct': col_name})
        master = master.merge(b_df, on='timestamp', how='left')
        
    # 5. Load Trades
    print("Loading trades data...")
    if trades_file.exists() and trades_file.stat().st_size > 0:
        contents = trades_file.read_text().strip()
        if contents:
            trades = pd.read_csv(trades_file)
            trade_timestamps = trades['timestamp'].unique()
            master['is_trading'] = master['timestamp'].isin(trade_timestamps).astype(int)
        else:
            master['is_trading'] = 0
    else:
        master['is_trading'] = 0
        
    # 6. Derived Columns
    print("Computing derived columns...")
    master['total_supply_kw'] = master['grid_available_kw'] + master['net_solar_kw'] + master['net_wind_kw']
    master['energy_balance_kw'] = master['total_supply_kw'] - master['total_hospital_kw']
    
    def get_balance_status(val):
        if val > 20: return "surplus"
        if val >= 0: return "normal"
        if val >= -50: return "warning"
        return "critical"
    
    master['balance_status'] = master['energy_balance_kw'].apply(get_balance_status)
    
    master['avg_battery_pct'] = master[bat_cols].mean(axis=1)
    master['min_battery_pct'] = master[bat_cols].min(axis=1)
    
    # min_battery_section
    # We find the index of the min value across battery columns
    master['min_battery_section'] = master[bat_cols].idxmin(axis=1).str.replace("bat_", "").str.replace("_pct", "")
    
    master['total_generator_kw'] = (
        master['g1_output_kw'].fillna(0) +
        master['g2_output_kw'].fillna(0) +
        master['g3_output_kw'].fillna(0) +
        master['g4_output_kw'].fillna(0)
    )
    master['total_supply_kw'] = master['grid_available_kw'].fillna(0) + master['net_solar_kw'].fillna(0) + master['net_wind_kw'].fillna(0) + master['total_generator_kw']
    master['energy_balance_kw'] = master['total_supply_kw'] - master['total_hospital_kw']

    for gen_id in ['g1', 'g2', 'g3', 'g4']:
        master[f'{gen_id}_running'] = master[f'{gen_id}_running'].fillna(0).astype(int)
        master[f'{gen_id}_starting'] = master[f'{gen_id}_starting'].fillna(0).astype(int)
        master[f'{gen_id}_output_kw'] = master[f'{gen_id}_output_kw'].fillna(0.0)
        master[f'{gen_id}_fuel_pct'] = master[f'{gen_id}_fuel_pct'].fillna(0.0)

    master['any_generator_running'] = ((master['g1_running'] == 1) | (master['g2_running'] == 1) | (master['g3_running'] == 1) | (master['g4_running'] == 1)).astype(int)
    master['any_fuel_critical'] = ((master['g1_fuel_pct'] < 15) | (master['g2_fuel_pct'] < 15) | (master['g3_fuel_pct'] < 15) | (master['g4_fuel_pct'] < 15)).astype(int)

    master['renewable_fraction'] = (master['net_solar_kw'] + master['net_wind_kw']) / master['total_supply_kw']
    master['renewable_fraction'] = master['renewable_fraction'].fillna(0).replace([np.inf, -np.inf], 0)
    
    # alert_level
    def get_alert_level(row):
        is_out = row['is_outage']
        min_bat = row['min_battery_pct']
        bal = row['energy_balance_kw']
        
        # CRITICAL
        if (is_out == 1 and min_bat < 20) or (bal < -100):
            return "CRITICAL"
        # WARNING
        if (is_out == 1) or (bal < 0) or (min_bat < 30):
            return "WARNING"
        # NORMAL
        return "NORMAL"
        
    master['alert_level'] = master.apply(get_alert_level, axis=1)
    
    # 7. Save and Summary
    print(f"Saving to {output_file}...")
    master.to_csv(output_file, index=False)
    
    print("-" * 30)
    print(f"Master Dataset Summary:")
    print(f"  Total Rows: {len(master)}")
    print(f"  Total Columns: {len(master.columns)}")
    print(f"  Date Range: {master['timestamp'].min()} to {master['timestamp'].max()}")
    
    alert_counts = master['alert_level'].value_counts(normalize=True) * 100
    print("\nAlert Level Distribution (%):")
    for level in ["NORMAL", "WARNING", "CRITICAL"]:
        print(f"  {level}: {alert_counts.get(level, 0):.2f}%")
        
    grid_down_pct = (master['is_outage'] == 1).mean() * 100
    print(f"\nGrid Down Time: {grid_down_pct:.2f}%")
    print(f"Average Renewable Fraction: {master['renewable_fraction'].mean():.2f}")
    print(f"Peak Energy Balance: {master['energy_balance_kw'].max():.2f} kW")
    print(f"Worst Energy Balance: {master['energy_balance_kw'].min():.2f} kW")
    
    null_count = master.isnull().sum().sum()
    print(f"Total Null Values: {null_count}")
    
    if null_count > 0:
        print("\nNull values found in:")
        print(master.isnull().sum()[master.isnull().sum() > 0])

if __name__ == "__main__":
    generate_master()
