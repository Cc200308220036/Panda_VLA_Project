"""
实现目的：
    实现 PyTorch Dataset，从 Zarr 数据集中按时间窗口读取机器人模仿学习样本。
    该 Dataset 先服务于 state-only BC，后续也可以扩展给 image+state BC 和 Diffusion Policy 使用。

输入：
    zarr_path:
        Zarr 数据路径，例如 data/pick_place_scripted_200.zarr

    stats_path:
        compute_zarr_stats.py 生成的统计量 JSON 文件，
        例如 data/pick_place_scripted_200.zarr_stats.json

    split:
        "train" 或 "val"

    obs_horizon:
        模型观察最近多少步 state/image，例如 2

    pred_horizon:
        模型预测未来多少步 action，例如 16

    include_image:
        是否读取图像。
        state-only BC 阶段请设为 False。

输出：
    每个 sample 是一个字典：
        state:
            torch.FloatTensor, shape = [obs_horizon, state_dim]

        action:
            torch.FloatTensor, shape = [pred_horizon, action_dim]

        如果 include_image=True，还会输出：
        image:
            torch.FloatTensor, shape = [obs_horizon, 3, H, W]

        episode_id:
            int64 tensor

        timestep:
            int64 tensor，表示当前 sample 的 action 起点时间
"""

import os
import json
import argparse

import zarr
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader


