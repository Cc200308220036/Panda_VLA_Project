import time
import numpy as np
import mujoco
import mujoco.viewer

from envs.pick_place_env import PickPlaceEnv
from controllers.ee_delta_controller import EEDeltaController


def make_action(step):
    """
    Return [dx, dy, dz, gripper].
    This is only for testing ee_delta_controller.
    """
    if step < 80:
        return 0.004, 0.0, 0.0, 1.0      # move +x
    elif step < 160:
        return 0.0, 0.004, 0.0, 1.0      # move +y
    elif step < 220:
        return 0.0, 0.0, -0.003, 1.0     # move down
    elif step < 280:
        return 0.0, 0.0, 0.003, 1.0      # move up
    elif step < 340:
        return 0.0, 0.0, 0.0, -1.0       # close gripper
    else:
        return 0.0, 0.0, 0.0, 1.0        # open gripper


def main():
    env = PickPlaceEnv(
        render_width=224,
        render_height=224,
        camera_name="top",
        seed=0,
    )

    controller = EEDeltaController(
        model=env.model,
        data=env.data,
        joint_names=env.joint_names,
        ee_body_name="hand",
        table_top_z=env.table_top_z,
        max_pos_delta=0.015,
        min_ee_z_above_table=0.04,
        workspace_low=(0.25, -0.35, 0.43),
        workspace_high=(0.90, 0.35, 1.00),
        open_gripper_ctrl=255.0,
        close_gripper_ctrl=0.0,
    )

    obs = env.reset()

    print("Initial ee_pos:", obs["ee_pos"])
    print("Initial cube_pos:", obs["cube_pos"])
    print("Initial target_pos:", obs["target_pos"])

    step = 0

    with mujoco.viewer.launch_passive(env.model, env.data) as viewer:
        while viewer.is_running():
            dx, dy, dz, gripper = make_action(step)

            ctrl, info = controller.compute_control(
                dx=dx,
                dy=dy,
                dz=dz,
                droll=0.0,
                dpitch=0.0,
                dyaw=0.0,
                gripper=gripper,
            )

            env.data.ctrl[:] = ctrl

            # Important:
            # Do physics stepping directly here.
            # Do not call env.step_env(), because env.step_env() will render image,
            # which is unnecessary when using MuJoCo native viewer.
            for _ in range(10):
                mujoco.mj_step(env.model, env.data)

            if step % 30 == 0:
                ee_pos, _ = env.get_ee_pose()
                print(
                    f"step={step:04d}, "
                    f"ee_pos={ee_pos}, "
                    f"ik={info['ik_success']}, "
                    f"ik_err={info['ik_error']:.4f}, "
                    f"gripper_ctrl={info['gripper_ctrl']}"
                )

            viewer.sync()

            # This controls real-time visualization speed.
            time.sleep(0.01)

            step += 1

    env.close()


if __name__ == "__main__":
    main()
