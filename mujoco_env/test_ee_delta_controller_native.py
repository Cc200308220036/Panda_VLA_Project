import cv2
import numpy as np

from envs.pick_place_env import PickPlaceEnv
from controllers.ee_delta_controller import EEDeltaController


def main():
    env = PickPlaceEnv(
        render_width=640,
        render_height=480,
        camera_name="front_policy",
        seed=0,
    )

    controller = EEDeltaController(
        model=env.model,
        data=env.data,
        joint_names=env.joint_names,
        ee_body_name="hand",
        table_top_z=env.table_top_z,
        max_pos_delta=0.005,
        min_ee_z_above_table=0.04,
        workspace_low=(0.25, -0.35, 0.43),
        workspace_high=(0.85, 0.35, 0.95),
        open_gripper_ctrl=255.0,
        close_gripper_ctrl=0.0,
    )

    obs = env.reset()

    print("Initial ee_pos:", obs["ee_pos"])
    print("Initial cube_pos:", obs["cube_pos"])
    print("Initial target_pos:", obs["target_pos"])

    # 测试动作序列：
    # 1. x 正方向移动
    # 2. y 正方向移动
    # 3. z 下降
    # 4. z 上升
    # 5. open / close gripper
    action_plan = []

    for _ in range(50):
        action_plan.append([0.005, 0.0, 0.0, 1.0])

    for _ in range(50):
        action_plan.append([0.0, 0.005, 0.0, 1.0])

    for _ in range(40):
        action_plan.append([0.0, 0.0, -0.005, 1.0])

    for _ in range(40):
        action_plan.append([0.0, 0.0, 0.005, 1.0])

    for _ in range(30):
        action_plan.append([0.0, 0.0, 0.0, -1.0])

    for _ in range(30):
        action_plan.append([0.0, 0.0, 0.0, 1.0])

    for step, a in enumerate(action_plan):
        dx, dy, dz, gripper = a

        ctrl, info = controller.compute_control(
            dx=dx,
            dy=dy,
            dz=dz,
            gripper=gripper,
        )

        obs, reward, done, env_info = env.step_env(
            ctrl=ctrl,
            n_substeps=20,
        )

        if step % 20 == 0:
            print(
                f"step={step:04d} "
                f"ee={obs['ee_pos']} "
                f"ik={info['ik_success']} "
                f"ik_err={info['ik_error']:.4f} "
                f"gripper_ctrl={info['gripper_ctrl']}"
            )

        img = cv2.cvtColor(obs["image"], cv2.COLOR_RGB2BGR)
        cv2.imshow("ee_delta_controller_native", img)

        key = cv2.waitKey(20)
        if key == ord("q"):
            break

    env.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
