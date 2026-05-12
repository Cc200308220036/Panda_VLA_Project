"""
实现目标：
    训练 state-only Behavior Cloning baseline。
    该脚本用于验证：
        1. ZarrDataset 采样是否正确；
        2. robot_state normalization 是否正确；
        3. action normalization 是否正确；
        4. 模型输入输出维度是否正确；
        5. train loss / val loss 是否能稳定下降；
        6. checkpoint、config、train_log 是否能正确保存。

输入：
    --zarr_path:
        Zarr 数据集路径。
        默认：
            data/zarr/pick_place_scripted_200.zarr

    --stats_path:
        Zarr 统计量 JSON 路径。
        默认：
            data/metadata/pick_place_scripted_200.zarr_stats.json

    Dataset 每个样本：
        state:
            torch.FloatTensor
            shape = [obs_horizon, state_dim]

        action:
            torch.FloatTensor
            shape = [pred_horizon, action_dim]

输出：
    --output_dir:
        训练结果保存目录。
        默认：
            experiments/bc_state_v1

    输出文件：
        config.json:
            本次训练配置

        train_log.csv:
            每个 epoch 的 train_loss、val_loss、学习率和耗时

        best.pt:
            val_loss 最低的 checkpoint

        last.pt:
            最后一个 epoch 的 checkpoint

说明：
    当前训练的是 state-only BC，不使用图像、不使用语言。
    这是 Diffusion Policy 之前的最小监督学习检查。
"""

import argparse
import csv
import json
import random
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from learning.datasets.zarr_dataset import ZarrSequenceDataset
from learning.diffusion_policy.model import StateBCPolicy, count_parameters


def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def run_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer,
    device: torch.device,
    train: bool,
    grad_clip: float,
):
    if train:
        model.train()
    else:
        model.eval()

    loss_fn = nn.MSELoss()

    total_loss = 0.0
    total_count = 0

    for batch in loader:
        state = batch["state"].to(device, non_blocking=True)
        action = batch["action"].to(device, non_blocking=True)

        if train:
            optimizer.zero_grad(set_to_none=True)

        with torch.set_grad_enabled(train):
            pred_action = model(state)

            if pred_action.shape != action.shape:
                raise RuntimeError(
                    f"Prediction shape mismatch. "
                    f"pred_action={tuple(pred_action.shape)}, "
                    f"target_action={tuple(action.shape)}"
                )

            loss = loss_fn(pred_action, action)

            if train:
                loss.backward()

                if grad_clip is not None and grad_clip > 0:
                    nn.utils.clip_grad_norm_(model.parameters(), grad_clip)

                optimizer.step()

        batch_size = state.shape[0]
        total_loss += float(loss.item()) * batch_size
        total_count += batch_size

    return total_loss / max(total_count, 1)


