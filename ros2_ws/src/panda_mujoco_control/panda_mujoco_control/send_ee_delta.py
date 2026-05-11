import rclpy
from rclpy.node import Node

from panda_mujoco_msgs.msg import EEDeltaCommand


class EEDeltaCommander(Node):
    def __init__(self):
        super().__init__("ee_delta_commander")

        self.pub = self.create_publisher(
            EEDeltaCommand,
            "/panda/command/ee_delta",
            10,
        )

        self.step = 0
        self.timer = self.create_timer(0.05, self.on_timer)

    def on_timer(self):
        self.step += 1

        msg = EEDeltaCommand()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "world"

        msg.dx = 0.0
        msg.dy = 0.0
        msg.dz = 0.0
        msg.droll = 0.0
        msg.dpitch = 0.0
        msg.dyaw = 0.0
        msg.gripper = 1.0

        if self.step < 30:
            msg.dx = 0.01
        elif self.step < 60:
            msg.dy = 0.005
        elif self.step < 90:
            msg.dz = -0.005
        elif self.step < 120:
            msg.dz = 0.005
        elif self.step < 150:
            msg.gripper = -1.0
        else:
            msg.gripper = 1.0

        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = EEDeltaCommander()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
