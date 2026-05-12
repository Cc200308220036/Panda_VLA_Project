"""
实现目标：
    训练 privileged-state Behavior Cloning baseline。

    该模型不是最终 VLA/视觉策略，而是一个诊断模型：
    用 robot_state + cube_pos + target_pos + relative state 作为输入，
    验证数据、动作、控制器、rollout 部署链路是否正确。

输入：
    --zarr_path:
        Zarr 数据集路径，要求包含：
            data/robot_state  float32 [N, 23]
            data/action       float32 [N, 7]
            data/cube_pos     float32 [N, 3]
            data/target_pos   float32 [N, 3]
            meta/episode_ends int64   [num_episodes]

    --state_mode:
        simple:
            state_dim = 29
        relative:
            state_dim = 38，默认推荐

输出：
    output_dir/
        best.pt
        last.pt
        privileged_state_stats.json
        train_log.csv

    best.pt 中保存：
        model_state_dict
        config
        stats_path
        best_val_loss
"""

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
import torch.nn.functional as F
import zarr
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm

from learning.diffusion_policy.model import StateBCPolicy, count_parameters
from learning.diffusion_policy.privileged_state_utils import (
    build_privileged_state_from_arrays,
)


def safe_std(x: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    return np.maximum(x, eps).astype(np.float32)


def get_episode_range(episode_ends: np.ndarray, ep_id: int) -> Tuple[int, int]:
    start = 0 if ep_id == 0 else int(episode_ends[ep_id - 1])
    end = int(episode_ends[ep_id])
    return start, end


def build_sample_indices(
    episode_ends: np.ndarray,
    episode_ids: np.ndarray,
    obs_horizon: int,
    pred_horizon: int,
) -> np.ndarray:
    indices: List[int] = []

    for ep_id in episode_ids:
        start, end = get_episode_range(episode_ends, int(ep_id))
        ep_len = end - start

        min_len = obs_horizon + pred_horizon
        if ep_len < min_len:
            continue

        first_t = start + obs_horizon - 1
        last_t = end - pred_horizon

        for t in range(first_t, last_t + 1):
            indices.append(t)

    if len(indices) == 0:
        raise RuntimeError("No valid training samples. Check horizons and episode lengths.")

    return np.asarray(indices, dtype=np.int64)


def compute_stats(
    privileged_state: np.ndarray,
    actions: np.ndarray,
    episode_ends: np.ndarray,
    train_episode_ids: np.ndarray,
) -> Dict:
    step_indices = []

    for ep_id in train_episode_ids:
        start, end = get_episode_range(episode_ends, int(ep_id))
        step_indices.append(np.arange(start, end, dtype=np.int64))

    step_indices = np.concatenate(step_indices, axis=0)

    train_states = privileged_state[step_indices]
    train_actions = actions[step_indices]

    state_mean = train_states.mean(axis=0).astype(np.float32)
    state_std = safe_std(train_states.std(axis=0).astype(np.float32))

    action_mean = train_actions.mean(axis=0).astype(np.float32)
    action_std = safe_std(train_actions.std(axis=0).astype(np.float32))

    return {
        "state_mean": state_mean.tolist(),
        "state_std": state_std.tolist(),
        "action_mean": action_mean.tolist(),
        "action_std": action_std.tolist(),
        "state_dim": int(privileged_state.shape[1]),
        "action_dim": int(actions.shape[1]),
    }


class PrivilegedStateBCDataset(Dataset):
    def __init__(
        self,
        privileged_state: np.ndarray,
        actions: np.ndarray,
        indices: np.ndarray,
        obs_horizon: int,
        pred_horizon: int,
        state_mean: np.ndarray,
        state_std: np.ndarray,
        action_mean: np.ndarray,
        action_std: np.ndarray,
    ):
        self.privileged_state = privileged_state.astype(np.float32)
        self.actions = actions.astype(np.float32)
        self.indices = indices.astype(np.int64)

        self.obs_horizon = int(obs_horizon)
        self.pred_horizon = int(pred_horizon)

        self.state_mean = state_mean.astype(np.float32)
        self.state_std = safe_std(state_std)
        self.action_mean = action_mean.astype(np.float32)
        self.action_std = safe_std(action_std)

    def __len__(self):
        return int(len(self.indices))

    def __getitem__(self, idx: int):
        t = int(self.indices[idx])

        state_window = self.privileged_state[
            t - self.obs_horizon + 1 : t + 1
        ]

        action_seq = self.actions[
            t : t + self.pred_horizon
        ]

        state_window = (state_window - self.state_mean) / self.state_std
        action_seq = (action_seq - self.action_mean) / self.action_std

        return {
            "state": torch.from_numpy(state_window.astype(np.float32)),
            "action": torch.from_numpy(action_seq.astype(np.float32)),
        }


def save_checkpoint(
    path: Path,
    model: StateBCPolicy,
    optimizer: torch.optim.Optimizer,
    config: Dict,
    epoch: int,
    train_loss: float,
    val_loss: float,
):
    path.parent.mkdir(parents=True, exist_ok=True)

    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "config": config,
            "epoch": int(epoch),
            "train_loss": float(train_loss),
            "val_loss": float(val_loss),
            "best_val_loss": float(val_loss),
        },
        path,
    )


