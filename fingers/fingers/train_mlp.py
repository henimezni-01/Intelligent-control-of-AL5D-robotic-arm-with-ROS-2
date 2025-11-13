import os
import pandas as pd
import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, log_loss
from sklearn.model_selection import train_test_split
from imblearn.over_sampling import SMOTE
import matplotlib.pyplot as plt
import joblib

def load_data(csv_path):
    df = pd.read_csv(csv_path)
    print("Nombre d'exemples par classe avant SMOTE :")
    print(df['label'].value_counts().sort_index())
    return df

def preprocess_data(df):
    X = df.drop(columns=['label']).values
    y = df['label'].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    return X_scaled, y, scaler

def balance_data_smote(X_train, y_train):
    smote = SMOTE(random_state=42)
    X_res, y_res = smote.fit_resample(X_train, y_train)
    print("\nNombre d'exemples par classe après SMOTE :")
    unique, counts = np.unique(y_res, return_counts=True)
    for label, count in zip(unique, counts):
        print(f"Classe {label} : {count} exemples")
    return X_res, y_res

def train_mlp(X_train, y_train):
    mlp = MLPClassifier(hidden_layer_sizes=(128, 64),
                        activation='relu',
                        solver='adam',
                        max_iter=300,
                        random_state=42,
                        verbose=False)
    mlp.fit(X_train, y_train)
    return mlp

def evaluate_model(mlp, X_test, y_test):
    y_pred = mlp.predict(X_test)
    y_proba = mlp.predict_proba(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    loss = log_loss(y_test, y_proba)
    print(f"\nAccuracy sur les données de TEST : {accuracy:.4f}")
    print(f"Loss (log loss) sur les données de TEST : {loss:.4f}")
    return accuracy, loss

def plot_loss_curve(mlp):
    plt.figure(figsize=(10, 5))
    plt.plot(mlp.loss_curve_, label='Loss (entraînement)')
    plt.title("Évolution de la Loss pendant l'entraînement")
    plt.xlabel("Époque")
    plt.ylabel("Loss")
    plt.legend()
    plt.grid()
    plt.tight_layout()
    plt.savefig("mlp_loss_curve_smote.png")
    plt.show()

def save_model_scaler(mlp, scaler):
    save_dir = '/home/heni/ros2_ws/src/fingers/fingers'
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    model_path = os.path.join(save_dir, 'mlp_gesture_model_smote.pkl')
    scaler_path = os.path.join(save_dir, 'mlp_scaler.pkl')
    joblib.dump(mlp, model_path)
    joblib.dump(scaler, scaler_path)
    print(f"Modèle sauvegardé dans : {model_path}")
    print(f"Scaler sauvegardé dans : {scaler_path}")

def main():
    csv_file_path = '/home/heni/ros2_ws/src/fingers/fingers/data/fingers_data.csv'
    df = load_data(csv_file_path)

    X, y, scaler = preprocess_data(df)

    # Séparation train-test (20% test) stratifiée
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)

    # Équilibrage des classes sur le train uniquement
    X_train_res, y_train_res = balance_data_smote(X_train, y_train)

    # Entraînement
    mlp = train_mlp(X_train_res, y_train_res)

    # Évaluation sur test
    evaluate_model(mlp, X_test, y_test)

    # Courbe de loss
    plot_loss_curve(mlp)

    # Sauvegarder modèle + scaler
    save_model_scaler(mlp, scaler)

if __name__ == '__main__':
    main()

