import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import freenect
import cv2

class KinectPublisher(Node):
    def __init__(self):
        super().__init__('kinect_publisher')
        self.publisher = self.create_publisher(Image, '/camera/rgb/image_raw', 10)
        self.bridge = CvBridge()
        self.timer = self.create_timer(1.0 / 30.0, self.timer_callback)  # 30 Hz

    def timer_callback(self):
        frame, _ = freenect.sync_get_video()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "kinect_rgb_optical_frame"
        self.publisher.publish(msg)
        self.get_logger().info('Image publiée')
        #self.show(frame)

    #def show(self, frame):
        #cv2.imshow('Kinect Live', frame)
        #cv2.waitKey(1)  # Nécessaire pour que la fenêtre s'actualise

def main(args=None):
    rclpy.init(args=args)
    node = KinectPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        cv2.destroyAllWindows()
        rclpy.shutdown()


