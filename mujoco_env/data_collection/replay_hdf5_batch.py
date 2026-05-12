import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import glob
import argparse
import h5py
import numpy as np
from tqdm import tqdm

from mujoco_env.envs.pick_place_env import PickPlaceEnv
from mujoco_env.controllers.ee_delta_controller import EEDeltaController


def make_controller(env):
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

    return {
        "actions": actions,
        "seed": seed,
        "stored_success": stored_success,
        "stored_valid_demo": stored_valid_demo,
        "stored_num_steps": stored_num_steps,
    }


def replay_one_episode(
    episode_path,
    render_width=224,
    render_height=224,
    camera_name="top",
    n_substeps=20,
):
    episode = load_episode(episode_path)

    env = PickPlaceEnv(
        render_width=render_width,
        render_height=render_height,
        camera_name=camera_name,
        seed=episode["seed"],
    )

    controller = make_controller(env)

    # 必须和 collect 时保持一致：
    # collect 中 env 初始化后又调用了 env.reset()
    env.reset()

    actions = episode["actions"]

    max_cube_z = -1e9
    min_place_xy_dist = 1e9
    ever_grasp = False
    ever_place = False

    for action in actions:
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
        "final_place_error": final_place_error.astype(np.float32),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_dir", type=str, required=True)
    parser.add_argument("--num_episodes", type=int, default=None)
    parser.add_argument("--camera_name", type=str, default="top")
    parser.add_argument("--render_width", type=int, default=224)
    parser.add_argument("--render_height", type=int, default=224)
    parser.add_argument("--n_substeps", type=int, default=20)
    args = parser.parse_args()

    episode_paths = sorted(
        glob.glob(os.path.join(args.dataset_dir, "episode_*.hdf5"))
    )

    if args.num_episodes is not None:
        episode_paths = episode_paths[: args.num_episodes]

    if len(episode_paths) == 0:
        raise RuntimeError(f"No episode_*.hdf5 found in {args.dataset_dir}")

    results = []
    failed = []

    for i, path in enumerate(tqdm(episode_paths)):
        result = replay_one_episode(
            episode_path=path,
            render_width=args.render_width,
            render_height=args.render_height,
            camera_name=args.camera_name,
            n_substeps=args.n_substeps,
        )

        results.append(result)

        if not result["replay_valid_demo"]:
            failed.append(
                {
                    "index": i,
                    "path": path,
                    "seed": result["seed"],
                    "final_xy_dist": result["final_xy_dist"],
                    "final_cube_lift": result["final_cube_lift"],
                    "ever_grasp": result["ever_grasp"],
                    "ever_place": result["ever_place"],
                    "final_place_error": result["final_place_error"].tolist(),
                }
            )

        print(
            f"ep={i:06d} "
            f"seed={result['seed']:06d} "
            f"replay_valid={result['replay_valid_demo']} "
            f"xy={result['final_xy_dist']:.4f} "
            f"lift={result['final_cube_lift']:.4f} "
            f"err={result['final_place_error']}"
        )

    replay_success_rate = np.mean([r["replay_valid_demo"] for r in results])
    place_success_rate = np.mean([r["replay_place_success"] for r in results])
    grasp_rate = np.mean([r["ever_grasp"] for r in results])
    ever_place_rate = np.mean([r["ever_place"] for r in results])

    final_xy_dists = np.asarray([r["final_xy_dist"] for r in results], dtype=np.float32)
    final_lifts = np.asarray([r["final_cube_lift"] for r in results], dtype=np.float32)
    final_errs = np.stack([r["final_place_error"] for r in results], axis=0)

    print("=" * 100)
    print(f"dataset_dir: {args.dataset_dir}")
    print(f"num_checked: {len(results)}")
    print(f"grasp_rate: {grasp_rate:.3f}")
    print(f"ever_place_rate: {ever_place_rate:.3f}")
    print(f"place_success_rate: {place_success_rate:.3f}")
    print(f"replay_success_rate: {replay_success_rate:.3f}")
    print(f"failed_count: {len(failed)}")
    print(f"failed: {failed}")
    print("-" * 100)
    print(f"final_xy_dist mean: {final_xy_dists.mean():.6f}")
    print(f"final_xy_dist max:  {final_xy_dists.max():.6f}")
    print(f"final_lift mean:    {final_lifts.mean():.6f}")
    print(f"final_lift min:     {final_lifts.min():.6f}")
    print(f"final_place_error mean:   {final_errs.mean(axis=0)}")
    print(f"final_place_error median: {np.median(final_errs, axis=0)}")
    print(f"final_place_error std:    {final_errs.std(axis=0)}")
    print("=" * 100)

    if replay_success_rate >= 0.95:
        print("[OK] Batch replay passed.")
    else:
        print("[WARNING] Batch replay success rate is low.")


if __name__ == "__main__":
    main()
