import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from sensor_msgs.msg import JointState
from builtin_interfaces.msg import Duration
from std_msgs.msg import Float32
import numpy as np

class MultiJointTrajectoryPublisher(Node):
    def __init__(self):
        # Initialize the node
        super().__init__('multi_joint_trajectory_publisher')

        # Publishers for arm and gripper
        self.arm_publisher_ = self.create_publisher(JointTrajectory, '/arm_controller/joint_trajectory', 10)
        self.gripper_publisher_ = self.create_publisher(JointTrajectory, '/gripper_controller/joint_trajectory', 10)
        
        # Subscribers for control topics
        self.angle_coude_sub_ = self.create_subscription(
            Float32, '/angle_coude', self.angle_coude_callback, 10
        )
        self.angle_poignet_sub_ = self.create_subscription(
            Float32, '/angle_poignet', self.angle_poignet_callback, 10
        )
        self.distance_pouce_index_sub_ = self.create_subscription(
            Float32, '/distance_pouce_index', self.distance_pouce_index_callback, 10
        )
        
        # Subscriber for joint states
        self.joint_state_sub_ = self.create_subscription(
            JointState, '/joint_states', self.joint_state_callback, 10
        )

        # Timers for periodic checks
        self.arm_timer_period = 0.2  # seconds
        self.arm_timer = self.create_timer(self.arm_timer_period, self.arm_timer_callback)
        
        self.gripper_timer_period = 0.2  # seconds
        self.gripper_timer = self.create_timer(self.gripper_timer_period, self.gripper_timer_callback)

        # Current joint positions
        self.current_positions = None
        self.arm_joint_indices = None
        self.gripper_joint_indices = None
        
        # Target positions
        self.arm_target_positions = [0.0, 0.0, 0.0, 0.0, 0.0]  # Initial zeros
        self.gripper_target_position = 0.0  # Initial zero
        
        # New command flags
        self.new_elbow_command = False
        self.new_wrist_command = False
        self.new_gripper_command = False
        
        # Completion flags
        self.arm_waiting_for_completion = False
        self.gripper_waiting_for_completion = False
        
        # Tolerance for position matching
        self.position_tolerance = 0.02  # 0.02 radians tolerance
        
        # Joint names
        self.arm_joint_names = ['base_joint', 'shoulder_joint', 'elbow_joint', 'wrist_1_joint', 'wrist_2_joint']
        self.gripper_joint_names = ['gripper_left_joint']  # Controller will handle mimic

        # Paramètres de vitesse et accélération (à ajuster selon votre robot)
        self.max_arm_velocity = 1.5  # rad/s - vitesse safe pour les joints du bras
        self.max_gripper_velocity = 1.0  # rad/s - vitesse pour la pince
        self.max_arm_acceleration = 0.8  # rad/s²
        self.max_gripper_acceleration = 0.6  # rad/s²

    def angle_coude_callback(self, msg):
        """Convert elbow angle from degrees to radians and schedule update"""
        elbow_angle_rad = np.deg2rad(msg.data-120)
        self.get_logger().info(f'Received elbow angle: {msg.data}° -> {elbow_angle_rad:.3f} rad')
        
        # Update only the elbow joint (index 2)
        self.arm_target_positions[2] = elbow_angle_rad
        self.new_elbow_command = True

    def angle_poignet_callback(self, msg):
        """Convert wrist angle from degrees to radians and schedule update"""
        wrist_angle_rad = np.deg2rad(msg.data-180)
        self.get_logger().info(f'Received wrist angle: {msg.data}° -> {wrist_angle_rad:.3f} rad')
        
        # Update only the wrist_1 joint (index 3)
        self.arm_target_positions[3] = wrist_angle_rad
        self.new_wrist_command = True

    def distance_pouce_index_callback(self, msg):
        """Convert distance in pixels to gripper position"""
        # Example conversion: distance in pixels to gripper position
        # You may need to adjust this conversion based on your specific setup
        distance_pixels = msg.data
        gripper_position = self.convert_distance_to_gripper(distance_pixels)
        
        self.get_logger().info(f'Received distance: {distance_pixels} pixels -> gripper: {gripper_position:.3f}')
        
        self.gripper_target_position = gripper_position
        self.new_gripper_command = True

    def convert_distance_to_gripper(self, distance_pixels):
        """Convert distance in pixels to gripper joint position"""
        # Adjust these values based on your specific setup
        min_distance = 0.0   # minimum distance in pixels (closed)
        max_distance = 200.0  # maximum distance in pixels (open)
        min_gripper = 0.0     # gripper closed position
        max_gripper = 0.05    # gripper open position (adjust based on your gripper)
        
        # Clamp and normalize the distance
        clamped_distance = max(min(distance_pixels, max_distance), min_distance)
        normalized = (clamped_distance - min_distance) / (max_distance - min_distance)
        
        return min_gripper + normalized * (max_gripper - min_gripper)

    def joint_state_callback(self, msg):
        """Store current joint positions and detect joint indices"""
        self.current_positions = msg.position
        
        # Detect arm joint indices if not already done
        if self.arm_joint_indices is None:
            self.arm_joint_indices = []
            for arm_joint_name in self.arm_joint_names:
                if arm_joint_name in msg.name:
                    self.arm_joint_indices.append(msg.name.index(arm_joint_name))
                else:
                    self.get_logger().warn(f"Arm joint {arm_joint_name} not found in joint_states")
            
            if len(self.arm_joint_indices) == 5:
                self.get_logger().info(f"Found arm joints at indices: {self.arm_joint_indices}")
        
        # Detect gripper joint indices if not already done
        if self.gripper_joint_indices is None:
            self.gripper_joint_indices = []
            for gripper_joint_name in self.gripper_joint_names:
                if gripper_joint_name in msg.name:
                    self.gripper_joint_indices.append(msg.name.index(gripper_joint_name))
                else:
                    self.get_logger().warn(f"Gripper joint {gripper_joint_name} not found in joint_states")
            
            if len(self.gripper_joint_indices) == 1:
                self.get_logger().info(f"Found gripper joint at index: {self.gripper_joint_indices[0]}")

        # Check arm trajectory completion
        if self.arm_waiting_for_completion:
            if self.has_arm_reached_target():
                self.get_logger().info('Arm trajectory completed!')
                self.arm_waiting_for_completion = False

        # Check gripper trajectory completion
        if self.gripper_waiting_for_completion:
            if self.has_gripper_reached_target():
                self.get_logger().info('Gripper trajectory completed!')
                self.gripper_waiting_for_completion = False

    def get_arm_positions(self):
        """Extract only the arm joint positions"""
        if self.current_positions is None or self.arm_joint_indices is None:
            return None
        
        try:
            return [self.current_positions[i] for i in self.arm_joint_indices]
        except IndexError:
            return None

    def get_gripper_position(self):
        """Extract only the gripper joint position"""
        if self.current_positions is None or self.gripper_joint_indices is None:
            return None
        
        try:
            return self.current_positions[self.gripper_joint_indices[0]]
        except IndexError:
            return None

    def has_arm_reached_target(self):
        """Check if arm has reached target positions"""
        current_arm_positions = self.get_arm_positions()
        if current_arm_positions is None or self.arm_target_positions is None:
            return False
        
        current = np.array(current_arm_positions)
        target = np.array(self.arm_target_positions)
        errors = np.abs(current - target)
        return np.all(errors <= self.position_tolerance)

    def has_gripper_reached_target(self):
        """Check if gripper has reached target position"""
        current_gripper_position = self.get_gripper_position()
        if current_gripper_position is None:
            return False
        
        error = abs(current_gripper_position - self.gripper_target_position)
        return error <= self.position_tolerance

    def arm_timer_callback(self):
        """Check if we need to publish a new arm trajectory"""
        if self.arm_waiting_for_completion:
            return
        
        if self.arm_joint_indices is None:
            return
        
        # Check if we have new commands
        if not (self.new_elbow_command or self.new_wrist_command):
            return
        
        # Create and publish arm trajectory
        msg = JointTrajectory()
        msg.joint_names = self.arm_joint_names
        
        point = JointTrajectoryPoint()
        point.positions = self.arm_target_positions.copy()
        point.velocities = []
        point.accelerations = []
        point.effort = []
        point.time_from_start = Duration(sec=0, nanosec=0)
        
        msg.points.append(point)
        msg.header.stamp.sec = 0
        msg.header.stamp.nanosec = 0
        msg.header.frame_id = ''

        self.arm_publisher_.publish(msg)
        self.arm_waiting_for_completion = True
        
        # Reset command flags
        self.new_elbow_command = False
        self.new_wrist_command = False
        
        self.get_logger().info(f'Published arm trajectory: {point.positions}')

    def gripper_timer_callback(self):
        """Check if we need to publish a new gripper trajectory"""
        if self.gripper_waiting_for_completion:
            return
        
        if self.gripper_joint_indices is None:
            return
        
        if not self.new_gripper_command:
            return
        
        # Create and publish gripper trajectory
        msg = JointTrajectory()
        msg.joint_names = self.gripper_joint_names
        
        point = JointTrajectoryPoint()
        point.positions = [self.gripper_target_position]
        point.velocities = []
        point.accelerations = []
        point.effort = []
        point.time_from_start = Duration(sec=0, nanosec=0)
        
        msg.points.append(point)
        msg.header.stamp.sec = 0
        msg.header.stamp.nanosec = 0
        msg.header.frame_id = ''

        self.gripper_publisher_.publish(msg)
        self.gripper_waiting_for_completion = True
        self.new_gripper_command = False
        
        self.get_logger().info(f'Published gripper trajectory: {point.positions}')

def main(args=None):
    rclpy.init(args=args)
    multi_joint_trajectory_publisher = MultiJointTrajectoryPublisher()
    
    try:
        rclpy.spin(multi_joint_trajectory_publisher)
    except KeyboardInterrupt:
        pass
    finally:
        multi_joint_trajectory_publisher.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()