class ZarrSequenceDataset(Dataset):
    def __init__(
        self,
        zarr_path: str,
        stats_path: str,
        split: str = "train",
        obs_horizon: int = 2,
        pred_horizon: int = 16,
        include_image: bool = False,
        normalize: bool = True,
    ):
        assert split in ["train", "val", "all"]
        assert obs_horizon >= 1
        assert pred_horizon >= 1

        self.zarr_path = zarr_path
        self.stats_path = stats_path
        self.split = split
        self.obs_horizon = int(obs_horizon)
        self.pred_horizon = int(pred_horizon)
        self.include_image = bool(include_image)
        self.normalize = bool(normalize)

        with open(stats_path, "r", encoding="utf-8") as f:
            self.stats = json.load(f)

        self.state_mean = np.asarray(self.stats["state_mean"], dtype=np.float32)
        self.state_std = np.asarray(self.stats["state_std"], dtype=np.float32)
        self.action_mean = np.asarray(self.stats["action_mean"], dtype=np.float32)
        self.action_std = np.asarray(self.stats["action_std"], dtype=np.float32)

        self.state_dim = int(self.stats["state_dim"])
        self.action_dim = int(self.stats["action_dim"])

        if split == "train":
            self.episode_ids = list(map(int, self.stats["train_episode_indices"]))
        elif split == "val":
            self.episode_ids = list(map(int, self.stats["val_episode_indices"]))
        else:
            self.episode_ids = list(range(int(self.stats["num_episodes"])))

        self.episode_ends = np.asarray(self.stats["episode_ends"], dtype=np.int64)

        self.indices = self._build_indices()

        self.root = None
        self.images = None
        self.states = None
        self.actions = None

    def _open_zarr(self):
        """
        DataLoader 多进程时，每个 worker 内部自己打开 Zarr。
        """
        if self.root is None:
            self.root = zarr.open_group(self.zarr_path, mode="r")
            self.states = self.root["data/robot_state"]
            self.actions = self.root["data/action"]
            if self.include_image:
                self.images = self.root["data/image"]

    def __getstate__(self):
        """
        防止 DataLoader 多进程 pickle 时携带已经打开的 Zarr 对象。
        """
        state = self.__dict__.copy()
        state["root"] = None
        state["images"] = None
        state["states"] = None
        state["actions"] = None
        return state

    def _episode_start_end(self, episode_id: int):
        start = 0 if episode_id == 0 else int(self.episode_ends[episode_id - 1])
        end = int(self.episode_ends[episode_id])
        return start, end

    def _build_indices(self):
        """
        构造所有可训练样本的索引。

        对每个时间点 t：
            state 使用：
                [t - obs_horizon + 1, ..., t]

            action 使用：
                [t, ..., t + pred_horizon - 1]

        为避免跨 episode，t 的范围必须满足：
            t - obs_horizon + 1 >= episode_start
            t + pred_horizon <= episode_end
        """
        indices = []

        for ep_id in self.episode_ids:
            ep_start, ep_end = self._episode_start_end(ep_id)
            ep_len = ep_end - ep_start

            min_required_len = self.obs_horizon + self.pred_horizon - 1
            if ep_len < min_required_len:
                continue

            t_min = ep_start + self.obs_horizon - 1
            t_max = ep_end - self.pred_horizon

            for t in range(t_min, t_max + 1):
                state_start = t - self.obs_horizon + 1
                state_end = t + 1
                action_start = t
                action_end = t + self.pred_horizon

                indices.append(
                    {
                        "episode_id": int(ep_id),
                        "timestep": int(t - ep_start),
                        "state_start": int(state_start),
                        "state_end": int(state_end),
                        "action_start": int(action_start),
                        "action_end": int(action_end),
                    }
                )

        if len(indices) == 0:
            raise RuntimeError(
                f"No valid samples for split={self.split}. "
                f"Please check obs_horizon={self.obs_horizon}, "
                f"pred_horizon={self.pred_horizon}."
            )

        return indices

    def __len__(self):
        return len(self.indices)

    def _normalize_state(self, state: np.ndarray) -> np.ndarray:
        return (state - self.state_mean) / self.state_std

    def _normalize_action(self, action: np.ndarray) -> np.ndarray:
        return (action - self.action_mean) / self.action_std

    def unnormalize_action(self, action_norm: np.ndarray) -> np.ndarray:
        return action_norm * self.action_std + self.action_mean

    def __getitem__(self, idx):
        self._open_zarr()

        item = self.indices[idx]

        state = np.asarray(
            self.states[item["state_start"]:item["state_end"]],
            dtype=np.float32,
        )

        action = np.asarray(
            self.actions[item["action_start"]:item["action_end"]],
            dtype=np.float32,
        )

        if self.normalize:
            state = self._normalize_state(state)
            action = self._normalize_action(action)

        sample = {
            "state": torch.from_numpy(state).float(),
            "action": torch.from_numpy(action).float(),
            "episode_id": torch.tensor(item["episode_id"], dtype=torch.long),
            "timestep": torch.tensor(item["timestep"], dtype=torch.long),
        }

        if self.include_image:
            image = np.asarray(
                self.images[item["state_start"]:item["state_end"]],
                dtype=np.uint8,
            )

            # [T, H, W, 3] uint8 -> [T, 3, H, W] float32, range [0, 1]
            image = image.astype(np.float32) / 255.0
            image = np.transpose(image, (0, 3, 1, 2))

            sample["image"] = torch.from_numpy(image).float()

        return sample


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--zarr_path",
        type=str,
        default="data/pick_place_scripted_200.zarr",
    )
    parser.add_argument(
        "--stats_path",
        type=str,
        default="data/pick_place_scripted_200.zarr_stats.json",
    )
    parser.add_argument("--split", type=str, default="train")
    parser.add_argument("--obs_horizon", type=int, default=2)
    parser.add_argument("--pred_horizon", type=int, default=16)
    parser.add_argument("--include_image", action="store_true")
    parser.add_argument("--batch_size", type=int, default=4)
    args = parser.parse_args()

    dataset = ZarrSequenceDataset(
        zarr_path=args.zarr_path,
        stats_path=args.stats_path,
        split=args.split,
        obs_horizon=args.obs_horizon,
        pred_horizon=args.pred_horizon,
        include_image=args.include_image,
        normalize=True,
    )

    print("=" * 100)
    print("[OK] Dataset created")
    print(f"split:        {args.split}")
    print(f"num samples:  {len(dataset)}")
    print(f"state_dim:    {dataset.state_dim}")
    print(f"action_dim:   {dataset.action_dim}")
    print(f"obs_horizon:  {dataset.obs_horizon}")
    print(f"pred_horizon: {dataset.pred_horizon}")

    sample = dataset[0]
    print("-" * 100)
    print("single sample:")
    for k, v in sample.items():
        if torch.is_tensor(v):
            print(k, tuple(v.shape), v.dtype)
        else:
            print(k, v)

    loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=0,
        drop_last=True,
    )

    batch = next(iter(loader))
    print("-" * 100)
    print("one batch:")
    for k, v in batch.items():
        if torch.is_tensor(v):
            print(k, tuple(v.shape), v.dtype)
        else:
            print(k, v)

    print("=" * 100)


if __name__ == "__main__":
    main()
