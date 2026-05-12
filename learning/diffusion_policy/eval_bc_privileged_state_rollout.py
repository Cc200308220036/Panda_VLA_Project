"""
实现目标：
    部署并评估 privileged-state Behavior Cloning 模型在 MuJoCo Panda pick-place 环境中的闭环 rollout 表现。

    本脚本用于验证：
        1. bc_privileged_state_v2/best.pt 是否能正确加载；
        2. privileged_state_stats.json 是否和 checkpoint 匹配；
        3. rollout 时是否使用 corrected privileged state：
               robot_state + cube_pos + target_pos + relative features
        4. 7D action 是否仍然走稳定链路：
               policy action
               -> EEDeltaController.compute_control(...)
               -> MuJoCo ctrl
               -> env.step_sim(...)
        5. 模型是否能在 fixed_scene / random_scene 中完成抓取放置。

输入：
    --checkpoint:
        train_bc_privileged_state.py 训练得到的 best.pt。
        推荐：
            experiments/bc_privileged_state_v2/best.pt

    --stats_path:
        privileged-state 归一化统计量。
        推荐：
            experiments/bc_privileged_state_v2/privileged_state_stats.json

    --output_dir:
        评估结果输出目录。

    --num_episodes:
        rollout episode 数量。

    --fixed_scene:
        是否使用固定 cube/target 位置。

输出：
    output_dir/eval_results.csv:
        每个 episode 的 success / grasp_success / place_success / xy_dist / steps 等指标。

    output_dir/summary.json:
        汇总 success_rate / grasp_success_rate / place_success_rate 等指标。

    output_dir/videos/*.mp4:
        如果启用 --save_video，则保存 rollout 视频。

重要说明：
    这个脚本不要把 7D policy action 直接传给 env.step(action)。
    当前你的 PickPlaceEnv.step() 是底层 MuJoCo ctrl step，不是 7D ee_delta action step。

    正确部署链路必须是：
        action = [dx, dy, dz, droll, dpitch, dyaw, gripper]
            ↓
        EEDeltaController.compute_control(...)
            ↓
        ctrl
            ↓
        env.step_sim(ctrl=ctrl, n_substeps=20)
"""

import argparse
import csv
import json
import os
import shutil
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch

try:
    import mujoco
except ImportError:
    mujoco = None

from learning.diffusion_policy.model import StateBCPolicy
from learning.diffusion_policy.privileged_state_utils import build_privileged_state_from_obs

try:
    from mujoco_env.controllers.ee_delta_controller import EEDeltaController
except ImportError:
    try:
        from controllers.ee_delta_controller import EEDeltaController
    except ImportError:
        EEDeltaController = None


