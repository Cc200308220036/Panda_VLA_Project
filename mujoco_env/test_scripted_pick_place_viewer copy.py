import time
import mujoco
import mujoco.viewer
import argparse

from envs.pick_place_env import PickPlaceEnv
from controllers.ee_delta_controller import EEDeltaController
from experts.scripted_pick_place import ScriptedPickPlaceExpert, PickPlaceStage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    env = PickPlaceEnv(
        render_width=224,
        render_height=224,
        camera_name="top",
        seed=args.seed,
    )


    controller = EEDeltaController(
        model=env.model,
        data=env.data,
        joint_names=env.joint_names,
        ee_body_name="hand",
        table_top_z=env.table_top_z,
        max_pos_delta=0.008,
        min_ee_z_above_table=0.035,
        workspace_low=(0.25, -0.35, 0.43),
        workspace_high=(0.90, 0.35, 1.00),
        open_gripper_ctrl=255.0,
        close_gripper_ctrl=0.0,
    )

    expert = ScriptedPickPlaceExpert(
        env=env,
        max_delta=0.006,
        reach_tol=0.020,
        z_reach_tol=0.020,
        pregrasp_height=0.20,
        grasp_height=0.105,
        lift_height=0.25,
        place_height=0.22,
        place_down_height=0.115,
        retreat_height=0.25,
        close_steps=120,
        open_steps=70,
        place_xy_offset=(0.0, 0.0),
    )

    obs = env.reset()
    expert.reset()

    print("Initial ee_pos:", obs["ee_pos"])
    print("Initial cube_pos:", obs["cube_pos"])
    print("Initial target_pos:", obs["target_pos"])

    max_steps = 900
    step = 0

    with mujoco.viewer.launch_passive(env.model, env.data) as viewer:
        while viewer.is_running() and step < max_steps:
            action, expert_info = expert.get_action()

            ctrl, ctrl_info = controller.compute_control(
                dx=action[0],
                dy=action[1],
                dz=action[2],
                droll=action[3],
                dpitch=action[4],
                dyaw=action[5],
                gripper=action[6],
            )

            env.step_sim(ctrl=ctrl, n_substeps=10)

            if step % 20 == 0:
                ee_pos, _ = env.get_ee_pose()
                cube_pos = env.get_cube_pos()
                target_pos = env.get_target_pos()

                # print(
                #     f"step={step:04d} "
                #     f"stage={expert_info['stage']:20s} "
                #     f"ee={ee_pos} "
                #     f"cube={cube_pos} "
                #     f"target={target_pos} "
                #     f"ik={ctrl_info['ik_success']} "
                #     f"ik_err={ctrl_info['ik_error']:.4f} "
                #     f"grasp={env.is_grasp_success()} "
                #     f"place={env.is_place_success()}"
                # )
                target_ee = expert_info["target_ee"]
                pos_err = target_ee - ee_pos
                xy_err = (pos_err[0] ** 2 + pos_err[1] ** 2) ** 0.5
                z_err = abs(pos_err[2])

                print(
                    f"step={step:04d} "
                    f"stage={expert_info['stage']:20s} "
                    f"ee={ee_pos} "
                    f"target_ee={target_ee} "
                    f"xy_err={xy_err:.4f} "
                    f"z_err={z_err:.4f} "
                    f"cube={cube_pos} "
                    f"target={target_pos} "
                    f"ik={ctrl_info['ik_success']} "
                    f"ik_err={ctrl_info['ik_error']:.4f} "
                    f"grasp={env.is_grasp_success()} "
                    f"place={env.is_place_success()}"
                )
            viewer.sync()
            time.sleep(0.01)

            if expert.stage == PickPlaceStage.DONE:
                print("Expert reached DONE.")
                break

            step += 1

    print("=" * 80)
    print("Final cube_pos:", env.get_cube_pos())
    print("Final target_pos:", env.get_target_pos())
    print("grasp_success:", env.is_grasp_success())
    print("place_success:", env.is_place_success())
    print("=" * 80)

    env.close()


if __name__ == "__main__":
    main()
