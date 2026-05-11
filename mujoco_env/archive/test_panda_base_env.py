import os
import cv2
import numpy as np

from envs.panda_base_env import PandaBaseEnv


def main():
    xml_path = os.path.expanduser(
        "~/panda_vla_project/mujoco_env/assets/robots/franka_panda/scene.xml"
    )

    env = PandaBaseEnv(
        xml_path=xml_path,
        render_width=224,
        render_height=224,
        camera_name=None,
    )

    obs = env.reset()

    print("joint_pos:", obs["joint_pos"])
    print("joint_vel:", obs["joint_vel"])
    print("gripper_qpos:", obs["gripper_qpos"])
    print("ee_pos:", obs["ee_pos"])
    print("ee_quat:", obs["ee_quat"])
    print("image shape:", obs["image"].shape)

    ctrl = np.zeros(env.model.nu)

    for i in range(300):
        # 前 7 维为 Panda 关节位置 actuator
        ctrl[:7] = env.home_qpos

        # 第 8 维为夹爪 actuator，先给一个打开值
        if env.model.nu >= 8:
            ctrl[7] = 255.0

        obs = env.step(ctrl=ctrl, n_substeps=5)

        img = cv2.cvtColor(obs["image"], cv2.COLOR_RGB2BGR)
        cv2.imshow("PandaBaseEnv", img)

        if cv2.waitKey(1) == ord("q"):
            break

    env.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
