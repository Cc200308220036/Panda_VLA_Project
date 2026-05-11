import math
import rclpy
from rclpy.node import Node

from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint


class JointPositionCommander(Node):
    def __init__(self):
        super().__init__("joint_position_commander")

        self.pub = self.create_publisher(
            JointTrajectory,
            "/panda/command/joint_position",
            10,
        )

        self.joint_names = [
            "joint1",
            "joint2",
            "joint3",
            "joint4",
            "joint5",
            "joint6",
            "joint7",
        ]

        self.t = 0.0
        self.timer = self.create_timer(0.02, self.on_timer)

    def on_timer(self):
        self.t += 0.02

        q = [
            0.0,
            -0.785,
            0.0,
            -2.356,
            0.0,
            1.571,
            0.785,
        ]

        q[0] = 0.2 * math.sin(self.t)

        msg = JointTrajectory()
        msg.joint_names = self.joint_names

        point = JointTrajectoryPoint()
        point.positions = q
        point.time_from_start.sec = 0
        point.time_from_start.nanosec = int(20e6)

        msg.points.append(point)
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = JointPositionCommander()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