def try_import_pick_place_env():
    try:
        from mujoco_env.envs.pick_place_env import PickPlaceEnv
        return PickPlaceEnv
    except ImportError:
        try:
            from envs.pick_place_env import PickPlaceEnv
            return PickPlaceEnv
        except ImportError as exc:
            raise ImportError(
                "Cannot import PickPlaceEnv. Please run this script from project root, "
                "or make sure mujoco_env is a Python package with __init__.py files."
            ) from exc


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_std(std: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    std = np.asarray(std, dtype=np.float32)
    return np.where(std < eps, eps, std).astype(np.float32)


def normalize_state(
    state_window: np.ndarray,
    state_mean: np.ndarray,
    state_std: np.ndarray,
) -> np.ndarray:
    return (state_window - state_mean) / state_std


def unnormalize_action(
    action_norm: np.ndarray,
    action_mean: np.ndarray,
    action_std: np.ndarray,
) -> np.ndarray:
    return action_norm * action_std + action_mean


def ensure_obs_has_privileged(env, obs: Dict[str, Any]) -> Dict[str, Any]:
    """
    确保 obs 至少包含：
        robot_state 或 joint_pos/joint_vel/gripper_qpos/ee_pos/ee_quat
        cube_pos
        target_pos
    """
    if isinstance(obs, tuple):
        obs = obs[0]

    if not isinstance(obs, dict):
        raise TypeError(f"Expected obs to be dict, got {type(obs)}")

    obs = dict(obs)

    if "robot_state" not in obs and hasattr(env, "get_robot_state"):
        obs["robot_state"] = np.asarray(env.get_robot_state(), dtype=np.float32)

    if "cube_pos" not in obs and hasattr(env, "get_cube_pos"):
        obs["cube_pos"] = np.asarray(env.get_cube_pos(), dtype=np.float32)

    if "target_pos" not in obs and hasattr(env, "get_target_pos"):
        obs["target_pos"] = np.asarray(env.get_target_pos(), dtype=np.float32)

    return obs


def build_env(args, seed: int):
    PickPlaceEnv = try_import_pick_place_env()

    env_kwargs = {
        "render_width": args.render_width,
        "render_height": args.render_height,
        "camera_name": args.camera_name,
        "seed": seed,
    }

    if args.xml_path:
        env_kwargs["xml_path"] = args.xml_path

    env = PickPlaceEnv(**env_kwargs)
    return env


def build_controller(env):
    """
    必须和采集 / replay 成功链路保持一致。

    如果你之前 collect_scripted_pick_place_hdf5.py 或 replay_hdf5_batch.py
    里的 EEDeltaController 参数不同，以之前成功脚本为准。
    """
    if EEDeltaController is None:
        raise ImportError(
            "Cannot import EEDeltaController. Please check "
            "mujoco_env/controllers/ee_delta_controller.py"
        )

    controller = EEDeltaController(
        model=env.model,
        data=env.data,
        joint_names=env.joint_names,
        ee_body_name="hand",
        table_top_z=getattr(env, "table_top_z", 0.40),
        max_pos_delta=args_global_max_pos_delta(),
        min_ee_z_above_table=0.035,
        workspace_low=(0.25, -0.35, 0.43),
        workspace_high=(0.90, 0.35, 1.00),
        open_gripper_ctrl=255.0,
        close_gripper_ctrl=0.0,
    )

    return controller


def args_global_max_pos_delta() -> float:
    """
    单独写成函数，避免 build_controller 依赖 argparse 全局变量。
    这里保持和之前成功 controller 链路一致。
    """
    return 0.015


def reset_env(env, seed: int, args) -> Dict[str, Any]:
    """
    支持随机场景和 fixed_scene。
    """
    if hasattr(env, "rng"):
        try:
            env.rng = np.random.default_rng(seed)
        except Exception:
            pass

    try:
        obs = env.reset(seed=seed)
    except TypeError:
        obs = env.reset()

    if isinstance(obs, tuple):
        obs = obs[0]

    if args.fixed_scene:
        cube_xy = np.array(
            [args.fixed_cube_x, args.fixed_cube_y],
            dtype=np.float64,
        )
        target_xy = np.array(
            [args.fixed_target_x, args.fixed_target_y],
            dtype=np.float64,
        )

        if not hasattr(env, "set_cube_pose"):
            raise AttributeError(
                "fixed_scene requires env.set_cube_pose(xy), "
                "but current env does not have it."
            )

        if not hasattr(env, "set_target_pose"):
            raise AttributeError(
                "fixed_scene requires env.set_target_pose(xy), "
                "but current env does not have it."
            )

        env.set_cube_pose(cube_xy)
        env.set_target_pose(target_xy)

        if mujoco is not None and hasattr(env, "model") and hasattr(env, "data"):
            mujoco.mj_forward(env.model, env.data)

        obs = env.get_obs()

    obs = ensure_obs_has_privileged(env, obs)
    return obs


def maybe_render_human(env):
    if hasattr(env, "render_human"):
        env.render_human()


def extract_frame(obs: Dict[str, Any], env) -> Optional[np.ndarray]:
    if isinstance(obs, dict) and "image" in obs:
        return np.asarray(obs["image"], dtype=np.uint8)

    if hasattr(env, "render"):
        frame = env.render()
        if frame is not None:
            return np.asarray(frame, dtype=np.uint8)

    return None


def save_video_mp4(frames: List[np.ndarray], path: Path, fps: int):
    if len(frames) == 0:
        return

    try:
        import cv2
    except ImportError:
        print("[WARN] cv2 is not installed, skip video saving.")
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    first = np.asarray(frames[0], dtype=np.uint8)
    height, width = first.shape[:2]

    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    for frame in frames:
        frame = np.asarray(frame, dtype=np.uint8)

        if frame.shape[0] != height or frame.shape[1] != width:
            frame = cv2.resize(frame, (width, height))

        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        else:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        writer.write(frame)

    writer.release()


def load_model_and_stats(args, device: torch.device):
    checkpoint = torch.load(args.checkpoint, map_location=device)
    config = checkpoint.get("config", {})

    stats_path = args.stats_path
    if not stats_path:
        stats_path = config.get("stats_path", "")

    if not stats_path:
        raise ValueError(
            "stats_path is empty. Please pass --stats_path, "
            "or ensure checkpoint config contains stats_path."
        )

    if not os.path.exists(stats_path):
        raise FileNotFoundError(f"stats_path not found: {stats_path}")

    stats = load_json(stats_path)

    state_mean = np.asarray(stats["state_mean"], dtype=np.float32)
    state_std = safe_std(np.asarray(stats["state_std"], dtype=np.float32))
    action_mean = np.asarray(stats["action_mean"], dtype=np.float32)
    action_std = safe_std(np.asarray(stats["action_std"], dtype=np.float32))

    state_dim = int(config.get("state_dim", stats.get("state_dim", len(state_mean))))
    action_dim = int(config.get("action_dim", stats.get("action_dim", len(action_mean))))

    obs_horizon = int(config.get("obs_horizon", args.obs_horizon))
    pred_horizon = int(config.get("pred_horizon", args.pred_horizon))
    hidden_dim = int(config.get("hidden_dim", args.hidden_dim))
    dropout = float(config.get("dropout", args.dropout))
    state_mode = str(config.get("state_mode", stats.get("state_mode", "relative")))

    if state_dim != len(state_mean):
        raise ValueError(
            f"state_dim mismatch: checkpoint/config state_dim={state_dim}, "
            f"but len(state_mean)={len(state_mean)}"
        )

    if action_dim != len(action_mean):
        raise ValueError(
            f"action_dim mismatch: checkpoint/config action_dim={action_dim}, "
            f"but len(action_mean)={len(action_mean)}"
        )

    if state_dim != 38 and state_mode == "relative":
        raise ValueError(
            f"Expected privileged relative state_dim=38, got {state_dim}. "
            "You may be loading a state-only checkpoint or wrong stats file."
        )

    model = StateBCPolicy(
        state_dim=state_dim,
        action_dim=action_dim,
        obs_horizon=obs_horizon,
        pred_horizon=pred_horizon,
        hidden_dim=hidden_dim,
        dropout=dropout,
    ).to(device)

    if "model_state_dict" not in checkpoint:
        raise KeyError(
            "checkpoint does not contain model_state_dict. "
            "Please check whether this is a StateBCPolicy checkpoint."
        )

    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    runtime = {
        "checkpoint": checkpoint,
        "config": config,
        "stats_path": stats_path,
        "state_mean": state_mean,
        "state_std": state_std,
        "action_mean": action_mean,
        "action_std": action_std,
        "state_dim": state_dim,
        "action_dim": action_dim,
        "obs_horizon": obs_horizon,
        "pred_horizon": pred_horizon,
        "hidden_dim": hidden_dim,
        "dropout": dropout,
        "state_mode": state_mode,
    }

    return model, runtime


@torch.no_grad()
def predict_action_sequence(
    model: StateBCPolicy,
    state_history: deque,
    runtime: Dict[str, Any],
    device: torch.device,
    action_clip_abs: float,
) -> np.ndarray:
    state_window = np.stack(list(state_history), axis=0).astype(np.float32)

    expected_shape = (runtime["obs_horizon"], runtime["state_dim"])
    if state_window.shape != expected_shape:
        raise ValueError(
            f"state_window shape mismatch: got {state_window.shape}, "
            f"expected {expected_shape}"
        )

    state_window_norm = normalize_state(
        state_window=state_window,
        state_mean=runtime["state_mean"],
        state_std=runtime["state_std"],
    )

    state_tensor = torch.from_numpy(state_window_norm).float().unsqueeze(0).to(device)

    action_norm_seq = model(state_tensor)
    action_norm_seq = action_norm_seq.squeeze(0).detach().cpu().numpy()

    action_seq = unnormalize_action(
        action_norm=action_norm_seq,
        action_mean=runtime["action_mean"],
        action_std=runtime["action_std"],
    )

    if action_clip_abs is not None and action_clip_abs > 0:
        action_seq = np.clip(
            action_seq,
            -float(action_clip_abs),
            float(action_clip_abs),
        )

    return action_seq.astype(np.float32)


def compute_place_success(env, strict: Optional[bool] = None) -> bool:
    if not hasattr(env, "is_place_success"):
        return False

    fn = env.is_place_success

    if strict is None:
        try:
            return bool(fn())
        except TypeError:
            try:
                return bool(fn(strict=True))
            except TypeError:
                return False

    try:
        return bool(fn(strict=strict))
    except TypeError:
        try:
            return bool(fn())
        except TypeError:
            return False


def compute_eval_info(env, ctrl_info: Dict[str, Any]) -> Dict[str, Any]:
    if hasattr(env, "is_grasp_success"):
        grasp_success = bool(env.is_grasp_success())
    else:
        grasp_success = False

    place_success = compute_place_success(env, strict=True)
    place_success_loose = compute_place_success(env, strict=False)

    cube_pos = None
    target_pos = None

    if hasattr(env, "get_cube_pos"):
        cube_pos = np.asarray(env.get_cube_pos(), dtype=np.float32)

    if hasattr(env, "get_target_pos"):
        target_pos = np.asarray(env.get_target_pos(), dtype=np.float32)

    if hasattr(env, "get_place_xy_dist"):
        try:
            place_xy_dist = float(env.get_place_xy_dist())
        except Exception:
            place_xy_dist = float("nan")
    elif cube_pos is not None and target_pos is not None:
        place_xy_dist = float(np.linalg.norm(cube_pos[:2] - target_pos[:2]))
    else:
        place_xy_dist = float("nan")

    ik_success = True
    if isinstance(ctrl_info, dict):
        ik_success = bool(ctrl_info.get("ik_success", True))

    step_count = int(getattr(env, "step_count", -1))

    info = {
        "success": bool(place_success),
        "grasp_success": bool(grasp_success),
        "place_success": bool(place_success),
        "place_success_loose": bool(place_success_loose),
        "place_xy_dist": float(place_xy_dist),
        "ik_success": bool(ik_success),
        "step_count": step_count,
        "ctrl_info": ctrl_info,
    }

    if cube_pos is not None:
        info["cube_pos"] = cube_pos

    if target_pos is not None:
        info["target_pos"] = target_pos

    return info


def step_env_with_controller(
    env,
    controller,
    action: np.ndarray,
    n_substeps: int = 20,
) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
    """
    正确执行 BC / Diffusion Policy 输出的 7D action。

    action:
        [dx, dy, dz, droll, dpitch, dyaw, gripper]
    """
    action = np.asarray(action, dtype=np.float64).reshape(-1)

    if action.shape[0] != 7:
        raise ValueError(
            f"Expected 7D action [dx,dy,dz,droll,dpitch,dyaw,gripper], "
            f"but got shape {action.shape}"
        )

    try:
        ctrl_out = controller.compute_control(
            dx=action[0],
            dy=action[1],
            dz=action[2],
            droll=action[3],
            dpitch=action[4],
            dyaw=action[5],
            gripper=action[6],
        )
    except TypeError:
        ctrl_out = controller.compute_control(action)

    if isinstance(ctrl_out, tuple):
        ctrl, ctrl_info = ctrl_out
    else:
        ctrl = ctrl_out
        ctrl_info = {}

    if hasattr(env, "step_count"):
        env.step_count += 1

    if hasattr(env, "step_sim"):
        step_ret = env.step_sim(ctrl=ctrl, n_substeps=n_substeps)
    elif hasattr(env, "step"):
        step_ret = env.step(ctrl=ctrl, n_substeps=n_substeps)
    else:
        raise RuntimeError(
            "Current env has neither step_sim() nor step(ctrl=...). "
            "Cannot execute MuJoCo ctrl."
        )

    if isinstance(step_ret, tuple):
        obs = step_ret[0]
    elif isinstance(step_ret, dict):
        obs = step_ret
    elif step_ret is None:
        obs = env.get_obs()
    else:
        obs = step_ret

    obs = ensure_obs_has_privileged(env, obs)

    if hasattr(env, "compute_reward"):
        reward = float(env.compute_reward())
    else:
        reward = 0.0

    info = compute_eval_info(env, ctrl_info=ctrl_info if isinstance(ctrl_info, dict) else {})

    done = bool(info.get("place_success", False))

    if hasattr(env, "max_episode_steps") and hasattr(env, "step_count"):
        if int(env.step_count) >= int(env.max_episode_steps):
            done = True

    return obs, reward, done, info


def run_one_episode(
    env,
    controller,
    model: StateBCPolicy,
    runtime: Dict[str, Any],
    device: torch.device,
    seed: int,
    episode_id: int,
    args,
) -> Tuple[Dict[str, Any], List[np.ndarray]]:
    obs = reset_env(env, seed=seed, args=args)

    state_mode = runtime.get("state_mode", "relative")
    first_state = build_privileged_state_from_obs(obs, mode=state_mode)

    if first_state.shape[0] != runtime["state_dim"]:
        raise ValueError(
            f"privileged_state dim mismatch: obs has {first_state.shape[0]}, "
            f"model expects {runtime['state_dim']}"
        )

    state_history = deque(maxlen=runtime["obs_horizon"])
    for _ in range(runtime["obs_horizon"]):
        state_history.append(first_state.copy())

    action_queue = deque()
    frames: List[np.ndarray] = []

    if args.save_video:
        frame = extract_frame(obs, env)
        if frame is not None:
            frames.append(frame)

    total_reward = 0.0
    last_info: Dict[str, Any] = {}
    done = False
    step = 0

    ever_grasp_success = False
    ever_place_success = False
    ever_place_success_loose = False

    for step in range(args.max_steps):
        if len(action_queue) == 0:
            action_seq = predict_action_sequence(
                model=model,
                state_history=state_history,
                runtime=runtime,
                device=device,
                action_clip_abs=args.action_clip_abs,
            )

            action_horizon = min(args.action_horizon, action_seq.shape[0])
            for i in range(action_horizon):
                action_queue.append(action_seq[i])

        action = action_queue.popleft()

        obs, reward, done, info = step_env_with_controller(
            env=env,
            controller=controller,
            action=action,
            n_substeps=args.n_substeps,
        )

        total_reward += float(reward)
        last_info = info

        ever_grasp_success = ever_grasp_success or bool(info.get("grasp_success", False))
        ever_place_success = ever_place_success or bool(info.get("place_success", False))
        ever_place_success_loose = ever_place_success_loose or bool(
            info.get("place_success_loose", False)
        )

        next_state = build_privileged_state_from_obs(obs, mode=state_mode)

        if next_state.shape[0] != runtime["state_dim"]:
            raise ValueError(
                f"privileged_state dim mismatch after step: obs has {next_state.shape[0]}, "
                f"model expects {runtime['state_dim']}"
            )

        state_history.append(next_state.copy())

        if args.debug and episode_id == 0 and (
            step < args.debug_first_n or step % args.debug_every == 0
        ):
            gripper_qpos = obs.get("gripper_qpos", None)
            ee_pos = obs.get("ee_pos", None)
            cube_pos = obs.get("cube_pos", None)
            target_pos = obs.get("target_pos", None)

            ee_cube_xy_dist = None
            ee_cube_z_diff = None
            if ee_pos is not None and cube_pos is not None:
                ee_pos_np = np.asarray(ee_pos, dtype=np.float32)
                cube_pos_np = np.asarray(cube_pos, dtype=np.float32)
                ee_cube_xy_dist = float(np.linalg.norm(ee_pos_np[:2] - cube_pos_np[:2]))
                ee_cube_z_diff = float(ee_pos_np[2] - cube_pos_np[2])

            print(
                f"[DEBUG step={step:03d}] "
                f"action_xyz={np.round(action[:3], 4)} "
                f"gripper_action={action[6]:+.4f} "
                f"gripper_qpos={np.round(gripper_qpos, 4) if gripper_qpos is not None else None} "
                f"ee_pos={np.round(ee_pos, 4) if ee_pos is not None else None} "
                f"cube_pos={np.round(cube_pos, 4) if cube_pos is not None else None} "
                f"target_pos={np.round(target_pos, 4) if target_pos is not None else None} "
                f"ee_cube_xy_dist={ee_cube_xy_dist} "
                f"ee_cube_z_diff={ee_cube_z_diff} "
                f"grasp={info.get('grasp_success')} "
                f"place={info.get('place_success')} "
                f"xy_dist={info.get('place_xy_dist')} "
                f"ik={info.get('ik_success')}"
            )

        if args.render:
            maybe_render_human(env)

        if args.save_video:
            frame = extract_frame(obs, env)
            if frame is not None:
                frames.append(frame)

        if done:
            break

    row = {
        "episode": int(episode_id),
        "seed": int(seed),
        "success": int(bool(ever_place_success)),
        "grasp_success": int(bool(ever_grasp_success)),
        "place_success": int(bool(ever_place_success)),
        "place_success_loose": int(bool(ever_place_success_loose)),
        "final_grasp_success": int(bool(last_info.get("grasp_success", False))),
        "final_place_success": int(bool(last_info.get("place_success", False))),
        "final_place_success_loose": int(bool(last_info.get("place_success_loose", False))),
        "place_xy_dist": float(last_info.get("place_xy_dist", np.nan)),
        "steps": int(step + 1),
        "total_reward": float(total_reward),
        "done": int(bool(done)),
        "ik_success": int(bool(last_info.get("ik_success", True))),
    }

    return row, frames


def write_csv(path: Path, rows: List[Dict[str, Any]]):
    if not rows:
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(rows[0].keys())

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def compute_summary(
    rows: List[Dict[str, Any]],
    args,
    runtime: Dict[str, Any],
) -> Dict[str, Any]:
    if rows:
        success_rate = float(np.mean([r["success"] for r in rows]))
        grasp_rate = float(np.mean([r["grasp_success"] for r in rows]))
        place_rate = float(np.mean([r["place_success"] for r in rows]))
        place_loose_rate = float(np.mean([r["place_success_loose"] for r in rows]))
        mean_steps = float(np.mean([r["steps"] for r in rows]))
        mean_reward = float(np.mean([r["total_reward"] for r in rows]))
        xy_values = [r["place_xy_dist"] for r in rows]
        mean_xy_dist = float(np.nanmean(xy_values))
        ik_rate = float(np.mean([r["ik_success"] for r in rows]))
    else:
        success_rate = 0.0
        grasp_rate = 0.0
        place_rate = 0.0
        place_loose_rate = 0.0
        mean_steps = 0.0
        mean_reward = 0.0
        mean_xy_dist = float("nan")
        ik_rate = 0.0

    summary = {
        "checkpoint": args.checkpoint,
        "stats_path": runtime["stats_path"],
        "output_dir": args.output_dir,
        "num_episodes": int(args.num_episodes),
        "start_seed": int(args.start_seed),
        "max_steps": int(args.max_steps),
        "fixed_scene": bool(args.fixed_scene),
        "state_mode": runtime.get("state_mode", "relative"),
        "state_dim": int(runtime["state_dim"]),
        "action_dim": int(runtime["action_dim"]),
        "obs_horizon": int(runtime["obs_horizon"]),
        "pred_horizon": int(runtime["pred_horizon"]),
        "action_horizon": int(args.action_horizon),
        "n_substeps": int(args.n_substeps),
        "success_rate": success_rate,
        "grasp_success_rate": grasp_rate,
        "place_success_rate": place_rate,
        "place_success_loose_rate": place_loose_rate,
        "mean_place_xy_dist": mean_xy_dist,
        "mean_steps": mean_steps,
        "mean_total_reward": mean_reward,
        "ik_success_rate": ik_rate,
    }

    return summary


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--checkpoint",
        type=str,
        default="experiments/bc_privileged_state_v2/best.pt",
    )
    parser.add_argument(
        "--stats_path",
        type=str,
        default="experiments/bc_privileged_state_v2/privileged_state_stats.json",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="experiments/bc_privileged_state_v2/eval_rollout",
    )

    parser.add_argument("--num_episodes", type=int, default=5)
    parser.add_argument("--start_seed", type=int, default=1000)
    parser.add_argument("--max_steps", type=int, default=700)

    parser.add_argument("--xml_path", type=str, default="")
    parser.add_argument("--camera_name", type=str, default="top")
    parser.add_argument("--render_width", type=int, default=224)
    parser.add_argument("--render_height", type=int, default=224)

    parser.add_argument(
        "--fixed_scene",
        action="store_true",
        help="Use fixed cube/target position for first sanity check.",
    )
    parser.add_argument("--fixed_cube_x", type=float, default=0.53)
    parser.add_argument("--fixed_cube_y", type=float, default=-0.10)
    parser.add_argument("--fixed_target_x", type=float, default=0.66)
    parser.add_argument("--fixed_target_y", type=float, default=0.13)

    parser.add_argument(
        "--action_horizon",
        type=int,
        default=1,
        help="How many predicted actions to execute before re-planning.",
    )
    parser.add_argument(
        "--action_clip_abs",
        type=float,
        default=1.0,
        help="Safety clip for unnormalized 7D action. Set <=0 to disable.",
    )
    parser.add_argument(
        "--n_substeps",
        type=int,
        default=20,
        help="MuJoCo substeps per policy action.",
    )

    parser.add_argument("--obs_horizon", type=int, default=2)
    parser.add_argument("--pred_horizon", type=int, default=16)
    parser.add_argument("--hidden_dim", type=int, default=256)
    parser.add_argument("--dropout", type=float, default=0.0)

    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--save_video", action="store_true")
    parser.add_argument("--video_fps", type=int, default=20)

    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--debug_first_n", type=int, default=30)
    parser.add_argument("--debug_every", type=int, default=20)

    args = parser.parse_args()

    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    model, runtime = load_model_and_stats(args, device)

    print("=" * 100)
    print("[Privileged-state BC MuJoCo Rollout Eval]")
    print(f"checkpoint:      {args.checkpoint}")
    print(f"stats_path:      {runtime['stats_path']}")
    print(f"output_dir:      {args.output_dir}")
    print(f"device:          {device}")
    print(f"state_mode:      {runtime.get('state_mode', 'relative')}")
    print(f"state_dim:       {runtime['state_dim']}")
    print(f"action_dim:      {runtime['action_dim']}")
    print(f"obs_horizon:     {runtime['obs_horizon']}")
    print(f"pred_horizon:    {runtime['pred_horizon']}")
    print(f"action_horizon:  {args.action_horizon}")
    print(f"n_substeps:      {args.n_substeps}")
    print(f"num_episodes:    {args.num_episodes}")
    print(f"fixed_scene:     {args.fixed_scene}")
    print("=" * 100)

    env = build_env(args, seed=args.start_seed)
    # 关键修改：让命令行 --max_steps 覆盖环境内部 300 步限制
    if hasattr(env, "max_episode_steps"):
        old_limit = int(env.max_episode_steps)
        env.max_episode_steps = int(args.max_steps)
        print(f"[INFO] Override env.max_episode_steps: {old_limit} -> {env.max_episode_steps}")

    controller = build_controller(env)

    rows: List[Dict[str, Any]] = []

    try:
        for ep in range(args.num_episodes):
            seed = args.start_seed + ep

            row, frames = run_one_episode(
                env=env,
                controller=controller,
                model=model,
                runtime=runtime,
                device=device,
                seed=seed,
                episode_id=ep,
                args=args,
            )

            rows.append(row)

            if args.save_video:
                video_path = output_dir / "videos" / f"episode_{ep:03d}_seed_{seed}.mp4"
                save_video_mp4(frames, video_path, fps=args.video_fps)

            print(
                f"episode {ep:03d} | "
                f"seed={seed} | "
                f"success={row['success']} | "
                f"grasp={row['grasp_success']} | "
                f"place={row['place_success']} | "
                f"place_loose={row['place_success_loose']} | "
                f"xy_dist={row['place_xy_dist']:.4f} | "
                f"steps={row['steps']} | "
                f"reward={row['total_reward']:.3f} | "
                f"ik={row['ik_success']}"
            )

    finally:
        if hasattr(env, "close"):
            env.close()

    eval_csv_path = output_dir / "eval_results.csv"
    summary_path = output_dir / "summary.json"

    write_csv(eval_csv_path, rows)

    summary = compute_summary(rows=rows, args=args, runtime=runtime)

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # 兼容之前 state-only rollout 的文件名习惯
    rollout_csv_path = output_dir / "rollout_results.csv"
    rollout_summary_path = output_dir / "rollout_summary.json"

    try:
        shutil.copyfile(eval_csv_path, rollout_csv_path)
        shutil.copyfile(summary_path, rollout_summary_path)
    except Exception:
        pass

    print("=" * 100)
    print("[SUMMARY]")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"csv:      {eval_csv_path}")
    print(f"summary:  {summary_path}")
    if args.save_video:
        print(f"videos:   {output_dir / 'videos'}")
    print("=" * 100)


if __name__ == "__main__":
    main()
