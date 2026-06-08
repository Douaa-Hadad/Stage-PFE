import pandas as pd
import numpy as np
from pathlib import Path

def load_generator_states(base_path):
    generator_dir = base_path / "data" / "supply" / "generators"
    generator_files = {
        'g1': generator_dir / 'generator_g1.csv',
        'g2': generator_dir / 'generator_g2.csv',
        'g3': generator_dir / 'generator_g3.csv',
        'g4': generator_dir / 'generator_g4.csv',
    }
    generator_state = {}
    for gen, path in generator_files.items():
        if path.exists():
            generator_state[gen] = pd.read_csv(path)
    return generator_state


def generate_batteries(generator_states=None):
    # Set seed for reproducibility
    np.random.seed(42)
    
    # Paths
    base_path = Path(__file__).parent.parent
    grid_file = base_path / "data" / "supply" / "grid_supply.csv"
    solar_file = base_path / "data" / "supply" / "solar_supply.csv"
    wind_file = base_path / "data" / "supply" / "wind_supply.csv"
    output_dir = base_path / "data" / "batteries"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load data
    grid_df = pd.read_csv(grid_file)
    solar_df = pd.read_csv(solar_file)
    wind_df = pd.read_csv(wind_file)
    
    n_steps = len(grid_df)
    if generator_states is None:
        generator_states = load_generator_states(base_path)
    
    # Battery Specifications
    # Note: 30-minute resolution means energy in kWh = power in kW * 0.5h
    specs = [
        {"name": "bat_reanimation", "section": "Reanimation/ICU", "priority": 1, "capacity_kwh": 200, "max_rate_kw": 60, "min_level": 0.10, "demand_kw": 35},
        {"name": "bat_bloc", "section": "Bloc Operatoire", "priority": 1, "capacity_kwh": 150, "max_rate_kw": 50, "min_level": 0.10, "demand_kw": 45},
        {"name": "bat_urgences", "section": "Urgences", "priority": 1, "capacity_kwh": 150, "max_rate_kw": 50, "min_level": 0.10, "demand_kw": 50},
        {"name": "bat_neonatologie", "section": "Neonatologie", "priority": 1, "capacity_kwh": 100, "max_rate_kw": 40, "min_level": 0.10, "demand_kw": 20},
        {"name": "bat_dialyse", "section": "Dialyse", "priority": 2, "capacity_kwh": 100, "max_rate_kw": 40, "min_level": 0.15, "demand_kw": 30},
        {"name": "bat_maternite", "section": "Maternite", "priority": 2, "capacity_kwh": 80, "max_rate_kw": 30, "min_level": 0.15, "demand_kw": 25},
        {"name": "bat_laboratoire", "section": "Laboratoire", "priority": 2, "capacity_kwh": 60, "max_rate_kw": 25, "min_level": 0.15, "demand_kw": 15},
        {"name": "bat_pharmacie", "section": "Pharmacie", "priority": 2, "capacity_kwh": 60, "max_rate_kw": 25, "min_level": 0.20, "demand_kw": 10},
        {"name": "bat_radiologie", "section": "Radiologie", "priority": 3, "capacity_kwh": 80, "max_rate_kw": 30, "min_level": 0.20, "demand_kw": 35},
        {"name": "bat_general", "section": "General", "priority": 5, "capacity_kwh": 200, "max_rate_kw": 60, "min_level": 0.25, "demand_kw": 80}
    ]
    
    # Initialize State
    for s in specs:
        s['current_charge_kwh'] = s['capacity_kwh'] * 0.85
        s['cycle_count'] = 0.0
        s['degradation_pct'] = 0.0
        s['usable_capacity_kwh'] = s['capacity_kwh']
        s['history'] = []

    # Constants
    TOTAL_BASE_DEMAND_KW = sum(s['demand_kw'] for s in specs)
    CHG_EFF = 0.95
    DIS_EFF = 0.97
    DEGRADATION_PER_CYCLE = 0.003 / 100.0 # 0.003%
    TIMESTEP_H = 0.5
    
    generator_to_batteries = {
        'g1': ['bat_reanimation', 'bat_bloc', 'bat_urgences', 'bat_neonatologie'],
        'g2': ['bat_dialyse', 'bat_maternite', 'bat_laboratoire', 'bat_pharmacie'],
        'g3': ['bat_radiologie'],
        'g4': ['bat_general'],
    }
    battery_to_generator = {}
    for gen, batteries in generator_to_batteries.items():
        for battery_name in batteries:
            battery_to_generator[battery_name] = gen

    # Simulation Loop
    for i in range(n_steps):
        is_outage = grid_df.iloc[i]['is_outage']
        solar_kw = solar_df.iloc[i]['net_solar_kw']
        wind_kw = wind_df.iloc[i]['net_wind_kw']
        
        # Reload generator timers for this timestep
        active_generators = {}
        for gen_id, gen_df in generator_states.items():
            if i < len(gen_df):
                active_generators[gen_id] = gen_df.iloc[i].to_dict()
        for s in specs:
            s['trade_flag'] = 0
            s['traded_kw'] = 0.0
            s['is_charging'] = 0
            s['is_discharging'] = 0
            s['charge_rate_kw'] = 0.0
            s['discharge_rate_kw'] = 0.0
        
        if is_outage == 0:
            # Grid ON: Charging
            surplus_kw = max(0, (solar_kw + wind_kw) - TOTAL_BASE_DEMAND_KW)
            
            # Charging priorities:
            # 1. P1 above 80%
            # 2. P2 above 60%
            # 3. Everyone to 100%
            
            charge_queues = [
                [s for s in specs if s['priority'] == 1 and (s['current_charge_kwh'] / s['usable_capacity_kwh']) < 0.8],
                [s for s in specs if s['priority'] == 2 and (s['current_charge_kwh'] / s['usable_capacity_kwh']) < 0.6],
                [s for s in specs if (s['current_charge_kwh'] / s['usable_capacity_kwh']) < 1.0]
            ]
            
            for queue in charge_queues:
                for s in queue:
                    target_pct = 0.8 if queue == charge_queues[0] else (0.6 if queue == charge_queues[1] else 1.0)
                    needed_kwh = max(0, (target_pct * s['usable_capacity_kwh']) - s['current_charge_kwh'])
                    if needed_kwh <= 0: continue
                    
                    # Max power we can pull into battery (in kW)
                    max_in_kw = min(s['max_rate_kw'], (needed_kwh / TIMESTEP_H) / CHG_EFF)
                    
                    # Try renewables first
                    from_renewables = min(max_in_kw, surplus_kw)
                    surplus_kw -= from_renewables
                    
                    # Remaining from grid
                    from_grid = max_in_kw - from_renewables
                    
                    total_chg_kw = from_renewables + from_grid
                    actual_energy_in = total_chg_kw * TIMESTEP_H * CHG_EFF
                    
                    s['current_charge_kwh'] += actual_energy_in
                    s['is_charging'] = 1
                    s['charge_rate_kw'] = total_chg_kw
                    # Update cycles
                    delta_cycles = actual_energy_in / (2.0 * s['usable_capacity_kwh'])
                    s['cycle_count'] += delta_cycles

        else:
            # Grid OFF: Discharging or generator-supported recharge
            # Each battery discharges for its own section unless its generator is running.
            for s in specs:
                demand_kw = s['demand_kw']
                battery_name = s['name']
                gen_id = battery_to_generator.get(battery_name)
                generator_running = False
                generator_output_kw = 0.0
                generator_recharge_kw = 0.0
                if gen_id and gen_id in active_generators:
                    gen_state = active_generators[gen_id]
                    if int(gen_state.get('is_running', 0)) == 1:
                        generator_running = True
                        generator_output_kw = float(gen_state.get('output_kw', 0.0))
                        generator_recharge_kw = 0.20 * generator_output_kw

                if generator_running and generator_recharge_kw > 0:
                    # Recharge covered battery from generator instead of discharging
                    max_charge_needed_kwh = max(0, s['usable_capacity_kwh'] - s['current_charge_kwh'])
                    max_charge_kw = min(s['max_rate_kw'], generator_recharge_kw)
                    actual_charge_kw = min(max_charge_kw, max_charge_needed_kwh / TIMESTEP_H / CHG_EFF)
                    if actual_charge_kw > 0:
                        energy_in = actual_charge_kw * TIMESTEP_H * CHG_EFF
                        s['current_charge_kwh'] += energy_in
                        s['is_charging'] = 1
                        s['charge_rate_kw'] = actual_charge_kw
                        s['discharge_rate_kw'] = 0.0
                        s['trade_flag'] = 0
                        s['traded_kw'] = 0.0
                        continue

                max_avail_kwh = max(0, s['current_charge_kwh'] - (s['min_level'] * s['usable_capacity_kwh']))
                max_avail_kw = (max_avail_kwh / TIMESTEP_H) * DIS_EFF

                actual_dis_kw = min(demand_kw, s['max_rate_kw'], max_avail_kw)
                s['discharge_rate_kw'] = actual_dis_kw
                if actual_dis_kw > 0:
                    s['is_discharging'] = 1
                    energy_out = (actual_dis_kw * TIMESTEP_H) / DIS_EFF
                    s['current_charge_kwh'] -= energy_out
                    # Update cycles
                    delta_cycles = energy_out / (2.0 * s['usable_capacity_kwh'])
                    s['cycle_count'] += delta_cycles
            
            # P2P Trading
            # High priority (low P number) sections can receive from lower priority
            # P5 -> P3 -> P2 -> P1
            priority_list = [1, 2, 3] # Receivers
            for target_p in priority_list:
                receivers = [s for s in specs if s['priority'] == target_p]
                for rc in receivers:
                    # Check if at min level and still has demand
                    if (rc['current_charge_kwh'] / rc['usable_capacity_kwh']) <= rc['min_level'] + 0.001:
                        deficit_kw = rc['demand_kw'] - rc['discharge_rate_kw']
                        if deficit_kw <= 0: continue
                        
                        # Look for donors (P value > target_p)
                        donors = [s for s in specs if s['priority'] > target_p]
                        # Sort donors by priority (highest P first: P5 then P3 then P2)
                        donors.sort(key=lambda x: x['priority'], reverse=True)
                        
                        for dn in donors:
                            # Buffer: min_level + 20%
                            donor_avail_kwh = max(0, dn['current_charge_kwh'] - ((dn['min_level'] + 0.20) * dn['usable_capacity_kwh']))
                            if donor_avail_kwh <= 0: continue
                            
                            max_trade_kw = min(20.0, deficit_kw, (donor_avail_kwh / TIMESTEP_H))
                            if max_trade_kw <= 0: continue
                            
                            # Execute trade
                            trade_energy_kwh = max_trade_kw * TIMESTEP_H
                            dn['current_charge_kwh'] -= trade_energy_kwh
                            # rc receives it - for this simulation, we'll assume it goes into the battery 
                            # and is immediately used, but we'll reflect it in the charge for the 'before' calculation
                            rc['current_charge_kwh'] += trade_energy_kwh
                            
                            dn['trade_flag'] = 1
                            dn['traded_kw'] += max_trade_kw
                            rc['trade_flag'] = -1
                            rc['traded_kw'] += max_trade_kw
                            
                            deficit_kw -= max_trade_kw
                            if deficit_kw <= 0: break

        # Update Health for all
        for s in specs:
            s['degradation_pct'] = s['cycle_count'] * DEGRADATION_PER_CYCLE * 100.0
            s['usable_capacity_kwh'] = s['capacity_kwh'] * (1.0 - s['degradation_pct'] / 100.0)
            
            # Record history
            pct = (s['current_charge_kwh'] / s['usable_capacity_kwh']) * 100.0
            
            # Status
            stat = "idle"
            if s['is_charging']: stat = "charging"
            elif s['is_discharging']: stat = "discharging"
            
            if s['trade_flag'] == 1: stat = "trading_donor"
            elif s['trade_flag'] == -1: stat = "trading_receiver"
            
            if pct < (s['min_level'] * 100.0 + 5.0): stat = "critical"
            if pct <= (s['min_level'] * 100.0 + 0.1): stat = "empty"
            
            s['history'].append({
                'timestamp': grid_df.iloc[i]['timestamp'],
                'charge_kwh': s['current_charge_kwh'],
                'charge_pct': pct,
                'charge_rate_kw': s['charge_rate_kw'],
                'discharge_rate_kw': s['discharge_rate_kw'],
                'is_charging': s['is_charging'],
                'is_discharging': s['is_discharging'],
                'is_outage': is_outage,
                'trade_flag': s['trade_flag'],
                'traded_kw': s['traded_kw'],
                'cycle_count': s['cycle_count'],
                'degradation_pct': s['degradation_pct'],
                'usable_capacity_kwh': s['usable_capacity_kwh'],
                'status': stat
            })

    # Save to CSV and Print Summary
    for s in specs:
        df_out = pd.DataFrame(s['history'])
        df_out.to_csv(output_dir / f"{s['name']}.csv", index=False)
        
        # Summary
        dis_hours = df_out['is_discharging'].sum() * 0.5
        trade_events = len(df_out[df_out['trade_flag'] != 0])
        min_soc = df_out['charge_pct'].min()
        hits_min = len(df_out[df_out['charge_pct'] <= (s['min_level'] * 100.0 + 0.1)])
        
        print(f"Summary for {s['name']}:")
        print(f"  Total Discharge Hours: {dis_hours:.1f}h")
        print(f"  P2P Trade Events: {trade_events}")
        print(f"  Lowest Charge Level: {min_soc:.2f}%")
        print(f"  Hits Min Safe Level: {hits_min} times")
        print(f"  Final Degradation: {s['degradation_pct']:.4f}%")
        print("-" * 30)

if __name__ == "__main__":
    generate_batteries()
