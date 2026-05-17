import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
from pathlib import Path
import tensorflow as tf

def generate_training_plots():
    base_path = Path(__file__).parent.parent
    trained_dir = base_path / "models" / "trained"
    figures_dir = base_path / "notebooks" / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Plot Model Architecture
    try:
        model = tf.keras.models.load_model(trained_dir / 'final_model.keras')
        tf.keras.utils.plot_model(model, to_file=figures_dir / 'model_architecture.png', show_shapes=True)
        print("Saved model_architecture.png")
    except Exception as e:
        print(f"Could not plot model: {e}")
    
    # 2. Plot Training Curves
    history_path = trained_dir / 'history.json'
    if history_path.exists():
        with open(history_path, 'r') as f:
            h = json.load(f)
            
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        best_epoch = np.argmin(h['val_loss'])
        
        # Total Loss
        axes[0,0].plot(h['loss'], label='Train')
        axes[0,0].plot(h['val_loss'], label='Val')
        axes[0,0].axvline(best_epoch, color='black', linestyle='--')
        axes[0,0].set_title('Total Loss')
        axes[0,0].legend()
        
        # Demand MAE (Keras 3 might name it differently, let's find the key)
        mae_key = [k for k in h.keys() if 'demand' in k and 'mae' in k and 'val' not in k][0]
        val_mae_key = 'val_' + mae_key
        axes[0,1].plot(h[mae_key], label='Train')
        axes[0,1].plot(h[val_mae_key], label='Val')
        axes[0,1].axvline(best_epoch, color='black', linestyle='--')
        axes[0,1].set_title('Demand MAE')
        axes[0,1].legend()
        
        # Anomaly Accuracy
        acc_key = [k for k in h.keys() if 'anomaly' in k and 'accuracy' in k and 'val' not in k][0]
        val_acc_key = 'val_' + acc_key
        axes[1,0].plot(h[acc_key], label='Train')
        axes[1,0].plot(h[val_acc_key], label='Val')
        axes[1,0].axvline(best_epoch, color='black', linestyle='--')
        axes[1,0].set_title('Anomaly Accuracy')
        axes[1,0].legend()
        
        # Alert Accuracy
        al_acc_key = [k for k in h.keys() if 'alert' in k and 'accuracy' in k and 'val' not in k][0]
        val_al_acc_key = 'val_' + al_acc_key
        axes[1,1].plot(h[al_acc_key], label='Train')
        axes[1,1].plot(h[val_al_acc_key], label='Val')
        axes[1,1].axvline(best_epoch, color='black', linestyle='--')
        axes[1,1].set_title('Alert Accuracy')
        axes[1,1].legend()
        
        plt.tight_layout()
        plt.savefig(figures_dir / 'training_curves.png')
        print("Saved training_curves.png")

if __name__ == "__main__":
    generate_training_plots()
