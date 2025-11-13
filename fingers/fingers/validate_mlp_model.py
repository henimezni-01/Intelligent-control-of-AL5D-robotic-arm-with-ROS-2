import os
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, log_loss, classification_report, confusion_matrix
import seaborn as sns
import matplotlib.pyplot as plt

# === Paramètres ===
MODEL_DIR = '/home/heni/ros2_ws/src/fingers/fingers'
CSV_PATH = os.path.join(MODEL_DIR, 'data/fingers_data.csv')
MODEL_PATH = os.path.join(MODEL_DIR, 'mlp_gesture_model_smote.pkl')
SCALER_PATH = os.path.join(MODEL_DIR, 'mlp_scaler.pkl')

# === Chargement du modèle et du scaler ===
model = joblib.load(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)

# === Chargement des données ===
df = pd.read_csv(CSV_PATH)
X = df.drop(columns=['label']).values
y = df['label'].values
class_names = sorted(df['label'].unique())

# === Split 80/20 ===
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42)

# === Standardisation ===
X_train_scaled = scaler.transform(X_train)
X_test_scaled = scaler.transform(X_test)

# === Prédictions ===
y_train_pred = model.predict(X_train_scaled)
y_test_pred = model.predict(X_test_scaled)

# === Probabilités ===
y_train_proba = model.predict_proba(X_train_scaled)
y_test_proba = model.predict_proba(X_test_scaled)

# === Évaluation ===
acc_train = accuracy_score(y_train, y_train_pred)
acc_test = accuracy_score(y_test, y_test_pred)
loss_train = log_loss(y_train, y_train_proba)
loss_test = log_loss(y_test, y_test_proba)

print(f"[TRAIN] Accuracy = {acc_train:.4f} | Log Loss = {loss_train:.4f}")
print(f"[TEST ] Accuracy = {acc_test:.4f} | Log Loss = {loss_test:.4f}\n")

# === Rapport de classification ===
print("=== Rapport de Classification (Test) ===")
print(classification_report(y_test, y_test_pred, digits=4))

# === Matrice de confusion ===
cm = confusion_matrix(y_test, y_test_pred)
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=class_names, yticklabels=class_names)
plt.title("Matrice de Confusion (Test)")
plt.xlabel("Prédit")
plt.ylabel("Réel")
plt.tight_layout()
plt.savefig(os.path.join(MODEL_DIR, "confusion_matrix_validate.png"))
plt.show()
