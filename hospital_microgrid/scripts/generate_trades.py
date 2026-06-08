import hashlib
from pathlib import Path

import numpy as np
import pandas as pd


def get_battery_specs():
    return {
        'bat_reanimation': {'section': 'Reanimation/ICU', 'priority': 1, 'capacity_kwh': 200.0},
        'bat_bloc': {'section': 'Bloc Operatoire', 'priority': 1, 'capacity_kwh': 150.0},
        'bat_urgences': {'section': 'Urgences', 'priority': 1, 'capacity_kwh': 150.0},
        'bat_neonatologie': {'section': 'Neonatologie', 'priority': 1, 'capacity_kwh': 100.0},
        'bat_dialyse': {'section': 'Dialyse', 'priority': 2, 'capacity_kwh': 100.0},
        'bat_maternite': {'section': 'Maternite', 'priority': 2, 'capacity_kwh': 80.0},
        'bat_laboratoire': {'section': 'Laboratoire', 'priority': 2, 'capacity_kwh': 60.0},
        'bat_pharmacie': {'section': 'Pharmacie', 'priority': 2, 'capacity_kwh': 60.0},
        'bat_radiologie': {'section': 'Radiologie', 'priority': 3, 'capacity_kwh': 80.0},
        'bat_general': {'section': 'General', 'priority': 5, 'capacity_kwh': 200.0},
    }


def load_generator_state(base_path):
    generator_dir = base_path / 'data' / 'supply' / 'generators'
    generator_files = {
        'g1': generator_dir / 'generator_g1.csv',
        'g2': generator_dir / 'generator_g2.csv',
        'g3': generator_dir / 'generator_g3.csv',
        'g4': generator_dir / 'generator_g4.csv',
    }
    generators = {}
    for gen_id, path in generator_files.items():
        if path.exists():
            generators[gen_id] = pd.read_csv(path)
    return generators


def get_trade_amount(receiver_pct, receiver_capacity_kwh, threshold):
    if receiver_pct >= threshold:
        return 0.0
    needed_kwh = max(0.0, (threshold - receiver_pct) / 100.0 * receiver_capacity_kwh)
    return min(15.0, max(2.0, needed_kwh / 0.5))


def get_donor_available_kw(donor_pct, donor_capacity_kwh):
    if donor_pct <= 40:
        return 0.0
    available_kwh = (donor_pct - 40.0) / 100.0 * donor_capacity_kwh
    return available_kwh / 0.5


def choose_donor(receivers, battery_data, battery_specs):
    donors = [b for b in battery_data if battery_specs[b]['priority'] > receivers['priority']]
    donors = sorted(donors, key=lambda b: battery_specs[b]['priority'], reverse=True)
    for donor in donors:
        donor_pct = battery_data[donor]['df'].iloc[receivers['index']]['charge_pct']
        avail_kw = get_donor_available_kw(donor_pct, battery_specs[donor]['capacity_kwh'])
        if avail_kw >= 2.0:
            return donor
    return None


def create_trade_record(trade_id, timestamp, donor_name, receiver_name, donor_info, receiver_info, amount_kw, scenario):
    cost_saving_eur = amount_kw * 0.5 * 1.2
    hash_input = f"{trade_id}{timestamp}{donor_info['section']}{receiver_info['section']}{amount_kw}{scenario}"
    blockchain_hash = '0x' + hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    return {
        'trade_id': trade_id,
        'timestamp': timestamp,
        'donor_section': donor_info['section'],
        'donor_priority': f"P{donor_info['priority']}",
        'donor_charge_pct_before': round(float(donor_info['pct']), 2),
        'receiver_section': receiver_info['section'],
        'receiver_priority': f"P{receiver_info['priority']}",
        'receiver_charge_pct_before': round(float(receiver_info['pct']), 2),
        'traded_kw': round(amount_kw, 2),
        'trade_scenario': scenario,
        'cost_saving_eur': round(cost_saving_eur, 2),
        'blockchain_hash': blockchain_hash,
    }


