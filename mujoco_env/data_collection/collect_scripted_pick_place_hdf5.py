import os
import sys
import json
import argparse
import h5py
import numpy as np
from tqdm import tqdm

import mujoco

# ==================== 路径修复：必须放在 import envs/controllers/experts 之前 ====================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ==================== 标准库 / 第三方库 ====================

from mujoco_env.envs.pick_place_env import PickPlaceEnv
from mujoco_env.controllers.ee_delta_controller import EEDeltaController
from mujoco_env.experts.scripted_pick_place import ScriptedPickPlaceExpert, PickPlaceStage

"""
用当前成功链路采集 HDF5 demo
"""

def make_controller(env):
    """
    必须和当前 batch 测试成功版本保持一致。
    不要随意改这里的参数。
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


def make_expert(env):
    """
    必须和当前 batch 测试成功版本保持一致。
    当前 place_xy_offset 是已经验证过的成功配置。
    """
    expert = ScriptedPickPlaceExpert(
        env=env,
        max_delta=0.010,
        reach_tol=0.018,
        z_reach_tol=0.015,
        pregrasp_height=0.20,
        grasp_height=0.105,
        lift_height=0.25,
        place_height=0.22,
        place_down_height=0.115,
        retreat_height=0.25,
        close_steps=120,
        open_steps=60,
        grasp_xy_offset=(-0.01, 0.006),
        place_xy_offset=(-0.050, -0.005),
    )
    return expert


def get_image_from_obs(obs):
    """
    兼容不同 obs key。
    你的 PandaBaseEnv 通常返回 obs["image"]。
    """
    if "image" in obs:
        return obs["image"]

    if "images" in obs and "top" in obs["images"]:
        return obs["images"]["top"]

    raise KeyError("Cannot find image in obs. Expected obs['image'] or obs['images']['top'].")


def get_robot_state_from_obs_or_env(obs, env):
    """
    优先使用 obs['robot_state']。
    如果没有，就从 env.get_robot_state() 读取。
    """
    if "robot_state" in obs:
        return obs["robot_state"].astype(np.float32)

    if hasattr(env, "get_robot_state"):
        return env.get_robot_state().astype(np.float32)

    raise KeyError("Cannot find robot_state in obs and env has no get_robot_state().")


def collect_one_episode(
    seed,
    render=False,
    max_steps=1800,
    render_width=224,
    render_height=224,
    camera_name="top",
):
    """
    采集单条 episode。

    关键执行链路：
        expert action -> controller ctrl -> env.step_sim(ctrl)

    注意：
        保存的是 step 之前的 observation 和当前 action。
        然后再执行 env.step_sim(ctrl)。
        这是模仿学习常用对齐方式：
            obs_t -> action_t -> obs_{t+1}
    """
    env = PickPlaceEnv(
        render_width=render_width,
        render_height=render_height,
        camera_name=camera_name,
        seed=seed,
    )

    controller = make_controller(env)
    expert = make_expert(env)

    obs = env.reset()
    expert.reset()

    images = []
    robot_states = []
    joint_pos_list = []
    joint_vel_list = []
    gripper_qpos_list = []
    ee_pos_list = []
    ee_quat_list = []

    actions = []
    ctrls = []

    cube_pos_list = []
    target_pos_list = []
    stage_list = []

    rewards = []
    success_list = []
    grasp_success_list = []
    place_success_list = []

    ever_grasp_success = False
    ever_place_success = False

    max_cube_z = -1e9
    min_place_xy_dist = 1e9

    initial_cube = env.get_cube_pos().copy()
    initial_target = env.get_target_pos().copy()

    final_stage = None

    for step in range(max_steps):
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

        # -----------------------------
        # 保存 step 前 obs 和 action
        # -----------------------------
        image = get_image_from_obs(obs)
        robot_state = get_robot_state_from_obs_or_env(obs, env)
        ee_pos, ee_quat = env.get_ee_pose()

        images.append(image.astype(np.uint8))
        robot_states.append(robot_state.astype(np.float32))
        joint_pos_list.append(env.get_joint_pos().astype(np.float32))
        joint_vel_list.append(env.get_joint_vel().astype(np.float32))
        gripper_qpos_list.append(env.get_gripper_qpos().astype(np.float32))
        ee_pos_list.append(ee_pos.astype(np.float32))
        ee_quat_list.append(ee_quat.astype(np.float32))

        actions.append(action.astype(np.float32))
        ctrls.append(ctrl.astype(np.float32))

        cube_pos = env.get_cube_pos()
        target_pos = env.get_target_pos()

        cube_pos_list.append(cube_pos.astype(np.float32))
        target_pos_list.append(target_pos.astype(np.float32))
        stage_list.append(str(expert_info["stage"]))

        # -----------------------------
        # 执行控制：沿用成功 batch 链路
        # -----------------------------
        env.step_sim(ctrl=ctrl, n_substeps=20)

        obs = env.get_obs()

        reward = env.compute_reward()
        grasp_success = env.is_grasp_success()
        place_success = env.is_place_success()

        rewards.append(float(reward))
        grasp_success_list.append(bool(grasp_success))
        place_success_list.append(bool(place_success))

        cube_pos_after = env.get_cube_pos()
        target_pos_after = env.get_target_pos()

        cube_z = float(cube_pos_after[2])
        max_cube_z = max(max_cube_z, cube_z)

        place_xy_dist = float(np.linalg.norm(cube_pos_after[:2] - target_pos_after[:2]))
        min_place_xy_dist = min(min_place_xy_dist, place_xy_dist)

        if grasp_success:
            ever_grasp_success = True

        if place_success:
            ever_place_success = True

        final_stage = expert_info["stage"]

        success_list.append(bool(place_success))

        if render:
            try:
                env.render_human()
            except Exception:
                pass

        if expert.stage == PickPlaceStage.DONE:
            break

    final_cube = env.get_cube_pos()
    final_target = env.get_target_pos()

    final_xy_dist = float(np.linalg.norm(final_cube[:2] - final_target[:2]))
    final_cube_lift = float(max_cube_z - env.cube_z)
    final_place_error = final_cube[:2] - final_target[:2]

    final_place_success = env.is_place_success()
    expert_done = expert.stage == PickPlaceStage.DONE

    valid_demo = (
        expert_done
        and ever_grasp_success
        and final_place_success
        and final_cube_lift > 0.03
    )

    if valid_demo:
        failure_reason = "none"
    elif not ever_grasp_success:
        failure_reason = "grasp_failed"
    elif final_cube_lift <= 0.03:
        failure_reason = "insufficient_lift"
    elif not final_place_success:
        failure_reason = "place_failed"
    elif not expert_done:
        failure_reason = "timeout_or_not_done"
    else:
        failure_reason = "unknown"

    episode = {
        "seed": int(seed),
        "valid_demo": bool(valid_demo),
        "success": bool(valid_demo),
        "final_place_success": bool(final_place_success),
        "expert_done": bool(expert_done),
        "failure_reason": failure_reason,

        "num_steps": int(len(actions)),
        "initial_cube": initial_cube.astype(np.float32),
        "initial_target": initial_target.astype(np.float32),
        "final_cube": final_cube.astype(np.float32),
        "final_target": final_target.astype(np.float32),
        "final_place_error": final_place_error.astype(np.float32),
        "final_xy_dist": float(final_xy_dist),
        "max_cube_z": float(max_cube_z),
        "final_cube_lift": float(final_cube_lift),
        "min_place_xy_dist": float(min_place_xy_dist),
        "ever_grasp": bool(ever_grasp_success),
        "ever_place": bool(ever_place_success),
        "final_stage": str(final_stage),

        "images": np.stack(images, axis=0).astype(np.uint8),
        "robot_state": np.stack(robot_states, axis=0).astype(np.float32),
        "joint_pos": np.stack(joint_pos_list, axis=0).astype(np.float32),
        "joint_vel": np.stack(joint_vel_list, axis=0).astype(np.float32),
        "gripper_qpos": np.stack(gripper_qpos_list, axis=0).astype(np.float32),
        "ee_pos": np.stack(ee_pos_list, axis=0).astype(np.float32),
        "ee_quat": np.stack(ee_quat_list, axis=0).astype(np.float32),

        "actions": np.stack(actions, axis=0).astype(np.float32),
        "ctrls": np.stack(ctrls, axis=0).astype(np.float32),

        "cube_pos": np.stack(cube_pos_list, axis=0).astype(np.float32),
        "target_pos": np.stack(target_pos_list, axis=0).astype(np.float32),
        "stage": stage_list,

        "rewards": np.asarray(rewards, dtype=np.float32),
        "success_list": np.asarray(success_list, dtype=np.bool_),
        "grasp_success_list": np.asarray(grasp_success_list, dtype=np.bool_),
        "place_success_list": np.asarray(place_success_list, dtype=np.bool_),
    }

    env.close()

    return episode


def save_episode_hdf5(path, episode):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with h5py.File(path, "w") as f:
        # -----------------------------
        # observations
        # -----------------------------
        obs_group = f.create_group("observations")
        image_group = obs_group.create_group("images")

        image_group.create_dataset(
            "top",
            data=episode["images"],
            compression="gzip",
            compression_opts=4,
        )

        obs_group.create_dataset("robot_state", data=episode["robot_state"])
        obs_group.create_dataset("joint_pos", data=episode["joint_pos"])
        obs_group.create_dataset("joint_vel", data=episode["joint_vel"])
        obs_group.create_dataset("gripper_qpos", data=episode["gripper_qpos"])
        obs_group.create_dataset("ee_pos", data=episode["ee_pos"])
        obs_group.create_dataset("ee_quat", data=episode["ee_quat"])

        # -----------------------------
        # actions for policy training
        # -----------------------------
        f.create_dataset("actions", data=episode["actions"])

        # -----------------------------
        # ctrl only for replay/debug
        # -----------------------------
        f.create_dataset("ctrls", data=episode["ctrls"])

        # -----------------------------
        # privileged info, not for policy input
        # -----------------------------
        priv = f.create_group("privileged")
        priv.create_dataset("cube_pos", data=episode["cube_pos"])
        priv.create_dataset("target_pos", data=episode["target_pos"])

        stage_bytes = np.asarray(
            [s.encode("utf-8") for s in episode["stage"]],
            dtype="S32",
        )
        priv.create_dataset("stage", data=stage_bytes)

        # -----------------------------
        # metrics
        # -----------------------------
        metrics = f.create_group("metrics")
        metrics.create_dataset("rewards", data=episode["rewards"])
        metrics.create_dataset("success", data=episode["success_list"])
        metrics.create_dataset("grasp_success", data=episode["grasp_success_list"])
        metrics.create_dataset("place_success", data=episode["place_success_list"])

        # -----------------------------
        # metadata attrs
        # -----------------------------
        meta = f.create_group("metadata")

        meta.attrs["seed"] = int(episode["seed"])
        meta.attrs["valid_demo"] = bool(episode["valid_demo"])
        meta.attrs["success"] = bool(episode["success"])
        meta.attrs["final_place_success"] = bool(episode["final_place_success"])
        meta.attrs["expert_done"] = bool(episode["expert_done"])
        meta.attrs["failure_reason"] = str(episode["failure_reason"])

        meta.attrs["num_steps"] = int(episode["num_steps"])
        meta.attrs["final_xy_dist"] = float(episode["final_xy_dist"])
        meta.attrs["max_cube_z"] = float(episode["max_cube_z"])
        meta.attrs["final_cube_lift"] = float(episode["final_cube_lift"])
        meta.attrs["min_place_xy_dist"] = float(episode["min_place_xy_dist"])
        meta.attrs["ever_grasp"] = bool(episode["ever_grasp"])
        meta.attrs["ever_place"] = bool(episode["ever_place"])
        meta.attrs["final_stage"] = str(episode["final_stage"])

        meta.create_dataset("initial_cube", data=episode["initial_cube"])
        meta.create_dataset("initial_target", data=episode["initial_target"])
        meta.create_dataset("final_cube", data=episode["final_cube"])
        meta.create_dataset("final_target", data=episode["final_target"])
        meta.create_dataset("final_place_error", data=episode["final_place_error"])


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--output_dir", type=str, default="data/raw/pick_place_scripted_debug_10")
    parser.add_argument("--num_episodes", type=int, default=10)
    parser.add_argument("--start_seed", type=int, default=0)
    parser.add_argument("--max_seed_trials", type=int, default=100000)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--keep_failed", action="store_true")

    parser.add_argument("--render_width", type=int, default=224)
    parser.add_argument("--render_height", type=int, default=224)
    parser.add_argument("--camera_name", type=str, default="top")
    parser.add_argument("--max_steps", type=int, default=1800)

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    saved_count = 0
    tried_count = 0
    failed_seeds = []
    saved_episodes = []

    seed = args.start_seed

    pbar = tqdm(total=args.num_episodes)

    while saved_count < args.num_episodes:
        if tried_count >= args.max_seed_trials:
            raise RuntimeError(
                f"Reached max_seed_trials={args.max_seed_trials}, "
                f"but only saved {saved_count}/{args.num_episodes} episodes."
            )

        episode = collect_one_episode(
            seed=seed,
            render=args.render,
            max_steps=args.max_steps,
            render_width=args.render_width,
            render_height=args.render_height,
            camera_name=args.camera_name,
        )

        tried_count += 1

        should_save = episode["valid_demo"] or args.keep_failed

        if should_save:
            ep_path = os.path.join(
                args.output_dir,
                f"episode_{saved_count:06d}.hdf5",
            )

            save_episode_hdf5(ep_path, episode)

            saved_episodes.append(
                {
                    "episode_id": int(saved_count),
                    "path": os.path.abspath(ep_path),
                    "seed": int(seed),
                    "valid_demo": bool(episode["valid_demo"]),
                    "success": bool(episode["success"]),
                    "num_steps": int(episode["num_steps"]),
                    "failure_reason": str(episode["failure_reason"]),
                    "final_place_error": episode["final_place_error"].tolist(),
                    "final_xy_dist": float(episode["final_xy_dist"]),
                    "final_cube_lift": float(episode["final_cube_lift"]),
                }
            )

            print(
                f"[SAVE] ep={saved_count:06d} "
                f"seed={seed:06d} "
                f"valid={episode['valid_demo']} "
                f"steps={episode['num_steps']} "
                f"err={episode['final_place_error']} "
                f"reason={episode['failure_reason']}"
            )

            saved_count += 1
            pbar.update(1)

        else:
            failed_seeds.append(seed)
            print(
                f"[DROP] seed={seed:06d} "
                f"valid={episode['valid_demo']} "
                f"reason={episode['failure_reason']} "
                f"err={episode['final_place_error']}"
            )

        seed += 1

    pbar.close()

    metadata = {
        "dataset_name": os.path.basename(args.output_dir),
        "output_dir": os.path.abspath(args.output_dir),
        "num_episodes": int(saved_count),
        "start_seed": int(args.start_seed),
        "next_seed": int(seed),
        "tried_count": int(tried_count),
        "failed_seeds": failed_seeds,

        "image_key": "observations/images/top",
        "state_key": "observations/robot_state",
        "action_key": "actions",
        "ctrl_key": "ctrls",

        "action_dim": 7,
        "control_type": "ee_delta_action_saved__controller_recomputed_or_ctrl_replayed",
        "camera_name": args.camera_name,
        "render_width": args.render_width,
        "render_height": args.render_height,

        "controller": {
            "ee_body_name": "hand",
            "max_pos_delta": 0.015,
            "min_ee_z_above_table": 0.035,
            "workspace_low": [0.25, -0.35, 0.43],
            "workspace_high": [0.90, 0.35, 1.00],
            "open_gripper_ctrl": 255.0,
            "close_gripper_ctrl": 0.0,
            "n_substeps": 20,
        },

        "expert": {
            "max_delta": 0.010,
            "reach_tol": 0.018,
            "z_reach_tol": 0.015,
            "pregrasp_height": 0.20,
            "grasp_height": 0.105,
            "lift_height": 0.25,
            "place_height": 0.22,
            "place_down_height": 0.115,
            "retreat_height": 0.25,
            "close_steps": 120,
            "open_steps": 60,
            "grasp_xy_offset": [-0.01, 0.006],
            "place_xy_offset": [-0.050, -0.005],
        },

        "episodes": saved_episodes,
    }

    metadata_path = os.path.join(args.output_dir, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("=" * 80)
    print(f"Saved episodes: {saved_count}")
    print(f"Tried seeds: {tried_count}")
    print(f"Output dir: {args.output_dir}")
    print(f"Metadata: {metadata_path}")
    print(f"Failed seeds: {failed_seeds}")
    print("=" * 80)


if __name__ == "__main__":
    main()
