"""
实现目标：
    从原始 HDF5 episode 文件中读取 privileged/cube_pos 和 privileged/target_pos，
    并补充写入已经存在的 Zarr 数据集。

输入：
    --hdf5_dir:
        原始 HDF5 episode 目录，例如：
        data/raw/pick_place_scripted_200

    --zarr_path:
        已经转换好的 Zarr 数据集，例如：
        data/zarr/pick_place_scripted_200.zarr

    --cube_key:
        HDF5 中 cube 位置路径，默认：
        privileged/cube_pos

    --target_key:
        HDF5 中 target 位置路径，默认：
        privileged/target_pos

输出：
    在 Zarr 中新增或覆盖：
        data/cube_pos      float32 [N, 3]
        data/target_pos    float32 [N, 3]

    其中 N 是所有 episode 拼接后的总 timestep。
"""

import argparse
import glob
import os

import h5py
import numpy as np
import zarr
from numcodecs import Blosc
from tqdm import tqdm


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hdf5_dir", type=str, default="data/raw/pick_place_scripted_200")
    parser.add_argument("--zarr_path", type=str, default="data/zarr/pick_place_scripted_200.zarr")
    parser.add_argument("--cube_key", type=str, default="privileged/cube_pos")
    parser.add_argument("--target_key", type=str, default="privileged/target_pos")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    hdf5_paths = sorted(glob.glob(os.path.join(args.hdf5_dir, "episode_*.hdf5")))
    if len(hdf5_paths) == 0:
        raise FileNotFoundError(f"No episode_*.hdf5 found in {args.hdf5_dir}")

    root = zarr.open_group(args.zarr_path, mode="a")

    if "meta/episode_ends" not in root:
        raise KeyError("Zarr missing meta/episode_ends")

    episode_ends = np.asarray(root["meta/episode_ends"][:], dtype=np.int64)
    total_steps = int(episode_ends[-1])
    num_episodes = int(len(episode_ends))

    if len(hdf5_paths) != num_episodes:
        raise ValueError(
            f"HDF5 episode count != Zarr episode count: "
            f"{len(hdf5_paths)} vs {num_episodes}"
        )

    data_group = root["data"]

    for name in ["cube_pos", "target_pos"]:
        if name in data_group:
            if args.overwrite:
                del data_group[name]
            else:
                raise FileExistsError(
                    f"data/{name} already exists. Pass --overwrite to replace it."
                )

    compressor = Blosc(cname="zstd", clevel=3, shuffle=Blosc.BITSHUFFLE)

    cube_ds = data_group.create_dataset(
        "cube_pos",
        shape=(total_steps, 3),
        chunks=(4096, 3),
        dtype=np.float32,
        compressor=compressor,
    )

    target_ds = data_group.create_dataset(
        "target_pos",
        shape=(total_steps, 3),
        chunks=(4096, 3),
        dtype=np.float32,
        compressor=compressor,
    )

    cursor = 0

    for ep_id, path in enumerate(tqdm(hdf5_paths, desc="Adding privileged state")):
        start = 0 if ep_id == 0 else int(episode_ends[ep_id - 1])
        end = int(episode_ends[ep_id])
        expected_t = end - start

        with h5py.File(path, "r") as f:
            if args.cube_key not in f:
                raise KeyError(f"{path} missing {args.cube_key}")
            if args.target_key not in f:
                raise KeyError(f"{path} missing {args.target_key}")

            cube_pos = np.asarray(f[args.cube_key][:], dtype=np.float32)
            target_pos = np.asarray(f[args.target_key][:], dtype=np.float32)

        if cube_pos.shape != (expected_t, 3):
            raise ValueError(
                f"cube_pos shape mismatch in {path}: "
                f"got {cube_pos.shape}, expected {(expected_t, 3)}"
            )

        if target_pos.shape != (expected_t, 3):
            raise ValueError(
                f"target_pos shape mismatch in {path}: "
                f"got {target_pos.shape}, expected {(expected_t, 3)}"
            )

        cube_ds[start:end] = cube_pos
        target_ds[start:end] = target_pos
        cursor = end

    root.attrs["cube_pos_key"] = "data/cube_pos"
    root.attrs["target_pos_key"] = "data/target_pos"

    print("=" * 80)
    print("[OK] Added privileged state to Zarr")
    print(f"zarr_path: {args.zarr_path}")
    print(f"cube_pos: data/cube_pos {cube_ds.shape}")
    print(f"target_pos: data/target_pos {target_ds.shape}")
    print("=" * 80)


if __name__ == "__main__":
    main()
