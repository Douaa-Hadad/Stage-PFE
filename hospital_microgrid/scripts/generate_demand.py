import pandas as pd
import numpy as np
from pathlib import Path

def generate_demand():
    # Set seed for reproducibility
    np.random.seed(42)
    
    # Paths
    base_path = Path(__file__).parent.parent
    weather_file = base_path / "data" / "weather" / "meteo_casablanca.csv"
    output_dir = base_path / "data" / "demand"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load data
    df = pd.read_csv(weather_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    n_steps = len(df)
    
    # Section Specifications
    sections = [
        {"file": "demand_reanimation.csv", "name": "Réanimation/ICU", "priority": 1, "base": 35, "type": "icu"},
        {"file": "demand_bloc.csv", "name": "Bloc Opératoire", "priority": 1, "base": 45, "type": "bloc"},
        {"file": "demand_urgences.csv", "name": "Urgences", "priority": 1, "base": 50, "type": "urgences"},
        {"file": "demand_neonatologie.csv", "name": "Néonatologie", "priority": 1, "base": 20, "type": "flat"},
        {"file": "demand_dialyse.csv", "name": "Dialyse", "priority": 2, "base": 30, "type": "dialyse"},
        {"file": "demand_maternite.csv", "name": "Maternité", "priority": 2, "base": 25, "type": "maternite"},
        {"file": "demand_laboratoire.csv", "name": "Laboratoire", "priority": 2, "base": 15, "type": "labo"},
        {"file": "demand_pharmacie.csv", "name": "Pharmacie", "priority": 2, "base": 10, "type": "pharmacie"},
        {"file": "demand_radiologie.csv", "name": "Radiologie", "priority": 3, "base": 35, "type": "radio"},
        {"file": "demand_medecine.csv", "name": "Médecine Interne", "priority": 3, "base": 20, "type": "medecine"},
        {"file": "demand_consultations.csv", "name": "Consultations", "priority": 4, "base": 15, "type": "consult"},
        {"file": "demand_administration.csv", "name": "Administration", "priority": 5, "base": 12, "type": "admin"},
        {"file": "demand_general.csv", "name": "Général", "priority": 5, "base": 40, "type": "general"}
    ]
    
    all_section_dfs = []
    
    for sec in sections:
        s_df = df[['timestamp', 'temperature_2m', 'hour', 'is_weekend', 'season', 'is_daytime']].copy()
        
        # 1. Base Pattern Logic
        def get_base(row):
            h = row['hour']
            daytime = row['is_daytime']
            wknd = row['is_weekend']
            t = sec['type']
            base = sec['base']
            
            if t == "icu": return base * (1.0 if daytime else 0.95)
            if t == "bloc": return base if 7 <= h <= 20 else 2.0
            if t == "urgences": return base * (1.1 if 10 <= h <= 22 else 0.95)
            if t == "flat": return base
            if t == "dialyse": return base if 6 <= h <= 18 else 0.0
            if t == "maternite": return base * (1.2 if not daytime else 0.8)
            if t == "labo": return base if 7 <= h <= 19 else 1.0
            if t == "pharmacie": return base * (1.0 if daytime else 0.7)
            if t == "radio": return base if (not wknd and 8 <= h <= 18) else 0.0
            if t == "medecine": return base * (1.1 if daytime else 0.7)
            if t == "consult": return base if (not wknd and 8 <= h <= 17) else 0.0
            if t == "admin": return base if (not wknd and 8 <= h <= 17) else 0.0
            if t == "general": return base * (1.0 if daytime else 0.1)
            return base

        s_df['base_kw'] = s_df.apply(get_base, axis=1)
        
        # 2. Weekend Effect (P3/P4/P5 reduced by 30%)
        if sec['priority'] >= 3:
            s_df.loc[s_df['is_weekend'] == 1, 'base_kw'] *= 0.7
            
        # 3. Temperature Effect
        # above 25°C add 0.8% per °C, below 15°C add 0.5% per °C
        s_df['temp_factor'] = 0.0
        s_df.loc[s_df['temperature_2m'] > 25, 'temp_factor'] = (s_df['temperature_2m'] - 25) * 0.008
        s_df.loc[s_df['temperature_2m'] < 15, 'temp_factor'] = (15 - s_df['temperature_2m']) * 0.005
        s_df['temperature_effect_kw'] = s_df['base_kw'] * s_df['temp_factor']
        
        # 4. Season Effect
        # summer +12%, winter +8%
        s_df['season_factor'] = 0.0
        s_df.loc[s_df['season'] == 'summer', 'season_factor'] = 0.12
        s_df.loc[s_df['season'] == 'winter', 'season_factor'] = 0.08
        s_df['season_effect_kw'] = s_df['base_kw'] * s_df['season_factor']
        
        # 5. Gaussian Noise (±8%)
        # Using uniform as "±8%" often implies a range, but user said Gaussian noise.
        # I'll use normal with std=0.04 so 95% is within ±8%.
        s_df['noise_kw'] = s_df['base_kw'] * np.random.normal(0, 0.04, n_steps)
        
        # 6. Spikes (~10/year)
        s_df['spike_flag'] = 0
        s_df['spike_kw'] = 0.0
        num_spikes = 20 # 10 per year * 2 years
        spike_indices = np.random.choice(s_df.index, size=num_spikes, replace=False)
        for idx in spike_indices:
            duration = np.random.randint(1, 4) # 1-3 timesteps
            end_idx = min(idx + duration, n_steps)
            s_df.loc[idx:end_idx-1, 'spike_flag'] = 1
            # magnitude +40% of base
            s_df.loc[idx:end_idx-1, 'spike_kw'] = s_df.loc[idx:end_idx-1, 'base_kw'] * 0.4
            
        # Final Demand
        s_df['final_demand_kw'] = (s_df['base_kw'] + 
                                   s_df['temperature_effect_kw'] + 
                                   s_df['season_effect_kw'] + 
                                   s_df['noise_kw'] + 
                                   s_df['spike_kw'])
        
        # Ensure non-negative
        s_df['final_demand_kw'] = s_df['final_demand_kw'].clip(lower=0)
        
        # Prepare section output
        s_df['section'] = sec['name']
        s_df['priority'] = f"P{sec['priority']}"
        
        cols = ['timestamp', 'section', 'priority', 'base_kw', 'temperature_effect_kw', 
                'season_effect_kw', 'noise_kw', 'spike_flag', 'final_demand_kw']
        
        final_sec_df = s_df[cols]
        final_sec_df.to_csv(output_dir / sec['file'], index=False)
        all_section_dfs.append(final_sec_df)
        
        # Individual Summary
        mean_d = final_sec_df['final_demand_kw'].mean()
        max_d = final_sec_df['final_demand_kw'].max()
        min_d = final_sec_df['final_demand_kw'].min()
        spikes = ( (final_sec_df['spike_flag'] == 1) & (final_sec_df['spike_flag'].shift(1) == 0) ).sum()
        print(f"Summary for {sec['name']}:")
        print(f"  Mean: {mean_d:.2f} kW, Max: {max_d:.2f} kW, Min: {min_d:.2f} kW, Spikes: {spikes}")

    # Combined File
    combined_df = pd.concat(all_section_dfs)
    
    # Calculate total hospital kw per timestamp
    # Group by timestamp and sum final_demand_kw
    totals = combined_df.groupby('timestamp')['final_demand_kw'].sum().reset_index()
    totals.rename(columns={'final_demand_kw': 'total_hospital_kw'}, inplace=True)
    
    # Merge totals back or handle it differently?
    # User wants "combined file demand_all_sections.csv should have all 13 sections stacked ... plus a total_hospital_kw column"
    # This means total_hospital_kw is repeated for all sections at that timestamp.
    combined_df = combined_df.merge(totals, on='timestamp')
    
    combined_df.to_csv(output_dir / "demand_all_sections.csv", index=False)
    
    # Overall Summary
    print("-" * 30)
    print(f"Hospital Overall Stats:")
    print(f"  Peak Demand: {totals['total_hospital_kw'].max():.2f} kW")
    print(f"  Average Demand: {totals['total_hospital_kw'].mean():.2f} kW")
    print(f"Files written to {output_dir}")

if __name__ == "__main__":
    generate_demand()
