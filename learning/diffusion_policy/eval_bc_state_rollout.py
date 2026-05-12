"""
实现目标：
    部署并评估 state-only Behavior Cloning 模型在 MuJoCo Panda pick-place 环境中的闭环 rollout 表现。

    该脚本完成：
        1. 加载训练好的 state-only BC checkpoint；
        2. 加载 state/action normalization 统计量；
        3. 创建 MuJoCo PickPlaceEnv；
        4. 维护 obs_horizon 长度的 robot_state buffer；
        5. 使用 BC 模型预测未来 pred_horizon 步 action；
        6. 对 action 做反归一化；
        7. 将 7D action 输入 MuJoCo 环境闭环执行；
        8. 统计 success / grasp_success / place_success；
        9. 保存 rollout_results.csv 和 rollout_summary.json；
        10. 可选保存 rollout 视频。

输入：
    --checkpoint:
        训练好的 state-only BC checkpoint。
        推荐：
            experiments/bc_state_v1_debug/best.pt

    --stats_path:
        数据集统计量 JSON。
        默认优先从 checkpoint["config"]["stats_path"] 读取。
        也可以手动指定：
            data/metadata/pick_place_scripted_200.zarr_stats.json

    --output_dir:
        rollout 结果保存目录。

    --num_episodes:
        评估 episode 数量。

    --max_steps:
        每个 episode 最大控制步数。

    --fixed_scene:
        是否使用固定 cube/target 位置。
        state-only BC 不看图像、不看 cube_pos/target_pos，
        所以建议先用 fixed_scene 验证链路，再做随机场景测试。

输出：
    output_dir/rollout_results.csv:
        每个 episode 的 seed、success、grasp_success、place_success、xy_dist、steps、total_reward 等。

    output_dir/rollout_summary.json:
        平均成功率、平均抓取率、平均放置距离等汇总指标。

    output_dir/videos/*.mp4:
        如果启用 --save_video，则保存每个 episode 的 rollout 视频。

说明：
    当前模型是 state-only BC，只使用 robot_state。
    它看不到图像、cube 位置和 target 位置。
    因此随机场景下成功率低是正常现象。
    本脚本的核心作用是检查：
        - checkpoint 加载是否正确；
        - state normalization 是否正确；
        - action unnormalization 是否正确；
        - 模型输出维度是否正确；
        - env.step(action) 闭环执行链路是否正确。
"""

import argparse
import csv
import json
import os
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


from mujoco_env.controllers.ee_delta_controller import EEDeltaController



def try_import_pick_place_env():
    """
    兼容两种常见项目结构：

    方式 1：
        from mujoco_env.envs.pick_place_env import PickPlaceEnv

    方式 2：
        cd mujoco_env 后：
        from envs.pick_place_env import PickPlaceEnv
    """
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
    return np.where(std < eps, eps, std)


def get_robot_state_from_obs(obs: Dict[str, Any]) -> np.ndarray:
    """
    优先使用 obs["robot_state"]。
    如果环境暂时没有 robot_state，则从基础字段拼接：

        joint_pos 7
        joint_vel 7
        gripper_qpos 2
        ee_pos 3
        ee_quat 4
        total = 23
    """
    if "robot_state" in obs:
        return np.asarray(obs["robot_state"], dtype=np.float32).reshape(-1)

    required_keys = [
        "joint_pos",
        "joint_vel",
        "gripper_qpos",
        "ee_pos",
        "ee_quat",
    ]

    missing = [k for k in required_keys if k not in obs]
    if missing:
        raise KeyError(
            f"Observation does not contain robot_state, and missing keys: {missing}"
        )

    state = np.concatenate(
        [
            np.asarray(obs["joint_pos"], dtype=np.float32).reshape(-1),
            np.asarray(obs["joint_vel"], dtype=np.float32).reshape(-1),
            np.asarray(obs["gripper_qpos"], dtype=np.float32).reshape(-1),
            np.asarray(obs["ee_pos"], dtype=np.float32).reshape(-1),
            np.asarray(obs["ee_quat"], dtype=np.float32).reshape(-1),
        ],
        axis=0,
    )

    return state.astype(np.float32)


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

    import inspect
    print("[DEBUG ENV CLASS]", env.__class__)
    print("[DEBUG ENV FILE]", inspect.getfile(env.__class__))
    print("[DEBUG ENV STEP SIG]", inspect.signature(env.step))
    print("[DEBUG HAS _action_to_ctrl]", hasattr(env, "_action_to_ctrl"))

    return env

