import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32
from std_msgs.msg import Float32MultiArray
import numpy as np
import joblib
import cv2

MODEL_PATH = '/home/heni/ros2_ws/src/fingers/fingers/mlp_gesture_model_smote.pkl'
SCALER_PATH = '/home/heni/ros2_ws/src/fingers/fingers/mlp_scaler.pkl'

class GesturePredictor(Node):
    def __init__(self):
        super().__init__('gesture_predictor')

        self.subscription = self.create_subscription(
            Float32MultiArray,
            '/hand_coordinates',
            self.coordinates_callback,
            10)

        self.pred_pub = self.create_publisher(Int32, '/mlp_prediction', 10)

        self.model = joblib.load(MODEL_PATH)
        self.scaler = joblib.load(SCALER_PATH)

        self.get_logger().info("Modèle et Scaler chargés, prêt à prédire...")
        cv2.namedWindow("Prediction", cv2.WINDOW_NORMAL)
        self.prediction_text = "En attente..."

    def coordinates_callback(self, msg):
        points = msg.data

        if len(points) != 63:
            self.get_logger().warning(f"Nombre inattendu de coordonnées : {len(points)}")
            return

        input_array = np.array(points).reshape(1, -1)
        scaled_input = self.scaler.transform(input_array)

        prediction = self.model.predict(scaled_input)[0]

        pred_msg = Int32()
        pred_msg.data = int(prediction)
        self.pred_pub.publish(pred_msg)

        # Affichage simple texte
        self.prediction_text = f'Prediction: {prediction}'
        img = 255 * np.ones((100, 400, 3), dtype=np.uint8)
        cv2.putText(img, self.prediction_text, (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
        cv2.imshow("Prediction", img)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            self.get_logger().info('Arrêt du noeud gesture_predictor...')
            self.destroy_node()
            cv2.destroyAllWindows()
            rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    node = GesturePredictor()
    rclpy.spin(node)

if __name__ == '__main__':
    main()


	

