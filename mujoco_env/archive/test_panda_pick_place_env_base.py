import os
import cv2
import numpy as np

from envs.panda_base_env import PandaBaseEnv


def main():
    xml_path = os.path.expanduser(
        "~/panda_vla_project/mujoco_env/assets/robots/franka_panda/panda_pick_place.xml"
    )

    env = PandaBaseEnv(
        xml_path=xml_path,
        render_width=640,
        render_height=480,
        camera_name="front",
    )

    obs = env.reset()

    print("joint_pos:", obs["joint_pos"])
    print("joint_vel:", obs["joint_vel"])
    print("gripper_qpos:", obs["gripper_qpos"])
    print("ee_pos:", obs["ee_pos"])
    print("image shape:", obs["image"].shape)

    img = cv2.cvtColor(obs["image"], cv2.COLOR_RGB2BGR)
    cv2.imwrite("pick_place_front_from_env.png", img)
    print("saved pick_place_front_from_env.png")

    env.close()


if __name__ == "__main__":
    main()
