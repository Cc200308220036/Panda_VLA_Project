import os
import sys
import cv2

# ==================== 路径修复：必须在 import envs/controllers/experts 之前 ====================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import argparse
import h5py
import numpy as np

from mujoco_env.envs.pick_place_env import PickPlaceEnv
from mujoco_env.controllers.ee_delta_controller import EEDeltaController


def make_controller(env):
    """
    必须和 collect_scripted_pick_place_hdf5.py / batch 测试成功版本保持一致。
    """
    controller = EEDeltaController(
        model=env.model,
        data=env.data,
        joint_names=env.joint_names,
        ee_body_name="hand",
        table_top_z=env.table_top_z,
        max_pos_delta=0.015,
        min_ee_z_above_table=0.035,
        workspace_low=(0.25, -0.35, 0.43),
        workspace_high=(0.90, 0.35, 1.00),
        open_gripper_ctrl=255.0,
        close_gripper_ctrl=0.0,
    )
    return controller


def load_episode(path):
    with h5py.File(path, "r") as f:
        actions = f["actions"][:].astype(np.float32)

        seed = int(f["metadata"].attrs["seed"])
        stored_success = bool(f["metadata"].attrs["success"])
        stored_valid_demo = bool(f["metadata"].attrs["valid_demo"])
        stored_num_steps = int(f["metadata"].attrs["num_steps"])

        initial_cube = f["metadata/initial_cube"][:]
        initial_target = f["metadata/initial_target"][:]
        final_cube = f["metadata/final_cube"][:]
        final_target = f["metadata/final_target"][:]
        final_place_error = f["metadata/final_place_error"][:]

    return {
        "actions": actions,
        "seed": seed,
        "stored_success": stored_success,
        "stored_valid_demo": stored_valid_demo,
        "stored_num_steps": stored_num_steps,
        "initial_cube": initial_cube,
        "initial_target": initial_target,
        "final_cube": final_cube,
        "final_target": final_target,
        "final_place_error": final_place_error,
    }


