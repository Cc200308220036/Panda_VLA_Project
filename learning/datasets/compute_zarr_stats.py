"""
实现目的：
    计算 Zarr 数据集中 robot_state 和 action 的归一化统计量，
    并生成 train / val episode 划分信息，供后续 PyTorch Dataset 和 BC 训练使用。

输入：
    --zarr_path:
        Zarr 数据集路径，例如 data/zarr/pick_place_scripted_200.zarr

    --output:
        统计量 JSON 输出路径。
        如果不指定，默认输出到：
        data/metadata/pick_place_scripted_200.zarr_stats.json

    --val_ratio:
        验证集 episode 比例，默认 0.1

    --split_seed:
        train / val 划分随机种子，默认 42

输出：
    一个 JSON 文件，包含：
        state_mean / state_std / state_min / state_max
        action_mean / action_std / action_min / action_max
        train_episode_indices
        val_episode_indices
        episode_ends
        episode_lengths
        state_dim
        action_dim
        total_steps
"""

import os
import json
import argparse

import zarr
import numpy as np
from tqdm import tqdm


def make_default_output_path(zarr_path: str) -> str:
    zarr_path = zarr_path.rstrip("/")
    return zarr_path + "_stats.json"


def safe_std(std: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    """
    对几乎恒定的维度，std 设为 1.0，避免归一化时除以极小值导致数值爆炸。
    """
    std = np.asarray(std, dtype=np.float64)
    return np.where(std < eps, 1.0, std)


def get_episode_range(episode_ends: np.ndarray, episode_id: int):
    start = 0 if episode_id == 0 else int(episode_ends[episode_id - 1])
    end = int(episode_ends[episode_id])
    return start, end


def compute_stats_for_episode_ids(
    states,
    actions,
    episode_ends: np.ndarray,
    episode_ids,
):
    state_dim = int(states.shape[1])
    action_dim = int(actions.shape[1])

    state_sum = np.zeros(state_dim, dtype=np.float64)
    state_sq_sum = np.zeros(state_dim, dtype=np.float64)
    state_min = np.full(state_dim, np.inf, dtype=np.float64)
    state_max = np.full(state_dim, -np.inf, dtype=np.float64)

    action_sum = np.zeros(action_dim, dtype=np.float64)
    action_sq_sum = np.zeros(action_dim, dtype=np.float64)
    action_min = np.full(action_dim, np.inf, dtype=np.float64)
    action_max = np.full(action_dim, -np.inf, dtype=np.float64)

    count = 0

    for ep_id in tqdm(episode_ids, desc="Computing stats"):
        start, end = get_episode_range(episode_ends, int(ep_id))

        s = np.asarray(states[start:end], dtype=np.float64)
        a = np.asarray(actions[start:end], dtype=np.float64)

        if s.shape[0] != a.shape[0]:
            raise ValueError(
                f"State/action length mismatch in episode {ep_id}: "
                f"state={s.shape}, action={a.shape}"
            )

        state_sum += s.sum(axis=0)
        state_sq_sum += (s ** 2).sum(axis=0)
        state_min = np.minimum(state_min, s.min(axis=0))
        state_max = np.maximum(state_max, s.max(axis=0))

        action_sum += a.sum(axis=0)
        action_sq_sum += (a ** 2).sum(axis=0)
        action_min = np.minimum(action_min, a.min(axis=0))
        action_max = np.maximum(action_max, a.max(axis=0))

        count += s.shape[0]

    if count <= 0:
        raise RuntimeError("No timesteps found for stats computation.")

    state_mean = state_sum / count
    state_var = state_sq_sum / count - state_mean ** 2
    state_std_raw = np.sqrt(np.maximum(state_var, 0.0))
    state_std = safe_std(state_std_raw)

    action_mean = action_sum / count
    action_var = action_sq_sum / count - action_mean ** 2
    action_std_raw = np.sqrt(np.maximum(action_var, 0.0))
    action_std = safe_std(action_std_raw)

    return {
        "count": int(count),

        "state_mean": state_mean.astype(np.float32).tolist(),
        "state_std": state_std.astype(np.float32).tolist(),
        "state_std_raw": state_std_raw.astype(np.float32).tolist(),
        "state_min": state_min.astype(np.float32).tolist(),
        "state_max": state_max.astype(np.float32).tolist(),

        "action_mean": action_mean.astype(np.float32).tolist(),
        "action_std": action_std.astype(np.float32).tolist(),
        "action_std_raw": action_std_raw.astype(np.float32).tolist(),
        "action_min": action_min.astype(np.float32).tolist(),
        "action_max": action_max.astype(np.float32).tolist(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--zarr_path",
        type=str,
        default="data/zarr/pick_place_scripted_200.zarr",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
    )
    parser.add_argument("--val_ratio", type=float, default=0.1)
    parser.add_argument("--split_seed", type=int, default=42)
    args = parser.parse_args()

    if args.output is None:
        args.output = make_default_output_path(args.zarr_path)

    root = zarr.open_group(args.zarr_path, mode="r")

    states = root["data/robot_state"]
    actions = root["data/action"]
    episode_ends = np.asarray(root["meta/episode_ends"][:], dtype=np.int64)

    total_steps = int(actions.shape[0])
    num_episodes = int(len(episode_ends))

    if states.shape[0] != total_steps:
        raise ValueError(
            f"robot_state length != action length: "
            f"{states.shape[0]} vs {total_steps}"
        )

    if int(episode_ends[-1]) != total_steps:
        raise ValueError(
            f"episode_ends[-1] != total_steps: "
            f"{episode_ends[-1]} vs {total_steps}"
        )

    episode_lengths = np.diff(
        np.concatenate([[0], episode_ends])
    ).astype(np.int64)

    all_episode_ids = np.arange(num_episodes, dtype=np.int64)
    rng = np.random.default_rng(args.split_seed)
    shuffled = all_episode_ids.copy()
    rng.shuffle(shuffled)

    if args.val_ratio <= 0:
        val_episode_ids = np.array([], dtype=np.int64)
    else:
        num_val = int(round(num_episodes * args.val_ratio))
        if num_episodes > 1:
            num_val = max(1, min(num_val, num_episodes - 1))
        else:
            num_val = 0
        val_episode_ids = np.sort(shuffled[:num_val])

    train_episode_ids = np.sort(
        np.asarray(
            [ep for ep in all_episode_ids if ep not in set(val_episode_ids.tolist())],
            dtype=np.int64,
        )
    )

    if len(train_episode_ids) == 0:
        raise RuntimeError("No train episodes. Please reduce --val_ratio.")

    stats = compute_stats_for_episode_ids(
        states=states,
        actions=actions,
        episode_ends=episode_ends,
        episode_ids=train_episode_ids,
    )

    output = {
        "zarr_path": os.path.abspath(args.zarr_path),
        "image_key": "data/image",
        "state_key": "data/robot_state",
        "action_key": "data/action",
        "episode_ends_key": "meta/episode_ends",

        "num_episodes": num_episodes,
        "total_steps": total_steps,
        "episode_ends": episode_ends.astype(np.int64).tolist(),
        "episode_lengths": episode_lengths.astype(np.int64).tolist(),

        "state_dim": int(states.shape[1]),
        "action_dim": int(actions.shape[1]),

        "val_ratio": float(args.val_ratio),
        "split_seed": int(args.split_seed),
        "train_episode_indices": train_episode_ids.astype(np.int64).tolist(),
        "val_episode_indices": val_episode_ids.astype(np.int64).tolist(),

        **stats,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print("=" * 100)
    print("[OK] Zarr stats saved")
    print(f"zarr_path:      {args.zarr_path}")
    print(f"output:         {args.output}")
    print(f"num_episodes:   {num_episodes}")
    print(f"total_steps:    {total_steps}")
    print(f"state_dim:      {states.shape[1]}")
    print(f"action_dim:     {actions.shape[1]}")
    print(f"train episodes: {len(train_episode_ids)}")
    print(f"val episodes:   {len(val_episode_ids)}")
    print(f"stats count:    {stats['count']}")
    print("=" * 100)


if __name__ == "__main__":
    main()
