"""
generate_generators.py — Diesel Generator Simulation
=====================================================
Creates 4 generator CSV files in data/supply/generators/:
  generator_g1.csv, generator_g2.csv, generator_g3.csv, generator_g4.csv

Each file simulates the generator state at every 30-minute timestep,
including fuel depletion, temperature derating, startup delays,
planned maintenance windows, and fuel-critical alerts.

3-Layer Resilience Hierarchy:
  Layer 1 — Renewables (solar + wind): FREE, always used first
  Layer 2 — Generators: reliable but cost diesel fuel
  Layer 3 — P2P battery trading: uses already-stored energy, costs nothing
"""

import pandas as pd
import numpy as np
from pathlib import Path


def generate_generators():
    np.random.seed(42)

    # ── Paths ──────────────────────────────────────────────────────────
    base_path = Path(__file__).parent.parent
    weather_file = base_path / "data" / "weather" / "meteo_casablanca.csv"
    grid_file = base_path / "data" / "supply" / "grid_supply.csv"
    output_dir = base_path / "data" / "supply" / "generators"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  GENERATOR SIMULATION")
    print("=" * 60)
    print("\nLoading input data...")
    weather_df = pd.read_csv(weather_file)
    grid_df = pd.read_csv(grid_file)
    n_steps = len(grid_df)
    print(f"  Weather rows: {len(weather_df)}")
    print(f"  Grid rows:    {n_steps}")

    # ── Generator specifications ───────────────────────────────────────
    #
    # outage_threshold: how many consecutive outage timesteps before
    #   the generator begins its startup sequence.
    #   G1/G2: 1 (start immediately on first outage timestep)
    #   G3/G4: 5 (start after outage has lasted > 4 timesteps = 2 hours)
    #
    TIMESTEP_H = 0.5                    # each timestep = 30 minutes
    FUEL_REFILL_PCT_PER_STEP = 2.5      # 5%/hour × 0.5h = 2.5%/step

    specs = [
        {"id": "g1", "capacity_kw": 300, "fuel_hours": 48,
         "outage_threshold": 1, "covers": "P1 (Rea, Bloc, Urg, Neo)"},
        {"id": "g2", "capacity_kw": 200, "fuel_hours": 36,
         "outage_threshold": 1, "covers": "P2 (Dial, Mat, Lab, Phar)"},
        {"id": "g3", "capacity_kw": 150, "fuel_hours": 24,
         "outage_threshold": 5, "covers": "P3 (Radio, Med Int)"},
        {"id": "g4", "capacity_kw": 100, "fuel_hours": 12,
         "outage_threshold": 5, "covers": "P4-P5 (Consult, Admin, Gen)"},
    ]

    for s in specs:
        s["fuel_duration_steps"] = int(s["fuel_hours"] / TIMESTEP_H)
        s["fuel_pct_per_step"] = 100.0 / s["fuel_duration_steps"]

    # ── Input arrays ───────────────────────────────────────────────────
    is_outage = grid_df["is_outage"].values.astype(int)
    timestamps = grid_df["timestamp"].values

    temperatures = weather_df["temperature_2m"].values
    solar_pot = weather_df["solar_potential"].values
    wind_pot = weather_df["wind_potential"].values

    # Pad to match grid length if needed
    def pad_array(arr, target_len):
        if len(arr) >= target_len:
            return arr[:target_len]
        return np.pad(arr, (0, target_len - len(arr)), mode="edge")

    temperatures = pad_array(temperatures, n_steps)
    solar_pot = pad_array(solar_pot, n_steps)
    wind_pot = pad_array(wind_pot, n_steps)

    # ── Schedule planned maintenance ───────────────────────────────────
    # 1 maintenance per year (12 timesteps = 6 hours each)
    # Scheduled during low-solar, low-wind periods with NO outage
    MAINTENANCE_DURATION = 12
    half = n_steps // 2

    def find_maintenance_slot(range_start, range_end, seed_offset):
        """Find one maintenance window in [range_start, range_end)."""
        rng = np.random.RandomState(42 + seed_offset)
        candidates = []
        for start in range(range_start, min(range_end, n_steps) - MAINTENANCE_DURATION):
            window = slice(start, start + MAINTENANCE_DURATION)
            if np.any(is_outage[window]):
                continue
            score = solar_pot[window].mean() + wind_pot[window].mean()
            candidates.append((score, start))
        if not candidates:
            return None
        candidates.sort()
        top = min(100, len(candidates))
        return candidates[rng.randint(0, top)][1]

    all_maintenance = {}
    for gi, s in enumerate(specs):
        maint_steps = set()
        for year_idx, (r_start, r_end) in enumerate([(0, half), (half, n_steps)]):
            slot = find_maintenance_slot(r_start, r_end, gi * 10 + year_idx)
            if slot is not None:
                for t in range(slot, min(slot + MAINTENANCE_DURATION, n_steps)):
                    maint_steps.add(t)
        all_maintenance[s["id"]] = maint_steps

    # ── Simulate each generator ────────────────────────────────────────
    print("\nRunning timestep-by-timestep simulation...")

    for s in specs:
        gen_id = s["id"]
        capacity = s["capacity_kw"]
        fuel_pct_per_step = s["fuel_pct_per_step"]
        outage_threshold = s["outage_threshold"]
        maintenance_set = all_maintenance[gen_id]

        # State variables
        fuel_level = 100.0
        is_running = False
        starting_timer = 0          # 0 = not starting; > 0 = countdown
        failed_timer = 0            # > 0 = generator failed and undergoing repairs
        consecutive_outage = 0
        activation_count = 0

        history = []

        for i in range(n_steps):
            outage = is_outage[i]
            temp = temperatures[i]
            in_maint = (i in maintenance_set)

            # Track consecutive outage length
            if outage == 1:
                consecutive_outage += 1
            else:
                consecutive_outage = 0

            # Temperature derating: -0.8% per °C above 35°C
            derating = max(0.0, 1.0 - 0.008 * max(0.0, temp - 35.0))

            # ── State machine ──────────────────────────────────────

            if failed_timer > 0:
                failed_timer -= 1
                is_running = False
                starting_timer = 0
                output_kw = 0.0
                fuel_consumed = 0.0
                is_maint_flag = 0
                startup_flag = 0
                status = "failed"
                # Can still refill fuel if grid is back ON
                if outage == 0:
                    fuel_level = min(100.0, fuel_level + FUEL_REFILL_PCT_PER_STEP)

            # CASE 1: Grid is ON → generator off, refill fuel
            elif outage == 0:
                was_running = is_running
                is_running = False
                starting_timer = 0
                fuel_level = min(100.0, fuel_level + FUEL_REFILL_PCT_PER_STEP)

                output_kw = 0.0
                fuel_consumed = 0.0
                is_maint_flag = 1 if in_maint else 0
                startup_flag = 0
                status = "maintenance" if in_maint else "off"

            # CASE 2: Outage but fuel is empty
            elif fuel_level <= 0:
                is_running = False
                starting_timer = 0
                fuel_level = 0.0

                output_kw = 0.0
                fuel_consumed = 0.0
                is_maint_flag = 0
                startup_flag = 0
                status = "fuel_empty"

            # CASE 3: Outage, generator currently running
            elif is_running:
                output_kw = capacity * derating
                fuel_level -= fuel_pct_per_step
                fuel_consumed = output_kw * TIMESTEP_H

                is_maint_flag = 0
                startup_flag = 0

                if fuel_level <= 0:
                    fuel_level = 0.0
                    is_running = False
                    output_kw = 0.0
                    fuel_consumed = 0.0
                    status = "fuel_empty"
                elif fuel_level < 15:
                    status = "running_fuel_critical"
                else:
                    status = "running"

            # CASE 4: Outage, generator starting up (countdown)
            elif starting_timer > 0:
                starting_timer -= 1
                if starting_timer == 0:
                    # Startup complete → start running THIS timestep
                    is_running = True
                    activation_count += 1
                    output_kw = capacity * derating
                    fuel_level -= fuel_pct_per_step
                    fuel_consumed = output_kw * TIMESTEP_H

                    if fuel_level <= 0:
                        fuel_level = 0.0
                        is_running = False
                        output_kw = 0.0
                        fuel_consumed = 0.0
                        status = "fuel_empty"
                    elif fuel_level < 15:
                        status = "running_fuel_critical"
                    else:
                        status = "running"
                    startup_flag = 0
                else:
                    output_kw = 0.0
                    fuel_consumed = 0.0
                    startup_flag = 1
                    status = "starting"

                is_maint_flag = 0

            # CASE 5: Outage, generator off, check if should start
            else:
                output_kw = 0.0
                fuel_consumed = 0.0
                is_maint_flag = 0

                if consecutive_outage >= outage_threshold:
                    # 15% chance to fail on the very first attempt to start
                    if consecutive_outage == outage_threshold and np.random.rand() < 0.15:
                        failed_timer = np.random.randint(6, 16) # Repair takes 3 to 8 hours (6-15 timesteps)
                        status = "failed"
                        startup_flag = 0
                    else:
                        # Begin startup sequence (1 timestep delay)
                        starting_timer = 1
                        startup_flag = 1
                        status = "starting"
                else:
                    startup_flag = 0
                    status = "off"

            # ── Record state ───────────────────────────────────────
            history.append({
                "timestamp":            timestamps[i],
                "is_running":           1 if is_running else 0,
                "output_kw":            round(output_kw, 2),
                "fuel_level_pct":       round(max(0.0, fuel_level), 2),
                "fuel_consumed_kwh":    round(fuel_consumed, 2),
                "temp_derating_factor": round(derating, 4),
                "is_maintenance":       is_maint_flag,
                "fuel_critical":        1 if 0 < fuel_level < 15 else 0,
                "startup_delay_active": startup_flag,
                "status":               status,
            })

        # ── Save CSV ───────────────────────────────────────────────
        df_out = pd.DataFrame(history)
        output_file = output_dir / f"generator_{gen_id}.csv"
        df_out.to_csv(output_file, index=False)

        # ── Validation summary ─────────────────────────────────────
        runtime_hours = df_out["is_running"].sum() * TIMESTEP_H
        fuel_critical_count = int(df_out["fuel_critical"].sum())
        maint_count = int(df_out["is_maintenance"].sum())
        starting_count = int(df_out["startup_delay_active"].sum())
        failed_count = len(df_out[df_out["status"] == "failed"])
        status_counts = df_out["status"].value_counts()

        print(f"\n{'-' * 50}")
        print(f"Generator {gen_id.upper()} - {s['covers']}")
        print(f"{'-' * 50}")
        print(f"  Capacity:            {capacity} kW")
        print(f"  Fuel tank:           {s['fuel_hours']}h ({s['fuel_duration_steps']} timesteps)")
        print(f"  Outage threshold:    {outage_threshold} timestep(s)")
        print(f"  Total runtime:       {runtime_hours:.1f} hours ({df_out['is_running'].sum()} timesteps)")
        print(f"  Activations:         {activation_count}")
        print(f"  Fuel critical steps: {fuel_critical_count}")
        print(f"  Maintenance steps:   {maint_count}")
        print(f"  Starting steps:      {starting_count}")
        print(f"  Failed steps:        {failed_count}")
        print(f"  Status breakdown:")
        for st_label, count in status_counts.items():
            print(f"    {st_label:30s} {count:6d} ({count/n_steps*100:.2f}%)")
        print(f"  Saved: {output_file}")

    print(f"\n{'=' * 60}")
    print(f"  Generator simulation complete — {len(specs)} files written")
    print(f"  Output directory: {output_dir}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    generate_generators()
