import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32, Float32
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

import cv2
import numpy as np
import mediapipe as mp
import time

class GestureAngleReactor(Node):
    def __init__(self):
        super().__init__('gesture_angle_reactor')

        # Subscription au topic de prédiction des doigts levés
        self.subscription_fingers = self.create_subscription(Int32, '/mlp_prediction', self.finger_callback, 10)
        # Subscription au flux vidéo de la caméra
        self.subscription_image = self.create_subscription(Image, '/camera/rgb/image_raw', self.image_callback, 10)

        self.bridge = CvBridge()
        self.current_action = None

        # Gestion blocage réception topic mlp_prediction et attente 4s
        self.block_finger_callback = False
        self.distance_start_time = None
        self.waiting_for_measure = False  # attente 4s avant mesure

        # Gestion freeze frame 4s après mesure
        self.freeze_frame = False
        self.freeze_start_time = None
        self.frozen_frame = None

        # Initialisation MediaPipe
        self.pose = mp.solutions.pose.Pose()
        self.hands = mp.solutions.hands.Hands(static_image_mode=False,
                                              max_num_hands=2,
                                              min_detection_confidence=0.5,
                                              min_tracking_confidence=0.5)

        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose
        self.mp_hands = mp.solutions.hands

        # Création des publishers Float32 pour les résultats
        self.pub_angle_coude = self.create_publisher(Float32, '/angle_coude', 10)
        self.pub_angle_poignet = self.create_publisher(Float32, '/angle_poignet', 10)
        self.pub_distance_pouce_index = self.create_publisher(Float32, '/distance_pouce_index', 10)

    def finger_callback(self, msg):
        if self.block_finger_callback:
            return

        if msg.data in [1, 2, 3]:
            self.get_logger().info(f"Commande {msg.data} reçue : début attente 4 secondes. Blocage réception topic mlp_prediction.")
            self.block_finger_callback = True
            self.waiting_for_measure = True
            self.distance_start_time = time.time()
            self.current_action = msg.data
        else:
            self.current_action = msg.data
            self.get_logger().info(f"Nombre de doigts reçu : {self.current_action}")

    def calculate_angle(self, a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        ba = a - b
        bc = c - b
        cos_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
        angle = np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))
        return angle

    def image_callback(self, msg):
        # Si freeze activé, on affiche frame figée, on attend 4s puis on reprend
        if self.freeze_frame:
            elapsed_freeze = time.time() - self.freeze_start_time
            cv2.imshow("Skeleton & Hand Viewer", self.frozen_frame)
            if elapsed_freeze >= 4.0:
                self.get_logger().info("Fin du freeze de la frame, retour au flux normal.")
                self.freeze_frame = False
                self.frozen_frame = None
                # Réactivation réception mlp_prediction et reset action
                self.block_finger_callback = False
                self.current_action = None
            cv2.waitKey(1)
            return

        # Pas d'action à traiter
        if self.current_action not in [1, 2, 3]:
            return

        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        result_pose = self.pose.process(rgb)
        result_hand = self.hands.process(rgb)

        h, w, _ = frame.shape

        # Gestion attente 4 secondes avant mesure
        if self.waiting_for_measure:
            elapsed = time.time() - self.distance_start_time
            if elapsed >= 4.0:
                self.waiting_for_measure = False
                self.get_logger().info("Temps d'attente écoulé, mesure en cours.")
            else:
                cv2.putText(frame, f"Attente {4 - int(elapsed)} sec...", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                cv2.imshow("Skeleton & Hand Viewer", frame)
                cv2.waitKey(1)
                return  # On attend avant de mesurer

        # Après attente, faire la mesure selon l'action
        if self.current_action == 1:  # Angle coude
            if result_pose.pose_landmarks:
                lm = result_pose.pose_landmarks.landmark
                keypoints = [(p.x, p.y) for p in lm]
                try:
                    right_visibility = sum([lm[i].visibility for i in [12, 14, 16]])
                    left_visibility = sum([lm[i].visibility for i in [11, 13, 15]])

                    if right_visibility >= left_visibility:
                        angle_coude = self.calculate_angle(keypoints[12], keypoints[14], keypoints[16])
                        pts = [12, 14, 16]
                    else:
                        angle_coude = self.calculate_angle(keypoints[11], keypoints[13], keypoints[15])
                        pts = [11, 13, 15]

                    for i in range(len(pts)-1):
                        x1, y1 = int(keypoints[pts[i]][0] * w), int(keypoints[pts[i]][1] * h)
                        x2, y2 = int(keypoints[pts[i+1]][0] * w), int(keypoints[pts[i+1]][1] * h)
                        cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                        cv2.circle(frame, (x1, y1), 7, (0, 0, 255), -1)
                        cv2.circle(frame, (x2, y2), 7, (0, 0, 255), -1)

                    label = f"Coude: {angle_coude:.2f}°"
                    self.get_logger().info(f"[ACTION 1] Angle du coude = {angle_coude:.2f}°")

                    # Publication de l'angle coude
                    angle_msg = Float32()
                    angle_msg.data = float(angle_coude)
                    self.pub_angle_coude.publish(angle_msg)
                    self.get_logger().info(f"Publié angle coude: {angle_msg.data:.2f}° sur /angle_coude")

                    # Freeze frame 4s
                    self.frozen_frame = frame.copy()
                    self.freeze_frame = True
                    self.freeze_start_time = time.time()

                    self.current_action = None

                except Exception as e:
                    self.get_logger().warn(f"Erreur landmarks coude: {e}")

        elif self.current_action == 2:  # Angle poignet
            if result_pose.pose_landmarks:
                lm = result_pose.pose_landmarks.landmark
                keypoints = [(p.x, p.y) for p in lm]
                try:
                    right_visibility = sum([lm[i].visibility for i in [14, 16, 20]])
                    left_visibility = sum([lm[i].visibility for i in [13, 15, 19]])

                    if right_visibility >= left_visibility:
                        angle_poignet = self.calculate_angle(keypoints[14], keypoints[16], keypoints[20])
                        pts = [14, 16, 20]
                    else:
                        angle_poignet = self.calculate_angle(keypoints[13], keypoints[15], keypoints[19])
                        pts = [13, 15, 19]

                    for i in range(len(pts)-1):
                        x1, y1 = int(keypoints[pts[i]][0] * w), int(keypoints[pts[i]][1] * h)
                        x2, y2 = int(keypoints[pts[i+1]][0] * w), int(keypoints[pts[i+1]][1] * h)
                        cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                        cv2.circle(frame, (x1, y1), 7, (0, 0, 255), -1)
                        cv2.circle(frame, (x2, y2), 7, (0, 0, 255), -1)

                    label = f"Poignet: {angle_poignet:.2f}°"
                    self.get_logger().info(f"[ACTION 2] Angle du poignet = {angle_poignet:.2f}°")

                    # Publication de l'angle poignet
                    poignet_msg = Float32()
                    poignet_msg.data = float(angle_poignet)
                    self.pub_angle_poignet.publish(poignet_msg)
                    self.get_logger().info(f"Publié angle poignet: {poignet_msg.data:.2f}° sur /angle_poignet")

                    # Freeze frame 4s
                    self.frozen_frame = frame.copy()
                    self.freeze_frame = True
                    self.freeze_start_time = time.time()

                    self.current_action = None

                except Exception as e:
                    self.get_logger().warn(f"Erreur landmarks poignet: {e}")

        elif self.current_action == 3:  # Distance pouce-index
            if result_hand.multi_hand_landmarks:
                hand = result_hand.multi_hand_landmarks[0]
                thumb_tip = hand.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
                index_tip = hand.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
                pt1 = np.array([thumb_tip.x * w, thumb_tip.y * h])
                pt2 = np.array([index_tip.x * w, index_tip.y * h])
                distance = np.linalg.norm(pt1 - pt2)

                cv2.circle(frame, (int(pt1[0]), int(pt1[1])), 10, (255, 0, 0), -1)
                cv2.circle(frame, (int(pt2[0]), int(pt2[1])), 10, (255, 0, 0), -1)
                cv2.line(frame, (int(pt1[0]), int(pt1[1])), (int(pt2[0]), int(pt2[1])), (255, 0, 255), 3)

                self.get_logger().info(f"[ACTION 3] Distance pouce-index mesurée = {distance:.2f} px")

                # Publication de la distance pouce-index
                dist_msg = Float32()
                dist_msg.data = float(distance)
                self.pub_distance_pouce_index.publish(dist_msg)
                self.get_logger().info(f"Publié distance pouce-index: {dist_msg.data:.2f} px sur /distance_pouce_index")

                # Freeze frame 4s
                self.frozen_frame = frame.copy()
                self.freeze_frame = True
                self.freeze_start_time = time.time()

                self.current_action = None

        # Affichage avec texte si pas freeze (freeze affiche la frame figée plus haut)
        if not self.freeze_frame:
            label = ""
            if self.current_action == 1:
                label = f"Mesure angle coude en attente..."
            elif self.current_action == 2:
                label = f"Mesure angle poignet en attente..."
            elif self.current_action == 3:
                label = f"Mesure distance pouce-index en attente..."

            if label:
                cv2.putText(frame, label, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

            cv2.imshow("Skeleton & Hand Viewer", frame)
            cv2.waitKey(1)


def main(args=None):
    rclpy.init(args=args)
    node = GestureAngleReactor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()