def save_checkpoint(
    path: Path,
    model: nn.Module,
    optimizer,
    epoch: int,
    config: dict,
    train_loss: float,
    val_loss: float,
):
    checkpoint = {
        "format_version": "bc_state_v1",
        "epoch": int(epoch),
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "config": config,
        "train_loss": float(train_loss),
        "val_loss": float(val_loss),
    }

    torch.save(checkpoint, path)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--zarr_path",
        type=str,
        default="data/zarr/pick_place_scripted_200.zarr",
    )
    parser.add_argument(
        "--stats_path",
        type=str,
        default="data/metadata/pick_place_scripted_200.zarr_stats.json",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="experiments/bc_state_v1",
    )

    parser.add_argument("--obs_horizon", type=int, default=2)
    parser.add_argument("--pred_horizon", type=int, default=16)

    parser.add_argument("--hidden_dim", type=int, default=256)
    parser.add_argument("--dropout", type=float, default=0.0)

    parser.add_argument("--batch_size", type=int, default=256)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight_decay", type=float, default=1e-6)
    parser.add_argument("--grad_clip", type=float, default=1.0)

    parser.add_argument("--num_workers", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", type=str, default="auto")

    args = parser.parse_args()

    set_seed(args.seed)

    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    train_dataset = ZarrSequenceDataset(
        zarr_path=args.zarr_path,
        stats_path=args.stats_path,
        split="train",
        obs_horizon=args.obs_horizon,
        pred_horizon=args.pred_horizon,
        include_image=False,
        normalize=True,
    )

    val_dataset = ZarrSequenceDataset(
        zarr_path=args.zarr_path,
        stats_path=args.stats_path,
        split="val",
        obs_horizon=args.obs_horizon,
        pred_horizon=args.pred_horizon,
        include_image=False,
        normalize=True,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        drop_last=False,
        pin_memory=(device.type == "cuda"),
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        drop_last=False,
        pin_memory=(device.type == "cuda"),
    )

    model = StateBCPolicy(
        state_dim=train_dataset.state_dim,
        action_dim=train_dataset.action_dim,
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

    config = vars(args).copy()
    config.update(
        {
            "device": str(device),
            "state_dim": int(train_dataset.state_dim),
            "action_dim": int(train_dataset.action_dim),
            "num_train_samples": int(len(train_dataset)),
            "num_val_samples": int(len(val_dataset)),
            "model_name": "StateBCPolicy",
            "num_parameters": int(count_parameters(model)),
        }
    )

    config_path = output_dir / "config.json"
    log_path = output_dir / "train_log.csv"
    best_path = output_dir / "best.pt"
    last_path = output_dir / "last.pt"

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print("=" * 100)
    print("[State-only BC Training]")
    print(f"zarr_path:       {args.zarr_path}")
    print(f"stats_path:      {args.stats_path}")
    print(f"output_dir:      {args.output_dir}")
    print(f"device:          {device}")
    print(f"state_dim:       {train_dataset.state_dim}")
    print(f"action_dim:      {train_dataset.action_dim}")
    print(f"obs_horizon:     {args.obs_horizon}")
    print(f"pred_horizon:    {args.pred_horizon}")
    print(f"train samples:   {len(train_dataset)}")
    print(f"val samples:     {len(val_dataset)}")
    print(f"parameters:      {count_parameters(model)}")
    print("=" * 100)

    best_val_loss = float("inf")

    with open(log_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "epoch",
                "train_loss",
                "val_loss",
                "lr",
                "time_sec",
            ],
        )
        writer.writeheader()

        for epoch in range(1, args.epochs + 1):
            t0 = time.time()

            train_loss = run_one_epoch(
                model=model,
                loader=train_loader,
                optimizer=optimizer,
                device=device,
                train=True,
                grad_clip=args.grad_clip,
            )

            val_loss = run_one_epoch(
                model=model,
                loader=val_loader,
                optimizer=optimizer,
                device=device,
                train=False,
                grad_clip=args.grad_clip,
            )

            elapsed = time.time() - t0
            lr = optimizer.param_groups[0]["lr"]

            writer.writerow(
                {
                    "epoch": epoch,
                    "train_loss": train_loss,
                    "val_loss": val_loss,
                    "lr": lr,
                    "time_sec": elapsed,
                }
            )
            f.flush()

            print(
                f"epoch {epoch:04d} | "
                f"train_loss={train_loss:.6f} | "
                f"val_loss={val_loss:.6f} | "
                f"lr={lr:.2e} | "
                f"time={elapsed:.1f}s"
            )

            save_checkpoint(
                path=last_path,
                model=model,
                optimizer=optimizer,
                epoch=epoch,
                config=config,
                train_loss=train_loss,
                val_loss=val_loss,
            )

            if val_loss < best_val_loss:
                best_val_loss = val_loss

                save_checkpoint(
                    path=best_path,
                    model=model,
                    optimizer=optimizer,
                    epoch=epoch,
                    config=config,
                    train_loss=train_loss,
                    val_loss=val_loss,
                )

                print(f"  [OK] saved best checkpoint: {best_path}")

    print("=" * 100)
    print("[DONE]")
    print(f"best_val_loss: {best_val_loss:.6f}")
    print(f"best.pt:       {best_path}")
    print(f"last.pt:       {last_path}")
    print(f"log:           {log_path}")
    print("=" * 100)


if __name__ == "__main__":
    main()