def build_controller(env):
    """
    必须和 HDF5 collect / replay 成功链路保持一致。
    policy 输出 7D action，controller 转成 MuJoCo ctrl。
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


def reset_env(env, seed: int, args):
    """
    支持随机场景和固定场景。

    固定场景用于先验证 state-only BC rollout 链路。
    因为 state-only BC 看不到 cube/target 随机位置。
    """
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
                "fixed_scene requires env.set_cube_pose(xy), but current env does not have it."
            )

        if not hasattr(env, "set_target_pose"):
            raise AttributeError(
                "fixed_scene requires env.set_target_pose(xy), but current env does not have it."
            )

        env.set_cube_pose(cube_xy)
        env.set_target_pose(target_xy)

        if mujoco is not None and hasattr(env, "model") and hasattr(env, "data"):
            mujoco.mj_forward(env.model, env.data)

        obs = env.get_obs()

    return obs


def parse_step_output(step_output):
    """
    统一解析 env.step() 返回值。

    支持：
        Gym:        obs, reward, done, info
        Gymnasium:  obs, reward, terminated, truncated, info

    不允许只返回 obs。
    因为只返回 obs 通常说明调用到了 PandaBaseEnv.step()，
    而不是 PickPlaceEnv.step()。
    """
    if not isinstance(step_output, tuple):
        raise RuntimeError(
            "env.step() returned only obs, not (obs, reward, done, info). "
            "This usually means you are calling PandaBaseEnv.step(), "
            "not PickPlaceEnv.step()."
        )

    if len(step_output) == 4:
        obs, reward, done, info = step_output
        return obs, float(reward), bool(done), info

    if len(step_output) == 5:
        obs, reward, terminated, truncated, info = step_output
        done = bool(terminated) or bool(truncated)
        return obs, float(reward), done, info

    raise RuntimeError(
        f"Unsupported env.step() tuple length: {len(step_output)}. "
        "Expected 4 or 5 values."
    )


def step_env(env, controller, action: np.ndarray, n_substeps: int = 20):
    """
    正确执行 BC / Diffusion Policy 输出的 7D action。

    action:
        [dx, dy, dz, droll, dpitch, dyaw, gripper]

    注意：
        不能调用 env.step(action=action)。
        当前稳定环境必须走：
            action -> EEDeltaController -> ctrl -> env.step_sim(ctrl)
    """
    action = np.asarray(action, dtype=np.float64).reshape(-1)

    if action.shape[0] != 7:
        raise ValueError(
            f"Expected 7D action [dx,dy,dz,droll,dpitch,dyaw,gripper], "
            f"but got shape {action.shape}"
        )

    ctrl_out = controller.compute_control(
        dx=action[0],
        dy=action[1],
        dz=action[2],
        droll=action[3],
        dpitch=action[4],
        dyaw=action[5],
        gripper=action[6],
    )

    if isinstance(ctrl_out, tuple):
        ctrl, ctrl_info = ctrl_out
    else:
        ctrl = ctrl_out
        ctrl_info = {}

    if not hasattr(env, "step_sim"):
        raise RuntimeError(
            "Current env has no step_sim(). "
            "Your successful collect/replay chain requires env.step_sim(ctrl=...)."
        )

    step_ret = env.step_sim(ctrl=ctrl, n_substeps=n_substeps)

    if isinstance(step_ret, dict):
        obs = step_ret
    else:
        obs = env.get_obs()

    reward = float(env.compute_reward()) if hasattr(env, "compute_reward") else 0.0

    grasp_success = bool(env.is_grasp_success()) if hasattr(env, "is_grasp_success") else False

    if hasattr(env, "is_place_success"):
        place_success = bool(env.is_place_success(strict=True))
        place_success_loose = bool(env.is_place_success(strict=False))
    else:
        place_success = False
        place_success_loose = False

    if hasattr(env, "get_place_xy_dist"):
        place_xy_dist = float(env.get_place_xy_dist())
    else:
        place_xy_dist = float("nan")

    if isinstance(ctrl_info, dict):
        ik_success = bool(ctrl_info.get("ik_success", True))
    else:
        ik_success = True

    info = {
        "success": place_success,
        "grasp_success": grasp_success,
        "place_success": place_success,
        "place_success_loose": place_success_loose,
        "place_xy_dist": place_xy_dist,
        "ik_success": ik_success,
        "ctrl_info": ctrl_info,
    }

    done = bool(place_success)

    return obs, reward, done, info




def maybe_render_human(env):
    if hasattr(env, "render_human"):
        env.render_human()


def extract_frame(obs: Dict[str, Any], env) -> Optional[np.ndarray]:
    if "image" in obs:
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

    first = frames[0]
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
    }

    return model, runtime


def predict_action_sequence(
    model: StateBCPolicy,
    state_history: deque,
    runtime: Dict[str, Any],
    device: torch.device,
    action_clip_abs: float,
) -> np.ndarray:
    state_window = np.stack(list(state_history), axis=0).astype(np.float32)

    if state_window.shape != (runtime["obs_horizon"], runtime["state_dim"]):
        raise ValueError(
            f"state_window shape mismatch: got {state_window.shape}, "
            f"expected {(runtime['obs_horizon'], runtime['state_dim'])}"
        )

    state_window_norm = normalize_state(
        state_window=state_window,
        state_mean=runtime["state_mean"],
        state_std=runtime["state_std"],
    )

    state_tensor = torch.from_numpy(state_window_norm).unsqueeze(0).to(device)

    with torch.no_grad():
        action_norm_seq = model(state_tensor)
        action_norm_seq = action_norm_seq.squeeze(0).detach().cpu().numpy()

    action_seq = unnormalize_action(
        action_norm=action_norm_seq,
        action_mean=runtime["action_mean"],
        action_std=runtime["action_std"],
    )

    action_seq = np.nan_to_num(
        action_seq,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    if action_clip_abs is not None and action_clip_abs > 0:
        action_seq = np.clip(
            action_seq,
            -float(action_clip_abs),
            float(action_clip_abs),
        )

    return action_seq.astype(np.float32)


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

    first_state = get_robot_state_from_obs(obs)
    if first_state.shape[0] != runtime["state_dim"]:
        raise ValueError(
            f"robot_state dim mismatch: obs has {first_state.shape[0]}, "
            f"model expects {runtime['state_dim']}"
        )

    state_history = deque(maxlen=runtime["obs_horizon"])
    for _ in range(runtime["obs_horizon"]):
        state_history.append(first_state.copy())

    action_queue = deque()
    frames = []

    if args.save_video:
        frame = extract_frame(obs, env)
        if frame is not None:
            frames.append(frame)

    total_reward = 0.0
    last_info = {}
    done = False
    step = 0

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

        obs, reward, done, info = step_env(
            env=env,
            controller=controller,
            action=action,
            n_substeps=20,
        )

        if episode_id == 0 and (step < 30 or step % 20 == 0):
            gripper_qpos = obs.get("gripper_qpos", None)
            ee_pos = obs.get("ee_pos", None)

            if "cube_pos" in obs:
                cube_pos = obs["cube_pos"]
            elif hasattr(env, "get_cube_pos"):
                cube_pos = env.get_cube_pos()
            else:
                cube_pos = None

            if "target_pos" in obs:
                target_pos = obs["target_pos"]
            elif hasattr(env, "get_target_pos"):
                target_pos = env.get_target_pos()
            else:
                target_pos = None

            ee_cube_xy_dist = None
            ee_cube_z_diff = None

            if ee_pos is not None and cube_pos is not None:
                ee_pos_np = np.asarray(ee_pos, dtype=np.float32).reshape(-1)
                cube_pos_np = np.asarray(cube_pos, dtype=np.float32).reshape(-1)

                ee_cube_xy_dist = float(
                    np.linalg.norm(ee_pos_np[:2] - cube_pos_np[:2])
                )
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


        total_reward += float(reward)
        last_info = info

        next_state = get_robot_state_from_obs(obs)
        if next_state.shape[0] != runtime["state_dim"]:
            raise ValueError(
                f"robot_state dim mismatch after step: obs has {next_state.shape[0]}, "
                f"model expects {runtime['state_dim']}"
            )

        state_history.append(next_state.copy())

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
        "success": int(bool(last_info.get("success", False))),
        "grasp_success": int(bool(last_info.get("grasp_success", False))),
        "place_success": int(bool(last_info.get("place_success", False))),
        "place_success_loose": int(bool(last_info.get("place_success_loose", False))),
        "place_xy_dist": float(last_info.get("place_xy_dist", np.nan)),
        "steps": int(last_info.get("step_count", step + 1)),
        "total_reward": float(total_reward),
        "done": int(bool(done)),
    }

    if "ik_success" in last_info:
        row["ik_success"] = int(bool(last_info.get("ik_success", False)))

    return row, frames


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--checkpoint",
        type=str,
        default="experiments/bc_state_v1_debug/best.pt",
    )
    parser.add_argument(
        "--stats_path",
        type=str,
        default="",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="experiments/bc_state_v1_debug/eval_rollout",
    )

    parser.add_argument("--num_episodes", type=int, default=20)
    parser.add_argument("--start_seed", type=int, default=1000)
    parser.add_argument("--max_steps", type=int, default=300)

    parser.add_argument("--xml_path", type=str, default="")
    parser.add_argument("--camera_name", type=str, default="top")
    parser.add_argument("--render_width", type=int, default=224)
    parser.add_argument("--render_height", type=int, default=224)

    parser.add_argument(
        "--fixed_scene",
        action="store_true",
        help="Use fixed cube/target position. Recommended for first state-only BC rollout test.",
    )
    parser.add_argument("--fixed_cube_x", type=float, default=0.53)
    parser.add_argument("--fixed_cube_y", type=float, default=-0.10)
    parser.add_argument("--fixed_target_x", type=float, default=0.66)
    parser.add_argument("--fixed_target_y", type=float, default=0.13)

    parser.add_argument(
        "--action_horizon",
        type=int,
        default=1,
        help="How many predicted actions to execute before re-planning. Default 1.",
    )
    parser.add_argument(
        "--action_clip_abs",
        type=float,
        default=1.0,
        help="Safety clip for unnormalized 7D action. Set <=0 to disable.",
    )

    parser.add_argument("--obs_horizon", type=int, default=2)
    parser.add_argument("--pred_horizon", type=int, default=16)
    parser.add_argument("--hidden_dim", type=int, default=256)
    parser.add_argument("--dropout", type=float, default=0.0)

    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--save_video", action="store_true")
    parser.add_argument("--video_fps", type=int, default=20)

    args = parser.parse_args()

    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    model, runtime = load_model_and_stats(args, device)

    print("=" * 100)
    print("[State-only BC MuJoCo Rollout Eval]")
    print(f"checkpoint:      {args.checkpoint}")
    print(f"stats_path:      {runtime['stats_path']}")
    print(f"output_dir:      {args.output_dir}")
    print(f"device:          {device}")
    print(f"state_dim:       {runtime['state_dim']}")
    print(f"action_dim:      {runtime['action_dim']}")
    print(f"obs_horizon:     {runtime['obs_horizon']}")
    print(f"pred_horizon:    {runtime['pred_horizon']}")
    print(f"action_horizon:  {args.action_horizon}")
    print(f"num_episodes:    {args.num_episodes}")
    print(f"fixed_scene:     {args.fixed_scene}")
    print("=" * 100)

    env = build_env(args, seed=args.start_seed)
    controller = build_controller(env)


    rows = []

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
                f"reward={row['total_reward']:.3f}"
            )

    finally:
        if hasattr(env, "close"):
            env.close()

    csv_path = output_dir / "rollout_results.csv"
    summary_path = output_dir / "rollout_summary.json"

    fieldnames = [
        "episode",
        "seed",
        "success",
        "grasp_success",
        "place_success",
        "place_success_loose",
        "place_xy_dist",
        "steps",
        "total_reward",
        "done",
    ]

    if any("ik_success" in row for row in rows):
        fieldnames.append("ik_success")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    success_rate = float(np.mean([r["success"] for r in rows])) if rows else 0.0
    grasp_rate = float(np.mean([r["grasp_success"] for r in rows])) if rows else 0.0
    place_rate = float(np.mean([r["place_success"] for r in rows])) if rows else 0.0
    place_loose_rate = float(np.mean([r["place_success_loose"] for r in rows])) if rows else 0.0
    mean_steps = float(np.mean([r["steps"] for r in rows])) if rows else 0.0
    mean_reward = float(np.mean([r["total_reward"] for r in rows])) if rows else 0.0

    xy_values = [r["place_xy_dist"] for r in rows]
    mean_xy_dist = float(np.nanmean(xy_values)) if rows else float("nan")

    summary = {
        "checkpoint": args.checkpoint,
        "stats_path": runtime["stats_path"],
        "output_dir": args.output_dir,
        "num_episodes": int(args.num_episodes),
        "start_seed": int(args.start_seed),
        "max_steps": int(args.max_steps),
        "fixed_scene": bool(args.fixed_scene),
        "state_dim": int(runtime["state_dim"]),
        "action_dim": int(runtime["action_dim"]),
        "obs_horizon": int(runtime["obs_horizon"]),
        "pred_horizon": int(runtime["pred_horizon"]),
        "action_horizon": int(args.action_horizon),
        "success_rate": success_rate,
        "grasp_success_rate": grasp_rate,
        "place_success_rate": place_rate,
        "place_success_loose_rate": place_loose_rate,
        "mean_place_xy_dist": mean_xy_dist,
        "mean_steps": mean_steps,
        "mean_total_reward": mean_reward,
    }

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("=" * 100)
    print("[SUMMARY]")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"csv:      {csv_path}")
    print(f"summary:  {summary_path}")
    if args.save_video:
        print(f"videos:   {output_dir / 'videos'}")
    print("=" * 100)


if __name__ == "__main__":
    main()