def run_epoch(
    model: StateBCPolicy,
    loader: DataLoader,
    device: torch.device,
    optimizer=None,
    grad_clip: float = 1.0,
) -> float:
    is_train = optimizer is not None
    model.train(is_train)

    total_loss = 0.0
    total_count = 0

    for batch in loader:
        state = batch["state"].to(device, non_blocking=True)
        action = batch["action"].to(device, non_blocking=True)

        pred = model(state)
        loss = F.mse_loss(pred, action)

        if is_train:
            optimizer.zero_grad(set_to_none=True)
            loss.backward()

            if grad_clip is not None and grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)

            optimizer.step()

        bs = int(state.shape[0])
        total_loss += float(loss.item()) * bs
        total_count += bs

    return total_loss / max(total_count, 1)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--zarr_path", type=str, default="data/zarr/pick_place_scripted_200.zarr")
    parser.add_argument("--output_dir", type=str, default="experiments/bc_privileged_state_v1")

    parser.add_argument("--state_mode", type=str, default="relative", choices=["simple", "relative"])
    parser.add_argument("--obs_horizon", type=int, default=2)
    parser.add_argument("--pred_horizon", type=int, default=16)

    parser.add_argument("--hidden_dim", type=int, default=256)
    parser.add_argument("--dropout", type=float, default=0.0)

    parser.add_argument("--batch_size", type=int, default=256)
    parser.add_argument("--epochs", type=int, default=150)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight_decay", type=float, default=1e-6)
    parser.add_argument("--grad_clip", type=float, default=1.0)

    parser.add_argument("--val_ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num_workers", type=int, default=4)

    args = parser.parse_args()

    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    root = zarr.open_group(args.zarr_path, mode="r")

    required_keys = [
        "data/robot_state",
        "data/action",
        "data/cube_pos",
        "data/target_pos",
        "meta/episode_ends",
    ]

    for key in required_keys:
        if key not in root:
            raise KeyError(
                f"Zarr missing {key}. "
                f"If data/cube_pos or data/target_pos is missing, "
                f"run add_privileged_to_zarr_from_hdf5.py first."
            )

    robot_state = np.asarray(root["data/robot_state"][:], dtype=np.float32)
    actions = np.asarray(root["data/action"][:], dtype=np.float32)
    cube_pos = np.asarray(root["data/cube_pos"][:], dtype=np.float32)
    target_pos = np.asarray(root["data/target_pos"][:], dtype=np.float32)
    episode_ends = np.asarray(root["meta/episode_ends"][:], dtype=np.int64)

    privileged_state = build_privileged_state_from_arrays(
        robot_state=robot_state,
        cube_pos=cube_pos,
        target_pos=target_pos,
        mode=args.state_mode,
    )

    num_episodes = int(len(episode_ends))
    all_episode_ids = np.arange(num_episodes, dtype=np.int64)
    np.random.shuffle(all_episode_ids)

    num_val = max(1, int(round(num_episodes * args.val_ratio)))
    val_episode_ids = np.sort(all_episode_ids[:num_val])
    train_episode_ids = np.sort(all_episode_ids[num_val:])

    stats = compute_stats(
        privileged_state=privileged_state,
        actions=actions,
        episode_ends=episode_ends,
        train_episode_ids=train_episode_ids,
    )

    stats.update(
        {
            "zarr_path": args.zarr_path,
            "state_mode": args.state_mode,
            "obs_horizon": int(args.obs_horizon),
            "pred_horizon": int(args.pred_horizon),
            "num_episodes": int(num_episodes),
            "train_episode_ids": train_episode_ids.astype(int).tolist(),
            "val_episode_ids": val_episode_ids.astype(int).tolist(),
        }
    )

    stats_path = output_dir / "privileged_state_stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    state_mean = np.asarray(stats["state_mean"], dtype=np.float32)
    state_std = safe_std(np.asarray(stats["state_std"], dtype=np.float32))
    action_mean = np.asarray(stats["action_mean"], dtype=np.float32)
    action_std = safe_std(np.asarray(stats["action_std"], dtype=np.float32))

    train_indices = build_sample_indices(
        episode_ends=episode_ends,
        episode_ids=train_episode_ids,
        obs_horizon=args.obs_horizon,
        pred_horizon=args.pred_horizon,
    )

    val_indices = build_sample_indices(
        episode_ends=episode_ends,
        episode_ids=val_episode_ids,
        obs_horizon=args.obs_horizon,
        pred_horizon=args.pred_horizon,
    )

    train_dataset = PrivilegedStateBCDataset(
        privileged_state=privileged_state,
        actions=actions,
        indices=train_indices,
        obs_horizon=args.obs_horizon,
        pred_horizon=args.pred_horizon,
        state_mean=state_mean,
        state_std=state_std,
        action_mean=action_mean,
        action_std=action_std,
    )

    val_dataset = PrivilegedStateBCDataset(
        privileged_state=privileged_state,
        actions=actions,
        indices=val_indices,
        obs_horizon=args.obs_horizon,
        pred_horizon=args.pred_horizon,
        state_mean=state_mean,
        state_std=state_std,
        action_mean=action_mean,
        action_std=action_std,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=True,
        drop_last=True,
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=True,
        drop_last=False,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = StateBCPolicy(
        state_dim=int(stats["state_dim"]),
        action_dim=int(stats["action_dim"]),
        obs_horizon=args.obs_horizon,
        pred_horizon=args.pred_horizon,
        hidden_dim=args.hidden_dim,
        dropout=args.dropout,
    ).to(device)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.lr,
        weight_decay=args.weight_decay,
    )

    config = {
        "policy_type": "privileged_state_bc",
        "zarr_path": args.zarr_path,
        "stats_path": str(stats_path),
        "state_mode": args.state_mode,
        "state_dim": int(stats["state_dim"]),
        "action_dim": int(stats["action_dim"]),
        "obs_horizon": int(args.obs_horizon),
        "pred_horizon": int(args.pred_horizon),
        "hidden_dim": int(args.hidden_dim),
        "dropout": float(args.dropout),
        "lr": float(args.lr),
        "weight_decay": float(args.weight_decay),
    }

    log_path = output_dir / "train_log.csv"
    best_val_loss = float("inf")

    print("=" * 100)
    print("[Privileged-state BC Training]")
    print(f"zarr_path:      {args.zarr_path}")
    print(f"output_dir:     {output_dir}")
    print(f"state_mode:     {args.state_mode}")
    print(f"state_dim:      {stats['state_dim']}")
    print(f"action_dim:     {stats['action_dim']}")
    print(f"obs_horizon:    {args.obs_horizon}")
    print(f"pred_horizon:   {args.pred_horizon}")
    print(f"train samples:  {len(train_dataset)}")
    print(f"val samples:    {len(val_dataset)}")
    print(f"parameters:     {count_parameters(model):,}")
    print(f"device:         {device}")
    print("=" * 100)

    with open(log_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["epoch", "train_loss", "val_loss", "best_val_loss"],
        )
        writer.writeheader()

        for epoch in range(1, args.epochs + 1):
            train_loss = run_epoch(
                model=model,
                loader=train_loader,
                device=device,
                optimizer=optimizer,
                grad_clip=args.grad_clip,
            )

            with torch.no_grad():
                val_loss = run_epoch(
                    model=model,
                    loader=val_loader,
                    device=device,
                    optimizer=None,
                    grad_clip=args.grad_clip,
                )

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                save_checkpoint(
                    path=output_dir / "best.pt",
                    model=model,
                    optimizer=optimizer,
                    config=config,
                    epoch=epoch,
                    train_loss=train_loss,
                    val_loss=val_loss,
                )

            save_checkpoint(
                path=output_dir / "last.pt",
                model=model,
                optimizer=optimizer,
                config=config,
                epoch=epoch,
                train_loss=train_loss,
                val_loss=val_loss,
            )

            writer.writerow(
                {
                    "epoch": epoch,
                    "train_loss": train_loss,
                    "val_loss": val_loss,
                    "best_val_loss": best_val_loss,
                }
            )
            f.flush()

            print(
                f"[epoch {epoch:04d}] "
                f"train_loss={train_loss:.6f} "
                f"val_loss={val_loss:.6f} "
                f"best={best_val_loss:.6f}"
            )

    print("=" * 100)
    print("[OK] Training complete")
    print(f"best checkpoint: {output_dir / 'best.pt'}")
    print(f"last checkpoint: {output_dir / 'last.pt'}")
    print(f"stats:           {stats_path}")
    print(f"log:             {log_path}")
    print("=" * 100)


if __name__ == "__main__":
    main()
