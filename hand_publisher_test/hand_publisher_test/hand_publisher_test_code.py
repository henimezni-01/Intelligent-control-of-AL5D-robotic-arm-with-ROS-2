import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray
from cv_bridge import CvBridge
import cv2
import mediapipe as mp

class HandPublisher(Node):
    def __init__(self):
        super().__init__('hand_publisher')

        # Souscription au flux d'image RGB
        self.subscription = self.create_subscription(
            Image,
            '/camera/rgb/image_raw',
            self.image_callback,
            10)

        # Publisher pour les coordonnées des mains
        self.publisher_ = self.create_publisher(Float32MultiArray, '/hand_coordinates', 10)

        # Initialisation MediaPipe
        self.bridge = CvBridge()
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(static_image_mode=False,
                                         max_num_hands=1,
                                         min_detection_confidence=0.7)

        self.mp_drawing = mp.solutions.drawing_utils
        self.get_logger().info('Node hand_publisher prêt !')

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(image_rgb)

        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            points = []
            for lm in hand_landmarks.landmark:
                points.extend([lm.x, lm.y, lm.z])

            msg_out = Float32MultiArray()
            msg_out.data = points
            self.publisher_.publish(msg_out)

            # Dessiner les landmarks sur l'image
            self.mp_drawing.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)

            self.get_logger().info(f'Coordonnées publiées : {len(points)}')

        # Affichage live
        cv2.imshow('Hand Publisher (Kinect)', frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            self.get_logger().info('Arrêt du noeud hand_publisher...')
            self.destroy_node()
            cv2.destroyAllWindows()
            rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    node = HandPublisher()
    rclpy.spin(node)

if __name__ == '__main__':
    main()

