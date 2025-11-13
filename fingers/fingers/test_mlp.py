import rclpy
from rclpy.node import Node
import joblib
import os
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, log_loss
from sklearn.model_selection import train_test_split

MODEL_DIR = '/home/heni/ros2_ws/src/fingers/fingers'
CSV_PATH = '/home/heni/ros2_ws/src/fingers/fingers/data/fingers_data.csv'

class MLPTestNode(Node):
    def __init__(self):
        super().__init__('mlp_test_node')
        self.get_logger().info('Chargement du scaler et du modèle...')

        # Charger modèle et scaler
        model_path = os.path.join(MODEL_DIR, 'mlp_gesture_model_smote.pkl')
        scaler_path = os.path.join(MODEL_DIR, 'mlp_scaler.pkl')

        if not os.path.exists(model_path) or not os.path.exists(scaler_path):
            self.get_logger().error('Modèle ou scaler non trouvés. Vérifiez les chemins.')
            raise FileNotFoundError('Modèle ou scaler non trouvés.')

        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        self.get_logger().info('Modèle et scaler chargés avec succès !')

        # Charger données CSV
        df = pd.read_csv(CSV_PATH)
        X = df.drop(columns=['label']).values
        y = df['label'].values

        # Séparer train/test 80/20 stratifié (on garde test uniquement ici)
        _, X_test, _, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y)

        # Appliquer scaler
        X_test_scaled = self.scaler.transform(X_test)

        # Prédire
        y_pred = self.model.predict(X_test_scaled)
        y_proba = self.model.predict_proba(X_test_scaled)

        # Évaluer
        acc = accuracy_score(y_test, y_pred)
        loss = log_loss(y_test, y_proba)

        self.get_logger().info(f'Accuracy sur les données de TEST : {acc:.4f}')
        self.get_logger().info(f'Loss (log loss) sur les données de TEST : {loss:.4f}')

def main(args=None):
    rclpy.init(args=args)
    node = MLPTestNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

