import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
from sklearn.utils.class_weight import compute_class_weight
import os

def run_preprocessing():
    base_path = Path(__file__).parent.parent
    data_path = base_path / "data" / "master_dataset.csv"
    output_path = base_path / "models" / "preprocessing"
    output_path.mkdir(parents=True, exist_ok=True)
    
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    input_features = [
        'net_solar_kw', 'net_wind_kw', 'grid_available_kw', 'total_supply_kw',
        'total_hospital_kw', 'energy_balance_kw', 'avg_battery_pct', 'min_battery_pct',
        'temperature_2m', 'cloud_cover', 'windspeed_10m', 'precipitation',
        'hour', 'is_weekend', 'is_daytime', 'renewable_fraction', 'is_trading'
    ]
    
    # Season encoding
    df['is_winter'] = (df['season'] == 'winter').astype(int)
    df['is_spring'] = (df['season'] == 'spring').astype(int)
    df['is_summer'] = (df['season'] == 'summer').astype(int)
    df['is_autumn'] = (df['season'] == 'autumn').astype(int)
    input_features += ['is_winter', 'is_spring', 'is_summer', 'is_autumn']
    
    # Alert encoding
    alert_map = {'NORMAL': 0, 'WARNING': 1, 'CRITICAL': 2}
    df['alert_encoded'] = df['alert_level'].map(alert_map)
    
    # Class weights
    classes = np.unique(df['alert_encoded'])
    weights = compute_class_weight(class_weight='balanced', classes=classes, y=df['alert_encoded'])
    class_weights = {int(c): float(w) for c, w in zip(classes, weights)}
    with open(output_path / 'class_weights.json', 'w') as f:
        json.dump(class_weights, f)
        
    # Split
    n = len(df)
    train_size = int(n * 0.7)
    val_size = int(n * 0.15)
    train_df = df.iloc[:train_size]
    val_df = df.iloc[train_size:train_size+val_size]
    test_df = df.iloc[train_size+val_size:]
    
    # Scale
    scaler = MinMaxScaler()
    scaler.fit(train_df[input_features])
    joblib.dump(scaler, output_path / 'scaler.pkl')
    
    train_scaled = scaler.transform(train_df[input_features])
    val_scaled = scaler.transform(val_df[input_features])
    test_scaled = scaler.transform(test_df[input_features])
    
    # Build sequences
    def create_sequences(scaled_data, raw_df, seq_length=48, pred_length=8):
        X, y_d, y_a, y_l = [], [], [], []
        for i in range(len(scaled_data) - seq_length - pred_length + 1):
            X.append(scaled_data[i : i+seq_length])
            y_d.append(raw_df['total_hospital_kw'].iloc[i+seq_length : i+seq_length+pred_length].values)
            outage_present = raw_df['is_outage'].iloc[i+seq_length : i+seq_length+pred_length].any()
            y_a.append(1 if outage_present else 0)
            y_l.append(raw_df['alert_encoded'].iloc[i+seq_length+pred_length-1])
        return np.array(X), np.array(y_d), np.array(y_a), np.array(y_l)
    
    for split, data_scaled, data_raw in zip(['train', 'val', 'test'], 
                                            [train_scaled, val_scaled, test_scaled],
                                            [train_df, val_df, test_df]):
        X, yd, ya, yl = create_sequences(data_scaled, data_raw)
        np.save(output_path / f'X_{split}.npy', X)
        np.save(output_path / f'y_demand_{split}.npy', yd)
        np.save(output_path / f'y_anomaly_{split}.npy', ya)
        np.save(output_path / f'y_alert_{split}.npy', yl)
        print(f"Saved {split} arrays: X={X.shape}, y_demand={yd.shape}, y_anomaly={ya.shape}, y_alert={yl.shape}")

if __name__ == "__main__":
    run_preprocessing()
