import pandas as pd
import numpy as np
from pathlib import Path
import math

# Optional bridge logging if available
try:
    from web3_bridge import HospitalBridge
except Exception:
    HospitalBridge = None


def find_maintenance_start(grid_df, solar_df, wind_df, window_steps=12):
    scores = []
    renewable_power = solar_df['net_solar_kw'] + wind_df['net_wind_kw']
    for start in range(0, len(grid_df) - window_steps + 1):
        window_outage = grid_df['is_outage'].iloc[start:start + window_steps].sum()
        if window_outage == 0:
            score = renewable_power.iloc[start:start + window_steps].sum()
            scores.append((score, start))
    if not scores:
        return None
    scores.sort(key=lambda x: x[0])
    return scores[0][1]


def build_generator_specs():
    return [
        {
            'id': 'g1',
            'name': 'Generator G1',
            'capacity_kw': 300.0,
            'fuel_hours': 48.0,
            'startup_delay_steps': 1,
            'maintenance_steps': 12,
            'covered_batteries': ['bat_reanimation', 'bat_bloc', 'bat_urgences', 'bat_neonatologie'],
            'comment': 'P1 sections',
            'min_outage_for_start': 1,
        },
        {
            'id': 'g2',
            'name': 'Generator G2',
            'capacity_kw': 200.0,
            'fuel_hours': 36.0,
            'startup_delay_steps': 1,
            'maintenance_steps': 12,
            'covered_batteries': ['bat_dialyse', 'bat_maternite', 'bat_laboratoire', 'bat_pharmacie'],
            'comment': 'P2 sections',
            'min_outage_for_start': 1,
        },
        {
            'id': 'g3',
            'name': 'Generator G3',
            'capacity_kw': 150.0,
            'fuel_hours': 24.0,
            'startup_delay_steps': 1,
            'maintenance_steps': 12,
            'covered_batteries': ['bat_radiologie'],
            'comment': 'P3 sections',
            'min_outage_for_start': 5,
        },
        {
            'id': 'g4',
            'name': 'Generator G4',
            'capacity_kw': 100.0,
            'fuel_hours': 12.0,
            'startup_delay_steps': 1,
            'maintenance_steps': 12,
            'covered_batteries': ['bat_general'],
            'comment': 'P4-P5 sections',
            'min_outage_for_start': 5,
        }
    ]


def get_battery_capacities():
    return {
        'bat_reanimation': 200.0,
        'bat_bloc': 150.0,
        'bat_urgences': 150.0,
        'bat_neonatologie': 100.0,
        'bat_dialyse': 100.0,
        'bat_maternite': 80.0,
        'bat_laboratoire': 60.0,
        'bat_pharmacie': 60.0,
        'bat_radiologie': 80.0,
        'bat_general': 200.0,
    }


def build_generator_status(status, fuel_pct, starting, running, maintenance):
    if maintenance:
        return 'maintenance'
    if fuel_pct <= 0:
        return 'fuel_empty'
    if starting:
        return 'starting'
    if running:
        if fuel_pct < 15:
            return 'running_fuel_critical'
        return 'running'
    return 'off'


def log_event(bridge, generator_id, event_type, fuel_level, output_kw):
    if not bridge:
        return
    try:
        bridge.log_generator_event(generator_id, event_type, int(fuel_level), int(output_kw))
    except Exception as e:
        print(f"Generator event logging failed: {e}")


