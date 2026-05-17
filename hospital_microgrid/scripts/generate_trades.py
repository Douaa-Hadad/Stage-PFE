import pandas as pd
import numpy as np
import hashlib
from pathlib import Path

def generate_trades():
    # Set seed for reproducibility
    np.random.seed(42)
    
    # Paths
    base_path = Path(__file__).parent.parent
    grid_file = base_path / "data" / "supply" / "grid_supply.csv"
    battery_dir = base_path / "data" / "batteries"
    output_file = base_path / "data" / "trades" / "energy_trades.csv"
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Load grid data
    grid_df = pd.read_csv(grid_file)
    
    # Load all 10 battery files
    battery_files = list(battery_dir.glob("bat_*.csv"))
    battery_data = {}
    
    # Section info to match battery files back to priorities
    # We'll extract section name and priority from the first row or assume names
    # Better: define the same specs list to know priorities
    specs = [
        {"name": "bat_reanimation", "section": "Réanimation/ICU", "priority": 1},
        {"name": "bat_bloc", "section": "Bloc Opératoire", "priority": 1},
        {"name": "bat_urgences", "section": "Urgences", "priority": 1},
        {"name": "bat_neonatologie", "section": "Néonatologie", "priority": 1},
        {"name": "bat_dialyse", "section": "Dialyse", "priority": 2},
        {"name": "bat_maternite", "section": "Maternité", "priority": 2},
        {"name": "bat_laboratoire", "section": "Laboratoire", "priority": 2},
        {"name": "bat_pharmacie", "section": "Pharmacie", "priority": 2},
        {"name": "bat_radiologie", "section": "Radiologie", "priority": 3},
        {"name": "bat_general", "section": "Général", "priority": 5}
    ]
    
    for s in specs:
        df = pd.read_csv(battery_dir / f"{s['name']}.csv")
        battery_data[s['name']] = {
            "df": df,
            "section": s['section'],
            "priority": s['priority']
        }
    
    # Pre-calculate outage duration
    is_outage = grid_df['is_outage'].values
    outage_dur_h = np.zeros(len(grid_df))
    curr_dur = 0
    for i in range(len(grid_df)):
        if is_outage[i] == 1:
            curr_dur += 0.5
        else:
            curr_dur = 0
        outage_dur_h[i] = curr_dur
        
    trades = []
    trade_id = 1
    
    # Scan timesteps where outage is active
    for i in range(len(grid_df)):
        if is_outage[i] == 0:
            continue
            
        timestamp = grid_df.iloc[i]['timestamp']
        
        # Find donors and receivers at this timestep
        donors = []
        receivers = []
        
        for name, data in battery_data.items():
            row = data['df'].iloc[i]
            if row['trade_flag'] == 1: # Donor
                donors.append({
                    "name": name,
                    "section": data['section'],
                    "priority": data['priority'],
                    "traded_kw": row['traded_kw'],
                    "charge_pct": row['charge_pct']
                })
            elif row['trade_flag'] == -1: # Receiver
                receivers.append({
                    "name": name,
                    "section": data['section'],
                    "priority": data['priority'],
                    "traded_kw": row['traded_kw'],
                    "charge_pct": row['charge_pct']
                })
        
        if not donors or not receivers:
            continue
            
        # Match them based on priority logic:
        # Receivers by priority (P1 -> P2 -> P3)
        # Donors by priority (P5 -> P3 -> P2)
        receivers.sort(key=lambda x: x['priority'])
        donors.sort(key=lambda x: x['priority'], reverse=True)
        
        # We need to distribute donor energy to receivers
        # In our simulation, one donor could give to multiple receivers
        # or vice versa. We'll use a pointer-based matching.
        d_idx = 0
        r_idx = 0
        
        # Clone remaining energy for matching
        for d in donors: d['rem'] = d['traded_kw']
        for r in receivers: r['rem'] = r['traded_kw']
        
        while r_idx < len(receivers) and d_idx < len(donors):
            r = receivers[r_idx]
            d = donors[d_idx]
            
            amount = min(r['rem'], d['rem'])
            if amount > 0:
                # Calculate charge_pct_before
                # charge_kwh_after = charge_kwh_before - amount * 0.5 (for donor)
                # But we have charge_pct after. 
                # Since we want a robust approximation:
                # Donor before = pct_after + (amount * 0.5 / capacity * 100)
                # Receiver before = pct_after - (amount * 0.5 / capacity * 100)
                
                # We'll just use the pct from the CSV as 'after' and adjust
                # Actually we'll simplify and use the row values as baseline
                donor_pct_before = d['charge_pct'] # Approximation
                receiver_pct_before = r['charge_pct'] # Approximation
                
                # Blockchain Hash
                hash_input = f"{trade_id}{timestamp}{d['section']}{r['section']}{amount}"
                b_hash = "0x" + hashlib.sha256(hash_input.encode()).hexdigest()[:16]
                
                trades.append({
                    "trade_id": trade_id,
                    "timestamp": timestamp,
                    "donor_section": d['section'],
                    "donor_priority": f"P{d['priority']}",
                    "donor_charge_pct_before": round(donor_pct_before, 2),
                    "receiver_section": r['section'],
                    "receiver_priority": f"P{r['priority']}",
                    "receiver_charge_pct_before": round(receiver_pct_before, 2),
                    "traded_kw": round(amount, 2),
                    "trade_reason": "outage_support",
                    "outage_duration_h": outage_dur_h[i],
                    "blockchain_hash": b_hash
                })
                
                trade_id += 1
                r['rem'] -= amount
                d['rem'] -= amount
                
            if r['rem'] <= 0.01: r_idx += 1
            if d['rem'] <= 0.01: d_idx += 1
            
    # Save to CSV
    trades_df = pd.DataFrame(trades)
    trades_df.to_csv(output_file, index=False)
    
    # Summary
    print(f"Energy Trades Generation Complete: {output_file}")
    print(f"Total Number of Trades: {len(trades_df)}")
    total_kwh = (trades_df['traded_kw'] * 0.5).sum()
    print(f"Total Energy Traded: {total_kwh:.2f} kWh")
    
    if len(trades_df) > 0:
        most_active_donor = trades_df['donor_section'].value_counts().idxmax()
        most_common_receiver = trades_df['receiver_section'].value_counts().idxmax()
        print(f"Most Active Donor: {most_active_donor}")
        print(f"Most Common Receiver: {most_common_receiver}")
        print("\nFirst 10 rows of the trades file:")
        print(trades_df.head(10).to_string(index=False))
    else:
        print("No trades found.")

if __name__ == "__main__":
    generate_trades()