def replay_episode(
    episode_path,
    render=False,
    render_width=224,
    render_height=224,
    camera_name="top",
    n_substeps=20,
    max_steps=None,
    verbose=True,
):
    episode = load_episode(episode_path)

    env = PickPlaceEnv(
        render_width=render_width,
        render_height=render_height,
        camera_name=camera_name,
        seed=episode["seed"],
    )

    controller = make_controller(env)

    # 注意：PickPlaceEnv 当前 reset() 不接收 seed。
    # 你 env 初始化时已经传入 seed=episode["seed"]，内部 rng 已经确定。
    # 这里调用 reset() 会根据当前 rng 继续采样一次。
    #
    # 如果你 collect 时也是 env = PickPlaceEnv(seed=seed) 后又 env.reset()，
    # 那 replay 也必须保持同样逻辑，才能复现。
    env.reset()

    actions = episode["actions"]
    if max_steps is not None:
        actions = actions[:max_steps]

    max_cube_z = -1e9
    min_place_xy_dist = 1e9
    ever_grasp = False
    ever_place = False

    if verbose:
        print("=" * 100)
        print(f"Replay episode: {episode_path}")
        print(f"seed: {episode['seed']}")
        print(f"stored_success: {episode['stored_success']}")
        print(f"stored_valid_demo: {episode['stored_valid_demo']}")
        print(f"stored_num_steps: {episode['stored_num_steps']}")
        print(f"actions shape: {actions.shape}")
        print("-" * 100)
        print(f"stored initial_cube:       {episode['initial_cube']}")
        print(f"stored initial_target:     {episode['initial_target']}")
        print(f"replay initial_cube:       {env.get_cube_pos()}")
        print(f"replay initial_target:     {env.get_target_pos()}")
        print("=" * 100)

    for t, action in enumerate(actions):
        ctrl, ctrl_info = controller.compute_control(
            dx=action[0],
            dy=action[1],
            dz=action[2],
            droll=action[3],
            dpitch=action[4],
            dyaw=action[5],
            gripper=action[6],
        )

        env.step_sim(ctrl=ctrl, n_substeps=n_substeps)

        cube_pos = env.get_cube_pos()
        target_pos = env.get_target_pos()

        max_cube_z = max(max_cube_z, float(cube_pos[2]))

        place_xy_dist = float(np.linalg.norm(cube_pos[:2] - target_pos[:2]))
        min_place_xy_dist = min(min_place_xy_dist, place_xy_dist)

        if env.is_grasp_success():
            ever_grasp = True

        if env.is_place_success():
            ever_place = True

        # if render:
        #     try:
        #         env.render_human()
        #     except Exception:
        #         pass

        if render:
            rgb = env.render()
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

            cv2.putText(
                bgr,
                f"t={t:04d} | grasp={env.is_grasp_success()} | place={env.is_place_success()}",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2,
            )

            cv2.imshow("HDF5 Replay", bgr)

            key = cv2.waitKey(10)
            if key == ord("q"):
                break

        if verbose and (t % 100 == 0 or t == len(actions) - 1):
            print(
                f"[t={t:04d}] "
                f"cube={cube_pos} "
                f"target={target_pos} "
                f"xy_dist={place_xy_dist:.4f} "
                f"grasp={env.is_grasp_success()} "
                f"place={env.is_place_success()}"
            )

    final_cube = env.get_cube_pos()
    final_target = env.get_target_pos()
    final_place_error = final_cube[:2] - final_target[:2]
    final_xy_dist = float(np.linalg.norm(final_place_error))
    final_cube_lift = float(max_cube_z - env.cube_z)

    replay_place_success = env.is_place_success()
    replay_valid_demo = bool(
        ever_grasp
        and replay_place_success
        and final_cube_lift > 0.03
    )

    if verbose:
        print("-" * 100)
        print(f"stored final_cube:         {episode['final_cube']}")
        print(f"stored final_target:       {episode['final_target']}")
        print(f"stored final_place_error:  {episode['final_place_error']}")
        print("-" * 100)
        print(f"replay final_cube:         {final_cube}")
        print(f"replay final_target:       {final_target}")
        print(f"replay final_place_error:  {final_place_error}")
        print(f"replay final_xy_dist:      {final_xy_dist:.6f}")
        print(f"max_cube_z:                {max_cube_z:.6f}")
        print(f"final_cube_lift:           {final_cube_lift:.6f}")
        print(f"min_place_xy_dist:         {min_place_xy_dist:.6f}")
        print(f"ever_grasp:                {ever_grasp}")
        print(f"ever_place:                {ever_place}")
        print(f"replay_place_success:      {replay_place_success}")
        print(f"replay_valid_demo:         {replay_valid_demo}")
        print("=" * 100)

    if render:
        cv2.destroyAllWindows()


    env.close()

    return {
        "episode_path": episode_path,
        "seed": episode["seed"],
        "stored_success": episode["stored_success"],
        "stored_valid_demo": episode["stored_valid_demo"],
        "replay_place_success": bool(replay_place_success),
        "replay_valid_demo": bool(replay_valid_demo),
        "ever_grasp": bool(ever_grasp),
        "ever_place": bool(ever_place),
        "final_xy_dist": float(final_xy_dist),
        "final_cube_lift": float(final_cube_lift),
        "min_place_xy_dist": float(min_place_xy_dist),
        "replay_final_place_error": final_place_error.astype(np.float32),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", type=str, required=True)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--max_steps", type=int, default=None)
    parser.add_argument("--camera_name", type=str, default="top")
    parser.add_argument("--render_width", type=int, default=224)
    parser.add_argument("--render_height", type=int, default=224)
    parser.add_argument("--n_substeps", type=int, default=20)
    args = parser.parse_args()

    result = replay_episode(
        episode_path=args.episode,
        render=args.render,
        render_width=args.render_width,
        render_height=args.render_height,
        camera_name=args.camera_name,
        n_substeps=args.n_substeps,
        max_steps=args.max_steps,
        verbose=True,
    )

    if result["replay_valid_demo"]:
        print("[OK] Replay succeeded.")
    else:
        print("[WARNING] Replay failed.")


if __name__ == "__main__":
    main()
