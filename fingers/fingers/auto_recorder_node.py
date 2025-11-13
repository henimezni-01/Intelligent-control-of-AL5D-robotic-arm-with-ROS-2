import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import mediapipe as mp
import csv
import os

class HandRecorder(Node):
    def __init__(self):
        super().__init__('hand_recorder')
        self.subscription = self.create_subscription(
            Image,
            '/camera/rgb/image_raw',
            self.image_callback,
            10)
        self.bridge = CvBridge()
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(static_image_mode=False,
                                         max_num_hands=1,
                                         min_detection_confidence=0.7)
        self.mp_drawing = mp.solutions.drawing_utils

        # Chemin vers le dossier et fichier CSV
        self.output_dir = '/home/heni/ros2_ws/src/fingers/fingers/data'
        os.makedirs(self.output_dir, exist_ok=True)
        self.csv_file_path = os.path.join(self.output_dir, 'fingers_data.csv')

        self.get_logger().info(f"Dossier prêt: {self.output_dir}")

        # Créer fichier CSV avec en-tête s'il n'existe pas
        if not os.path.exists(self.csv_file_path):
            with open(self.csv_file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                header = []
                for i in range(21):
                    header += [f'x{i}', f'y{i}', f'z{i}']
                header.append('label')
                writer.writerow(header)
            self.get_logger().info(f"Fichier CSV créé avec en-tête: {self.csv_file_path}")
        else:
            self.get_logger().info(f"Fichier CSV existant : {self.csv_file_path}")

        self.current_points = None
        self.current_label = None

    def image_callback(self, msg):
        # Convertir image ROS -> OpenCV
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Détection des mains MediaPipe
        results = self.hands.process(image_rgb)

        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            points = []
            for lm in hand_landmarks.landmark:
                points.extend([lm.x, lm.y, lm.z])
            self.current_points = points

            # Dessiner les landmarks
            self.mp_drawing.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)

            # Afficher le label sur la fenêtre
            if self.current_label is not None:
                cv2.putText(frame, f'Label: {self.current_label}', (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        else:
            self.current_points = None

        cv2.imshow('Hand Recorder', frame)
        key = cv2.waitKey(1) & 0xFF

        # Si touche 0,1,2,3 pressée et points valides -> enregistrer dans CSV
        if key in [ord('0'), ord('1'), ord('2'), ord('3')] and self.current_points is not None:
            label = int(chr(key))
            self.current_label = label
            self.save_to_csv(self.current_points, label)
            self.get_logger().info(f'Donnée enregistrée avec label: {label}')

        # Touche q pour quitter
        if key == ord('q'):
            self.get_logger().info('Arrêt du noeud...')
            self.destroy_node()
            cv2.destroyAllWindows()
            rclpy.shutdown()

    def save_to_csv(self, points, label):
        with open(self.csv_file_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(points + [label])

def main(args=None):
    rclpy.init(args=args)
    node = HandRecorder()
    rclpy.spin(node)

if __name__ == '__main__':
    main()

