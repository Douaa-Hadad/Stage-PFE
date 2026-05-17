import numpy as np
import tensorflow as tf
from pathlib import Path

prep_dir = Path("models/preprocessing")
trained_dir = Path("models/trained")

y_anomaly_test = np.load(prep_dir / "y_anomaly_test.npy")
y_alert_test = np.load(prep_dir / "y_alert_test.npy")

model = tf.keras.models.load_model(trained_dir / "best_model.keras")
X_test = np.load(prep_dir / "X_test.npy")

p = model.predict(X_test, verbose=0)
p_demand, p_anomaly, p_alert = p

print(f"y_anomaly_test shape: {y_anomaly_test.shape}")
print(f"p_anomaly shape: {p_anomaly.shape}")
print(f"y_alert_test shape: {y_alert_test.shape}")
print(f"p_alert shape: {p_alert.shape}")

y_pred_anom = (p_anomaly.flatten() > 0.3).astype(int)
y_true_anom = y_anomaly_test.flatten()

recall_anom = np.sum((y_true_anom == 1) & (y_pred_anom == 1)) / (np.sum(y_true_anom == 1) + 1e-9)
print(f"Recall Anomaly: {recall_anom}")

y_pred_alert = np.argmax(p_alert, axis=1)
y_true_alert = y_alert_test.flatten()
critical_recall = np.sum((y_true_alert == 2) & (y_pred_alert == 2)) / (np.sum(y_true_alert == 2) + 1e-9)
print(f"Critical Recall: {critical_recall}")