def generate_trades():
    np.random.seed(42)

    base_path = Path(__file__).parent.parent
    grid_file = base_path / 'data' / 'supply' / 'grid_supply.csv'
    battery_dir = base_path / 'data' / 'batteries'
    output_file = base_path / 'data' / 'trades' / 'energy_trades.csv'
    output_file.parent.mkdir(parents=True, exist_ok=True)

    grid_df = pd.read_csv(grid_file)
    battery_specs = get_battery_specs()
    battery_data = {}
    for battery_name, spec in battery_specs.items():
        file_path = battery_dir / f'{battery_name}.csv'
        if file_path.exists():
            df = pd.read_csv(file_path)
            battery_data[battery_name] = {
                'df': df,
                'section': spec['section'],
                'priority': spec['priority'],
                'capacity_kwh': spec['capacity_kwh'],
            }

    generators = load_generator_state(base_path)
    outages = grid_df['is_outage'].astype(int).values

    def outage_start(i):
        return outages[i] == 1 and (i == 0 or outages[i - 1] == 0)

    def outage_run_length(i):
        length = 0
        while i + length < len(outages) and outages[i + length] == 1:
            length += 1
        return length

    trade_rows = []
    trade_id = 1

    # Build generator coverage mapping
    gen_coverage = {
        'g1': ['bat_reanimation', 'bat_bloc', 'bat_urgences', 'bat_neonatologie'],
        'g2': ['bat_dialyse', 'bat_maternite', 'bat_laboratoire', 'bat_pharmacie'],
        'g3': ['bat_radiologie'],
        'g4': ['bat_general'],
    }
    battery_to_gen = {battery: gen for gen, batteries in gen_coverage.items() for battery in batteries}

    for i in range(len(grid_df)):
        if outages[i] == 0:
            continue

        timestamp = grid_df.iloc[i]['timestamp']
        current_charges = {
            name: float(data['df'].iloc[i]['charge_pct'])
            for name, data in battery_data.items()
        }

        # Scenario A: Startup gap for P1
        if outage_start(i):
            p1_candidates = [name for name, data in battery_data.items() if data['priority'] == 1]
            critical_p1 = [name for name in p1_candidates if current_charges[name] < 25.0]
            if critical_p1:
                receiver_name = min(critical_p1, key=lambda n: current_charges[n])
                receiver_info = {
                    'section': battery_data[receiver_name]['section'],
                    'priority': battery_data[receiver_name]['priority'],
                    'pct': current_charges[receiver_name],
                    'index': i,
                }
                donor_name = choose_donor(receiver_info, battery_data, battery_specs)
                if donor_name:
                    amount_kw = get_trade_amount(current_charges[receiver_name], battery_data[receiver_name]['capacity_kwh'], 35.0)
                    if amount_kw > 0:
                        donor_info = {
                            'section': battery_data[donor_name]['section'],
                            'priority': battery_data[donor_name]['priority'],
                            'pct': current_charges[donor_name],
                            'index': i,
                        }
                        trade_rows.append(create_trade_record(trade_id, timestamp, donor_name, receiver_name, donor_info, receiver_info, amount_kw, 'startup_gap'))
                        trade_id += 1

        # Generator state default values
        generator_running = {gen: False for gen in gen_coverage}
        generator_output = {gen: 0.0 for gen in gen_coverage}
        generator_fuel = {gen: 100.0 for gen in gen_coverage}
        for gen_id, df in generators.items():
            if i < len(df):
                row = df.iloc[i]
                generator_running[gen_id] = int(row.get('is_running', 0)) == 1
                generator_output[gen_id] = float(row.get('output_kw', 0.0))
                generator_fuel[gen_id] = float(row.get('fuel_level_pct', 100.0))

        # Scenario B, C, D: Evaluate each generator coverage group
        for gen_id, covered in gen_coverage.items():
            gen_on = generator_running.get(gen_id, False)
            gen_cap = float(generators[gen_id].iloc[i]['output_kw']) if gen_id in generators and i < len(generators[gen_id]) else 0.0
            fuel_pct = generator_fuel.get(gen_id, 100.0)
            covered_batteries = covered

            for battery_name in covered_batteries:
                pct = current_charges[battery_name]
                receiver_info = {
                    'section': battery_data[battery_name]['section'],
                    'priority': battery_data[battery_name]['priority'],
                    'pct': pct,
                    'index': i,
                }
                donor_name = choose_donor(receiver_info, battery_data, battery_specs)
                if donor_name is None:
                    continue
                donor_info = {
                    'section': battery_data[donor_name]['section'],
                    'priority': battery_data[donor_name]['priority'],
                    'pct': current_charges[donor_name],
                    'index': i,
                }

                # Scenario B: Generator failure
                if not gen_on and pct < 30.0:
                    amount_kw = get_trade_amount(pct, battery_data[battery_name]['capacity_kwh'], 35.0)
                    if amount_kw > 0:
                        trade_rows.append(create_trade_record(trade_id, timestamp, donor_name, battery_name, donor_info, receiver_info, amount_kw, 'generator_failure'))
                        trade_id += 1
                        continue

                # Scenario C: Partial coverage
                if gen_on and gen_cap < 0.6 * battery_data[battery_name]['capacity_kwh'] and i > 0:
                    prev_pct = float(battery_data[battery_name]['df'].iloc[i - 1]['charge_pct'])
                    if pct < prev_pct:
                        amount_kw = get_trade_amount(pct, battery_data[battery_name]['capacity_kwh'], 40.0)
                        if amount_kw > 0:
                            trade_rows.append(create_trade_record(trade_id, timestamp, donor_name, battery_name, donor_info, receiver_info, amount_kw, 'partial_coverage'))
                            trade_id += 1
                            continue

                # Scenario D: Fuel critical bridge
                if fuel_pct < 15.0 and pct < 40.0:
                    amount_kw = get_trade_amount(pct, battery_data[battery_name]['capacity_kwh'], 45.0)
                    if amount_kw > 0:
                        trade_rows.append(create_trade_record(trade_id, timestamp, donor_name, battery_name, donor_info, receiver_info, amount_kw, 'fuel_critical_bridge'))
                        trade_id += 1
                        continue

    trades_df = pd.DataFrame(trade_rows)
    if trades_df.empty:
        trades_df = pd.DataFrame(columns=[
            'trade_id', 'timestamp', 'donor_section', 'donor_priority',
            'donor_charge_pct_before', 'receiver_section', 'receiver_priority',
            'receiver_charge_pct_before', 'traded_kw', 'trade_scenario',
            'cost_saving_eur', 'blockchain_hash'
        ])
    trades_df.to_csv(output_file, index=False)

    print(f"Energy Trades Generation Complete: {output_file}")
    print(f"Total Number of Trades: {len(trades_df)}")
    total_kwh = (trades_df['traded_kw'] * 0.5).sum() if not trades_df.empty else 0.0
    total_savings = trades_df['cost_saving_eur'].sum() if not trades_df.empty else 0.0
    print(f"Total Energy Traded: {total_kwh:.2f} kWh")
    print(f"Total Cost Saved: {total_savings:.2f} MAD")

    if not trades_df.empty:
        print("\nTrades by Scenario:")
        print(trades_df['trade_scenario'].value_counts().to_string())
        print("\nFirst 10 rows of the trades file:")
        print(trades_df.head(10).to_string(index=False))
    else:
        print("No trades found.")


if __name__ == '__main__':
    generate_trades()
