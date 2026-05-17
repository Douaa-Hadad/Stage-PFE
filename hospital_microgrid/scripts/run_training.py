import pandas as pd
import numpy as np
import json
import time
from pathlib import Path
import tensorflow as tf
from tensorflow.keras import layers, models, callbacks
from sklearn.utils.class_weight import compute_class_weight
import os

def run_training():
    base_path = Path(__file__).parent.parent
    prep_dir = base_path / "models" / "preprocessing"
    trained_dir = base_path / "models" / "trained"
    trained_dir.mkdir(parents=True, exist_ok=True)
    
    # Load Data
    X_train = np.load(prep_dir / 'X_train.npy')
    y_demand_train = np.load(prep_dir / 'y_demand_train.npy')
    y_anomaly_train = np.load(prep_dir / 'y_anomaly_train.npy')
    y_alert_train = np.load(prep_dir / 'y_alert_train.npy')
    
    X_val = np.load(prep_dir / 'X_val.npy')
    y_demand_val = np.load(prep_dir / 'y_demand_val.npy')
    y_anomaly_val = np.load(prep_dir / 'y_anomaly_val.npy')
    y_alert_val = np.load(prep_dir / 'y_alert_val.npy')
    
    # Fix 1 — Class Weights (Computed mathematically)
    print('Computing class weights...')
    
    classes_alert = np.array([0, 1, 2])
    alert_weights_arr = compute_class_weight('balanced', classes=classes_alert, y=y_alert_train.flatten())
    alert_weights_arr[2] = alert_weights_arr[2] * 3
    alert_class_weights = {i: weight for i, weight in enumerate(alert_weights_arr)}

    classes_anomaly = np.array([0, 1])
    anomaly_weights_arr = compute_class_weight('balanced', classes=classes_anomaly, y=y_anomaly_train.flatten())
    anomaly_weights_arr[1] = anomaly_weights_arr[1] * 3
    anomaly_class_weights = {i: weight for i, weight in enumerate(anomaly_weights_arr)}

    # Convert to sample weights (list to match y_train_list)
    sample_weights_list = [
        np.ones(len(y_demand_train)),
        np.array([anomaly_class_weights[int(val)] for val in y_anomaly_train.flatten()]),
        np.array([alert_class_weights[int(val)] for val in y_alert_train.flatten()])
    ]
    
    print(f"Training shape: {X_train.shape}")
    
    # Build Model (Fix 2 - Lighter Architecture)
    input_shape = (48, 21)
    inputs = layers.Input(shape=input_shape, name='main_input')
    x = layers.LSTM(64, return_sequences=True)(inputs)
    x = layers.Dropout(0.2)(x)
    x = layers.LSTM(32, return_sequences=False)(x)
    x = layers.Dropout(0.2)(x)
    shared = layers.Dense(16, activation='relu', name='shared_dense')(x)
    
    demand_output = layers.Dense(16, activation='relu')(shared)
    demand_output = layers.Dense(8, activation='linear', name='demand_output')(demand_output)
    anomaly_output = layers.Dense(8, activation='relu')(shared)
    anomaly_output = layers.Dense(1, activation='sigmoid', name='anomaly_output')(anomaly_output)
    alert_output = layers.Dense(16, activation='relu')(shared)
    alert_output = layers.Dense(3, activation='softmax', name='alert_output')(alert_output)
    
    model = models.Model(inputs=inputs, outputs=[demand_output, anomaly_output, alert_output])
    
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss={
            'demand_output': 'mse',
            'anomaly_output': 'binary_crossentropy',
            'alert_output': 'sparse_categorical_crossentropy'
        },
        loss_weights={
            'demand_output': 0.5,
            'anomaly_output': 4.0,
            'alert_output': 4.0
        },
        metrics={
            'demand_output': 'mae',
            'anomaly_output': 'accuracy',
            'alert_output': 'accuracy'
        }
    )
    
    # Fix 3 - Conservative training
    model_callbacks = [
        callbacks.EarlyStopping(monitor='val_loss', patience=8, restore_best_weights=True),
        callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=4, min_lr=1e-6),
        callbacks.ModelCheckpoint(str(trained_dir / 'best_model.keras'), monitor='val_loss', save_best_only=True),
        callbacks.CSVLogger(str(trained_dir / 'training_log.csv'))
    ]
    
    y_train_list = [y_demand_train, y_anomaly_train, y_alert_train]
    y_val_list = [y_demand_val, y_anomaly_val, y_alert_val]
    
    print("Starting training with sample weights list...")
    history = model.fit(
        X_train,
        y_train_list,
        validation_data=(X_val, y_val_list),
        epochs=50,
        batch_size=128,
        sample_weight=sample_weights_list,
        callbacks=model_callbacks,
        verbose=1
    )
    
    model.save(str(trained_dir / 'final_model.keras'))
    with open(trained_dir / 'history.json', 'w') as f:
        json.dump({k: [float(v1) for v1 in v] for k, v in history.history.items()}, f)
    print("Retraining complete.")

if __name__ == "__main__":
    run_training()
