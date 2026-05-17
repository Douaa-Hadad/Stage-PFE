import json
import os
from pathlib import Path

def create_preprocessing_notebook():
    notebook_path = Path("notebooks/02_preprocessing.ipynb")
    output_path = Path("models/preprocessing")
    
    notebook_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.mkdir(parents=True, exist_ok=True)
    
    cells = []
    
    # Header
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# Data Preprocessing for multi-task LSTM\n",
            "This notebook prepares the hospital microgrid data for training an LSTM model that predicts energy demand, outages, and alert levels."
        ]
    })
    
    # Imports
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import pandas as pd\n",
            "import numpy as np\n",
            "import matplotlib.pyplot as plt\n",
            "import joblib\n",
            "import json\n",
            "from pathlib import Path\n",
            "from sklearn.preprocessing import MinMaxScaler\n",
            "from sklearn.utils.class_weight import compute_class_weight\n",
            "\n",
            "# Settings\n",
            "os.makedirs('../models/preprocessing', exist_ok=True)"
        ]
    })
    
    # Section 1
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Section 1 — Load & Select Features"]
    })
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "df = pd.read_csv('../data/master_dataset.csv')\n",
            "df['timestamp'] = pd.to_datetime(df['timestamp'])\n",
            "df.set_index('timestamp', inplace=True)\n",
            "\n",
            "input_features = [\n",
            "    'net_solar_kw', 'net_wind_kw', 'grid_available_kw', 'total_supply_kw',\n",
            "    'total_hospital_kw', 'energy_balance_kw', 'avg_battery_pct', 'min_battery_pct',\n",
            "    'temperature_2m', 'cloud_cover', 'windspeed_10m', 'precipitation',\n",
            "    'hour', 'is_weekend', 'is_daytime', 'renewable_fraction', 'is_trading'\n",
            "]\n",
            "\n",
            "# Season encoding\n",
            "df['is_winter'] = (df['season'] == 'winter').astype(int)\n",
            "df['is_spring'] = (df['season'] == 'spring').astype(int)\n",
            "df['is_summer'] = (df['season'] == 'summer').astype(int)\n",
            "df['is_autumn'] = (df['season'] == 'autumn').astype(int)\n",
            "\n",
            "input_features += ['is_winter', 'is_spring', 'is_summer', 'is_autumn']\n",
            "\n",
            "# Alert encoding\n",
            "alert_map = {'NORMAL': 0, 'WARNING': 1, 'CRITICAL': 2}\n",
            "df['alert_encoded'] = df['alert_level'].map(alert_map)\n",
            "\n",
            "print(f'Final Features: {input_features}')\n",
            "print(f'Shape: {df[input_features].shape}')"
        ]
    })
    
    # Section 2
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Section 2 — Handle Class Imbalance"]
    })
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "print('Alert Distribution:')\n",
            "print(df['alert_encoded'].value_counts())\n",
            "\n",
            "classes = np.unique(df['alert_encoded'])\n",
            "weights = compute_class_weight(class_weight='balanced', classes=classes, y=df['alert_encoded'])\n",
            "class_weights = {int(c): float(w) for c, w in zip(classes, weights)}\n",
            "\n",
            "print(f'Class Weights: {class_weights}')\n",
            "with open('../models/preprocessing/class_weights.json', 'w') as f:\n",
            "    json.dump(class_weights, f)\n",
            "print('Saved class weights to models/preprocessing/class_weights.json')"
        ]
    })
    
    # Section 3
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Section 3 — Train / Validation / Test Split"]
    })
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "n = len(df)\n",
            "train_size = int(n * 0.7)\n",
            "val_size = int(n * 0.15)\n",
            "\n",
            "train_df = df.iloc[:train_size]\n",
            "val_df = df.iloc[train_size:train_size+val_size]\n",
            "test_df = df.iloc[train_size+val_size:]\n",
            "\n",
            "print(f'Train: {train_df.index.min()} to {train_df.index.max()} ({len(train_df)} rows)')\n",
            "print(f'Val:   {val_df.index.min()} to {val_df.index.max()} ({len(val_df)} rows)')\n",
            "print(f'Test:  {test_df.index.min()} to {test_df.index.max()} ({len(test_df)} rows)')\n",
            "\n",
            "plt.figure(figsize=(15, 6))\n",
            "plt.plot(train_df.index, [1]*len(train_df), '|', label='Train', color='blue')\n",
            "plt.plot(val_df.index, [1]*len(val_df), '|', label='Val', color='green')\n",
            "plt.plot(test_df.index, [1]*len(test_df), '|', label='Test', color='red')\n",
            "plt.legend()\n",
            "plt.title('Time-Series Split')\n",
            "plt.yticks([])\n",
            "plt.show()"
        ]
    })
    
    # Section 4
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Section 4 — Scaling"]
    })
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "scaler = MinMaxScaler()\n",
            "scaler.fit(train_df[input_features])\n",
            "\n",
            "train_scaled = scaler.transform(train_df[input_features])\n",
            "val_scaled = scaler.transform(val_df[input_features])\n",
            "test_scaled = scaler.transform(test_df[input_features])\n",
            "\n",
            "joblib.dump(scaler, '../models/preprocessing/scaler.pkl')\n",
            "print('Saved scaler to models/preprocessing/scaler.pkl')\n",
            "\n",
            "# Visual Check\n",
            "fig, axes = plt.subplots(1, 2, figsize=(15, 5))\n",
            "train_df['total_hospital_kw'].hist(ax=axes[0], bins=50, alpha=0.5, label='Original')\n",
            "axes[0].set_title('total_hospital_kw (Original)')\n",
            "\n",
            "pd.Series(train_scaled[:, 4]).hist(ax=axes[1], bins=50, alpha=0.5, color='orange', label='Scaled')\n",
            "axes[1].set_title('total_hospital_kw (Scaled)')\n",
            "plt.show()"
        ]
    })
    
    # Section 5
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Section 5 — Build Sequences"]
    })
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "def create_sequences(scaled_data, raw_df, seq_length=48, pred_length=8):\n",
            "    X = []\n",
            "    y_demand = []\n",
            "    y_anomaly = []\n",
            "    y_alert = []\n",
            "    \n",
            "    # We need to use the raw_df for labels as they are not all in input_features\n",
            "    for i in range(len(scaled_data) - seq_length - pred_length + 1):\n",
            "        # Input: [i : i+48]\n",
            "        X.append(scaled_data[i : i+seq_length])\n",
            "        \n",
            "        # Predicted index: [i+48 : i+48+8]\n",
            "        # Regression: total_hospital_kw\n",
            "        y_demand.append(raw_df['total_hospital_kw'].iloc[i+seq_length : i+seq_length+pred_length].values)\n",
            "        \n",
            "        # Binary: is_outage in next 8 steps\n",
            "        outage_present = raw_df['is_outage'].iloc[i+seq_length : i+seq_length+pred_length].any()\n",
            "        y_anomaly.append(1 if outage_present else 0)\n",
            "        \n",
            "        # Multiclass: alert_encoded at the end of pred window (i+seq_length+pred_length-1)\n",
            "        y_alert.append(raw_df['alert_encoded'].iloc[i+seq_length+pred_length-1])\n",
            "        \n",
            "    return np.array(X), np.array(y_demand), np.array(y_anomaly), np.array(y_alert)\n",
            "\n",
            "X_train, y_demand_train, y_anomaly_train, y_alert_train = create_sequences(train_scaled, train_df)\n",
            "X_val, y_demand_val, y_anomaly_val, y_alert_val = create_sequences(val_scaled, val_df)\n",
            "X_test, y_demand_test, y_anomaly_test, y_alert_test = create_sequences(test_scaled, test_df)\n",
            "\n",
            "print(f'X_train shape: {X_train.shape}')\n",
            "print(f'y_demand_train shape: {y_demand_train.shape}')\n",
            "\n",
            "for split, data in zip(['train', 'val', 'test'], \n",
            "                       [[X_train, y_demand_train, y_anomaly_train, y_alert_train],\n",
            "                        [X_val, y_demand_val, y_anomaly_val, y_alert_val],\n",
            "                        [X_test, y_demand_test, y_anomaly_test, y_alert_test]]):\n",
            "    np.save(f'../models/preprocessing/X_{split}.npy', data[0])\n",
            "    np.save(f'../models/preprocessing/y_demand_{split}.npy', data[1])\n",
            "    np.save(f'../models/preprocessing/y_anomaly_{split}.npy', data[2])\n",
            "    np.save(f'../models/preprocessing/y_alert_{split}.npy', data[3])"
        ]
    })
    
    # Section 6
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Section 6 — Verify Sequences"]
    })
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "idx = np.random.randint(0, len(X_train))\n",
            "plt.figure(figsize=(15, 5))\n",
            "plt.plot(range(48), X_train[idx, :, 4], label='Historical Demand (Scaled)')\n",
            "# We need to scale the target demand if we want to plot on same axis, \n",
            "# or just plot raw but here X is scaled. \n",
            "# Let's just plot the pattern.\n",
            "plt.plot(range(48, 56), y_demand_train[idx] / 600.0, 'r--', label='Future Demand (Approx Scaled)')\n",
            "plt.title(f'Sample Sequence (Index {idx})')\n",
            "plt.legend()\n",
            "plt.show()\n",
            "\n",
            "print(f'y_anomaly: {y_anomaly_train[idx]}')\n",
            "print(f'y_alert: {y_alert_train[idx]}')\n",
            "print(f'Any NaNs in X_train: {np.isnan(X_train).any()}')"
        ]
    })
    
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "codemirror_mode": {
                    "name": "ipython",
                    "version": 3
                },
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.8.10"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }
    
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, indent=2)
    
    print(f"Notebook created at {notebook_path}")

if __name__ == "__main__":
    create_preprocessing_notebook()
