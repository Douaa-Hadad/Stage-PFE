import json
import os
from pathlib import Path

def create_training_notebook():
    notebook_path = Path("notebooks/03_model_training.ipynb")
    output_path = Path("models/trained")
    
    notebook_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.mkdir(parents=True, exist_ok=True)
    
    cells = []
    
    # Header
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# Multi-Task LSTM Model Training\n",
            "This notebook builds and trains a multi-task LSTM model to predict energy demand, detect outages, and classify system alerts."
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
            "import json\n",
            "import time\n",
            "from pathlib import Path\n",
            "import tensorflow as tf\n",
            "from tensorflow.keras import layers, models, callbacks\n",
            "from sklearn.utils.class_weight import compute_class_weight\n",
            "\n",
            "# Settings\n",
            "os.makedirs('../models/trained', exist_ok=True)\n",
            "print(f'TensorFlow Version: {tf.__version__}')"
        ]
    })
    
    # Section 1
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Section 1 — Load Data & Compute Class Weights"]
    })
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "prep_dir = Path('../models/preprocessing')\n",
            "\n",
            "X_train = np.load(prep_dir / 'X_train.npy')\n",
            "y_demand_train = np.load(prep_dir / 'y_demand_train.npy')\n",
            "y_anomaly_train = np.load(prep_dir / 'y_anomaly_train.npy')\n",
            "y_alert_train = np.load(prep_dir / 'y_alert_train.npy')\n",
            "\n",
            "X_val = np.load(prep_dir / 'X_val.npy')\n",
            "y_demand_val = np.load(prep_dir / 'y_demand_val.npy')\n",
            "y_anomaly_val = np.load(prep_dir / 'y_anomaly_val.npy')\n",
            "y_alert_val = np.load(prep_dir / 'y_alert_val.npy')\n",
            "\n",
            "# Fix 1 — Class Weights (No Oversampling)\n",
            "print('Computing class weights...')\n",
            "\n",
            "classes_alert = np.array([0, 1, 2])\n",
            "alert_weights_arr = compute_class_weight('balanced', classes=classes_alert, y=y_alert_train.flatten())\n",
            "alert_weights_arr[2] = alert_weights_arr[2] * 3\n",
            "alert_class_weights = {i: weight for i, weight in enumerate(alert_weights_arr)}\n",
            "\n",
            "classes_anomaly = np.array([0, 1])\n",
            "anomaly_weights_arr = compute_class_weight('balanced', classes=classes_anomaly, y=y_anomaly_train.flatten())\n",
            "anomaly_weights_arr[1] = anomaly_weights_arr[1] * 3\n",
            "anomaly_class_weights = {i: weight for i, weight in enumerate(anomaly_weights_arr)}\n",
            "\n",
            "sample_weights = {\n",
            "    'demand_output': np.ones(len(y_demand_train)),\n",
            "    'anomaly_output': np.array([anomaly_class_weights[int(val)] for val in y_anomaly_train.flatten()]),\n",
            "    'alert_output': np.array([alert_class_weights[int(val)] for val in y_alert_train.flatten()])\n",
            "}\n",
            "\n",
            "print(f'Training shape: {X_train.shape}')\n",
            "print(f'Anomaly class weights: {anomaly_class_weights}')\n",
            "print(f'Alert class weights: {alert_class_weights}')"
        ]
    })
    
    # Section 2
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Section 2 — Model Architecture"]
    })
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "input_shape = (48, 21)\n",
            "inputs = layers.Input(shape=input_shape, name='main_input')\n",
            "x = layers.LSTM(64, return_sequences=True)(inputs)\n",
            "x = layers.Dropout(0.2)(x)\n",
            "x = layers.LSTM(32, return_sequences=False)(x)\n",
            "x = layers.Dropout(0.2)(x)\n",
            "shared = layers.Dense(16, activation='relu', name='shared_dense')(x)\n",
            "\n",
            "demand_output = layers.Dense(16, activation='relu')(shared)\n",
            "demand_output = layers.Dense(8, activation='linear', name='demand_output')(demand_output)\n",
            "anomaly_output = layers.Dense(8, activation='relu')(shared)\n",
            "anomaly_output = layers.Dense(1, activation='sigmoid', name='anomaly_output')(anomaly_output)\n",
            "alert_output = layers.Dense(16, activation='relu')(shared)\n",
            "alert_output = layers.Dense(3, activation='softmax', name='alert_output')(alert_output)\n",
            "\n",
            "model = models.Model(inputs=inputs, outputs=[demand_output, anomaly_output, alert_output])\n",
            "model.summary()"
        ]
    })
    
    # Section 3
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Section 3 — Compile (Updated Loss Weights)"]
    })
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "model.compile(\n",
            "    optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),\n",
            "    loss={\n",
            "        'demand_output': 'mse',\n",
            "        'anomaly_output': 'binary_crossentropy',\n",
            "        'alert_output': 'sparse_categorical_crossentropy'\n",
            "    },\n",
            "    loss_weights={\n",
            "        'demand_output': 0.5,\n",
            "        'anomaly_output': 4.0,\n",
            "        'alert_output': 4.0\n",
            "    },\n",
            "    metrics={\n",
            "        'demand_output': 'mae',\n",
            "        'anomaly_output': 'accuracy',\n",
            "        'alert_output': 'accuracy'\n",
            "    }\n",
            ")"
        ]
    })
    
    # Section 4
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Section 4 — Callbacks"]
    })
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "model_callbacks = [\n",
            "    callbacks.EarlyStopping(monitor='val_loss', patience=8, restore_best_weights=True),\n",
            "    callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=4, min_lr=1e-6),\n",
            "    callbacks.ModelCheckpoint('../models/trained/best_model.keras', monitor='val_loss', save_best_only=True),\n",
            "    callbacks.CSVLogger('../models/trained/training_log.csv')\n",
            "]"
        ]
    })
    
    # Section 5
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Section 5 — Train (Class Weights)"]
    })
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "start_time = time.time()\n",
            "history = model.fit(\n",
            "    X_train,\n",
            "    [y_demand_train, y_anomaly_train, y_alert_train],\n",
            "    validation_data=(X_val, [y_demand_val, y_anomaly_val, y_alert_val]),\n",
            "    epochs=50,\n",
            "    batch_size=128,\n",
            "    sample_weight=sample_weights,\n",
            "    callbacks=model_callbacks,\n",
            "    verbose=1\n",
            ")\n",
            "\n",
            "end_time = time.time()\n",
            "print(f'Training finished at {time.ctime()}')\n",
            "best_epoch = np.argmin(history.history['val_loss'])\n",
            "print(f'Best epoch: {best_epoch + 1} with val_loss: {history.history[\"val_loss\"][best_epoch]:.4f}')"
        ]
    })
    
    # Section 6
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Section 6 — Training Curves"]
    })
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "fig, axes = plt.subplots(2, 2, figsize=(15, 12))\n",
            "best_epoch = np.argmin(history.history['val_loss'])\n",
            "\n",
            "# Total Loss\n",
            "axes[0,0].plot(history.history['loss'], label='Train')\n",
            "axes[0,0].plot(history.history['val_loss'], label='Val')\n",
            "axes[0,0].axvline(best_epoch, color='black', linestyle='--')\n",
            "axes[0,0].set_title('Total Loss')\n",
            "axes[0,0].legend()\n",
            "\n",
            "# Demand MAE\n",
            "axes[0,1].plot(history.history['demand_output_mae'], label='Train')\n",
            "axes[0,1].plot(history.history['val_demand_output_mae'], label='Val')\n",
            "axes[0,1].axvline(best_epoch, color='black', linestyle='--')\n",
            "axes[0,1].set_title('Demand MAE')\n",
            "axes[0,1].legend()\n",
            "\n",
            "# Anomaly Accuracy\n",
            "axes[1,0].plot(history.history['anomaly_output_accuracy'], label='Train')\n",
            "axes[1,0].plot(history.history['val_anomaly_output_accuracy'], label='Val')\n",
            "axes[1,0].axvline(best_epoch, color='black', linestyle='--')\n",
            "axes[1,0].set_title('Anomaly Accuracy')\n",
            "axes[1,0].legend()\n",
            "\n",
            "# Alert Accuracy\n",
            "axes[1,1].plot(history.history['alert_output_accuracy'], label='Train')\n",
            "axes[1,1].plot(history.history['val_alert_output_accuracy'], label='Val')\n",
            "axes[1,1].axvline(best_epoch, color='black', linestyle='--')\n",
            "axes[1,1].set_title('Alert Accuracy')\n",
            "axes[1,1].legend()\n",
            "\n",
            "plt.tight_layout()\n",
            "plt.savefig('figures/training_curves.png')\n",
            "plt.show()"
        ]
    })
    
    # Section 7
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Section 7 — Save"]
    })
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "model.save('../models/trained/final_model.keras')\n",
            "\n",
            "with open('../models/trained/history.json', 'w') as f:\n",
            "    json.dump({k: [float(v1) for v1 in v] for k, v in history.history.items()}, f)\n",
            "\n",
            "print('Models and history saved to models/trained/')\n",
            "\n",
            "print('\\nFinal Metrics (Val):')\n",
            "for k, v in history.history.items():\n",
            "    if k.startswith('val_'):\n",
            "        print(f'{k}: {v[best_epoch]:.4f}')"
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
    create_training_notebook()
