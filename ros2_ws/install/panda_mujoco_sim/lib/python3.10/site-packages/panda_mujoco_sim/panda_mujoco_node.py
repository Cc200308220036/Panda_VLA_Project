import os
import sys
import numpy as np

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import JointState, Image
from geometry_msgs.msg import PoseStamped
from trajectory_msgs.msg import JointTrajectory
from cv_bridge import CvBridge

from panda_mujoco_msgs.msg import EEDeltaCommand


PROJECT_ROOT = os.path.expanduser("~/panda_vla_project")
MUJOCO_ENV_PATH = os.path.join(PROJECT_ROOT, "mujoco_env")
sys.path.append(MUJOCO_ENV_PATH)

from envs.panda_base_env import PandaBaseEnv
from controllers.ee_delta_controller import EEDeltaController


class PandaMujocoNode(Node):
    def __init__(self):
        super().__init__("panda_mujoco_node")

        xml_path = os.path.join(
            PROJECT_ROOT,
            "mujoco_env/assets/robots/franka_panda/panda_pick_place.xml",
        )

        self.env = PandaBaseEnv(
            xml_path=xml_path,
            render_width=640,
            render_height=480,
            camera_name="front_policy",
        )

        self.bridge = CvBridge()

        self.joint_names = [
            "joint1",
            "joint2",
            "joint3",
            "joint4",
            "joint5",
            "joint6",
            "joint7",
        ]

        self.current_ctrl = np.zeros(self.env.model.nu, dtype=np.float64)
        self.current_ctrl[:7] = self.env.home_qpos

        self.ee_delta_controller = EEDeltaController(
            model=self.env.model,
            data=self.env.data,
            joint_names=self.joint_names,
            ee_body_name="hand",
            table_top_z=0.40,
            max_pos_delta=0.01,
            min_ee_z_above_table=0.04,
            workspace_low=(0.25, -0.35, 0.43),
            workspace_high=(0.85, 0.35, 0.95),
            open_gripper_ctrl=255.0,
            close_gripper_ctrl=0.0,
        )

        if self.env.model.nu >= 8:
            self.current_ctrl[7] = 255.0

        self.joint_state_pub = self.create_publisher(
            JointState,
            "/panda/joint_states",
            10,
        )

        self.ee_pose_pub = self.create_publisher(
            PoseStamped,
            "/panda/ee_pose",
            10,
        )

        self.image_pub = self.create_publisher(
            Image,
            "/panda/front/image_raw",
            10,
        )

        self.joint_cmd_sub = self.create_subscription(
            JointTrajectory,
            "/panda/command/joint_position",
            self.on_joint_position_command,
            10,
        )

        self.ee_delta_sub = self.create_subscription(
            EEDeltaCommand,
            "/panda/command/ee_delta",
            self.on_ee_delta_command,
            10,
        )

        self.timer = self.create_timer(0.01, self.on_timer)

        self.get_logger().info("Panda MuJoCo node started.")

    def on_joint_position_command(self, msg: JointTrajectory):
        if len(msg.points) == 0:
            self.get_logger().warn("Received empty JointTrajectory.")
            return

        point = msg.points[-1]

        if len(point.positions) < 7:
            self.get_logger().warn("JointTrajectory point has fewer than 7 positions.")
            return

        q_target = np.array(point.positions[:7], dtype=np.float64)
        self.current_ctrl[:7] = q_target

    def on_ee_delta_command(self, msg: EEDeltaCommand):
        ctrl, info = self.ee_delta_controller.compute_control(
            dx=msg.dx,
            dy=msg.dy,
            dz=msg.dz,
            droll=msg.droll,
            dpitch=msg.dpitch,
            dyaw=msg.dyaw,
            gripper=msg.gripper,
        )

        self.current_ctrl[:] = ctrl

        if not info["ik_success"]:
            self.get_logger().warn(
                f"IK failed. error={info['ik_error']:.4f}, "
                f"target={info['target_pos']}"
            )


    def on_timer(self):
        obs = self.env.step(ctrl=self.current_ctrl, n_substeps=5)

        stamp = self.get_clock().now().to_msg()

        self.publish_joint_states(obs, stamp)
        self.publish_ee_pose(obs, stamp)
        self.publish_image(obs, stamp)

    def publish_joint_states(self, obs, stamp):
        msg = JointState()
        msg.header.stamp = stamp
        msg.name = self.joint_names
        msg.position = obs["joint_pos"].astype(float).tolist()
        msg.velocity = obs["joint_vel"].astype(float).tolist()
        msg.effort = []

        self.joint_state_pub.publish(msg)

    def publish_ee_pose(self, obs, stamp):
        msg = PoseStamped()
        msg.header.stamp = stamp
        msg.header.frame_id = "world"

        pos = obs["ee_pos"]
        quat = obs["ee_quat"]

        msg.pose.position.x = float(pos[0])
        msg.pose.position.y = float(pos[1])
        msg.pose.position.z = float(pos[2])

        # MuJoCo quat: w, x, y, z
        # ROS quat: x, y, z, w
        msg.pose.orientation.x = float(quat[1])
        msg.pose.orientation.y = float(quat[2])
        msg.pose.orientation.z = float(quat[3])
        msg.pose.orientation.w = float(quat[0])

        self.ee_pose_pub.publish(msg)

    def publish_image(self, obs, stamp):
        rgb = obs["image"]

        msg = self.bridge.cv2_to_imgmsg(rgb, encoding="rgb8")
        msg.header.stamp = stamp
        msg.header.frame_id = "front_camera"

        self.image_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = PandaMujocoNode()

    try:
        rclpy.spin(node)
    finally:
        node.env.close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