def generate_generators():
    np.random.seed(42)

    base_path = Path(__file__).parent.parent
    grid_file = base_path / 'data' / 'supply' / 'grid_supply.csv'
    weather_file = base_path / 'data' / 'weather' / 'meteo_casablanca.csv'
    battery_dir = base_path / 'data' / 'batteries'
    output_dir = base_path / 'data' / 'supply' / 'generators'
    output_dir.mkdir(parents=True, exist_ok=True)

    grid_df = pd.read_csv(grid_file)
    weather_df = pd.read_csv(weather_file)

    specs = build_generator_specs()
    battery_caps = get_battery_capacities()

    # Initial battery state is needed to support generator decisions
    battery_rows = {}
    for name, capacity in battery_caps.items():
        file_path = battery_dir / f'{name}.csv'
        if file_path.exists():
            df = pd.read_csv(file_path)
            if 'charge_pct' in df.columns:
                battery_rows[name] = df['charge_pct'].fillna(100.0).values
            else:
                battery_rows[name] = np.full(len(grid_df), 100.0)
        else:
            battery_rows[name] = np.full(len(grid_df), 100.0)

    bridge = None
    if HospitalBridge:
        try:
            bridge = HospitalBridge()
        except Exception as e:
            print(f"Bridge unavailable for generator logging: {e}")
            bridge = None

    # Assign maintenance windows outside outages in low renewable periods
    for spec in specs:
        start = find_maintenance_start(grid_df, pd.read_csv(base_path / 'data' / 'supply' / 'solar_supply.csv'), pd.read_csv(base_path / 'data' / 'supply' / 'wind_supply.csv'), window_steps=spec['maintenance_steps'])
        spec['maintenance_start'] = start
        spec['maintenance_end'] = start + spec['maintenance_steps'] if start is not None else None

    histories = {spec['id']: [] for spec in specs}
    state = {}
    for spec in specs:
        state[spec['id']] = {
            'fuel_level_pct': 100.0,
            'running': False,
            'starting': False,
            'maintenance': False,
            'maintenance_steps_remaining': 0,
            'activation_count': 0,
            'last_status': 'off',
            'outage_activations': 0,
            'startup_delay_active': False,
        }

    outage_run = 0
    for i in range(len(grid_df)):
        is_outage = int(grid_df.iloc[i]['is_outage'])
        temp_c = float(weather_df.iloc[i].get('temperature_2m', 25.0))
        temp_derate = max(0.0, 1.0 - max(0.0, temp_c - 35.0) * 0.008)

        if is_outage == 1:
            outage_run += 1
        else:
            outage_run = 0

        for spec in specs:
            st = state[spec['id']]
            fuel_pct = st['fuel_level_pct']
            running = st['running']
            starting = False
            maintenance = st['maintenance']
            output_kw = 0.0
            fuel_consumed_kwh = 0.0
            startup_delay_active = 0
            fuel_critical = fuel_pct < 15.0

            if maintenance:
                st['maintenance_steps_remaining'] -= 1
                if st['maintenance_steps_remaining'] <= 0:
                    maintenance = False
                    st['maintenance'] = False
                    st['maintenance_steps_remaining'] = 0
                    log_event(bridge, list(state.keys()).index(spec['id']) + 1, 'stopped', fuel_pct, 0)
                else:
                    maintenance = True
            elif is_outage == 0:
                if running or st['starting']:
                    log_event(bridge, list(state.keys()).index(spec['id']) + 1, 'stopped', fuel_pct, 0)
                running = False
                st['running'] = False
                st['starting'] = False
                st['startup_delay_active'] = False
                if fuel_pct < 100:
                    st['fuel_level_pct'] = min(100.0, fuel_pct + 2.5)
                fuel_pct = st['fuel_level_pct']
            else:
                # Outage conditions
                if spec['maintenance_start'] is not None and i == spec['maintenance_start']:
                    maintenance = True
                    st['maintenance'] = True
                    st['maintenance_steps_remaining'] = spec['maintenance_steps']
                    log_event(bridge, list(state.keys()).index(spec['id']) + 1, 'maintenance', fuel_pct, 0)
                elif st['maintenance_steps_remaining'] > 0:
                    maintenance = True
                elif fuel_pct <= 0:
                    running = False
                    st['running'] = False
                    st['starting'] = False
                else:
                    can_start = outage_run >= spec['min_outage_for_start']
                    if not running:
                        if outage_run == spec['min_outage_for_start']:
                            starting = True
                            st['starting'] = True
                            startup_delay_active = 1
                        elif outage_run > spec['min_outage_for_start'] and spec['min_outage_for_start'] > 1:
                            starting = False
                            st['starting'] = False
                            running = True
                        elif outage_run > spec['min_outage_for_start'] and spec['min_outage_for_start'] == 1:
                            running = True
                            st['starting'] = False
                        elif st['starting'] and outage_run > spec['min_outage_for_start']:
                            running = True
                            st['starting'] = False
                        elif st['starting'] and outage_run == spec['min_outage_for_start']:
                            starting = True
                            startup_delay_active = 1
                    if running and not maintenance and fuel_pct > 0:
                        output_kw = spec['capacity_kw'] * temp_derate
                        fuel_consumed_kwh = output_kw * 0.5
                        fuel_pct = max(0.0, fuel_pct - (fuel_consumed_kwh / (spec['capacity_kw'] * spec['fuel_hours']) * 100.0))
                        st['fuel_level_pct'] = fuel_pct
                        if st['last_status'] not in ['running', 'running_fuel_critical']:
                            st['activation_count'] += 1
                            log_event(bridge, list(state.keys()).index(spec['id']) + 1, 'started', fuel_pct, output_kw)
                    elif starting:
                        startup_delay_active = 1
                        if not st['running'] and not st['maintenance']:
                            st['starting'] = True
                    else:
                        running = False
                        st['running'] = False
                        st['starting'] = False
                        st['startup_delay_active'] = False

            if st['maintenance'] and not maintenance:
                st['maintenance'] = False

            if running and not st['running']:
                st['running'] = True
            if not running and st['running']:
                st['running'] = False

            status = build_generator_status('', fuel_pct, st['starting'], st['running'], maintenance)
            if status == 'running_fuel_critical':
                fuel_critical = True

            histories[spec['id']].append({
                'timestamp': grid_df.iloc[i]['timestamp'],
                'is_running': int(st['running']),
                'output_kw': round(output_kw, 2),
                'fuel_level_pct': round(fuel_pct, 2),
                'fuel_consumed_kwh': round(fuel_consumed_kwh, 2),
                'temp_derating_factor': round(temp_derate, 3),
                'is_maintenance': int(maintenance),
                'fuel_critical': int(fuel_pct < 15.0),
                'startup_delay_active': startup_delay_active,
                'status': status,
            })
            st['last_status'] = status
            st['startup_delay_active'] = startup_delay_active

    # Save CSV outputs and print summary
    for spec in specs:
        df_out = pd.DataFrame(histories[spec['id']])
        file_path = output_dir / f'generator_{spec['id']}.csv'
        df_out.to_csv(file_path, index=False)

        runtime_hours = df_out['is_running'].sum() * 0.5
        fuel_critical_events = df_out[df_out['fuel_critical'] == 1].shape[0]
        maintenance_steps = df_out[df_out['is_maintenance'] == 1].shape[0]
        activations = int((df_out['status'] == 'running').astype(int).diff().fillna(0).gt(0).sum())

        print(f"{spec['name']} Summary:")
        print(f"  Total Runtime: {runtime_hours:.1f} hours")
        print(f"  Fuel Critical Timesteps: {fuel_critical_events}")
        print(f"  Maintenance Timesteps: {maintenance_steps}")
        print(f"  Activations: {activations}")
        print("-" * 40)


if __name__ == '__main__':
    generate_generators()
