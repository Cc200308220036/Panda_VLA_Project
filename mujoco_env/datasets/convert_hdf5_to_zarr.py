import os
import sys

# ==================== 路径修复：必须在 import 自定义模块前 ====================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import glob
import json
import shutil
import argparse

import h5py
import zarr
import numpy as np
from tqdm import tqdm
from numcodecs import Blosc


def read_episode_basic_info(hdf5_path, image_key, state_key, action_key):
    with h5py.File(hdf5_path, "r") as f:
        image_shape = f[image_key].shape
        state_shape = f[state_key].shape
        action_shape = f[action_key].shape

        num_steps = int(action_shape[0])
        seed = int(f["metadata"].attrs["seed"])

        valid_demo = bool(f["metadata"].attrs.get("valid_demo", True))
        success = bool(f["metadata"].attrs.get("success", True))

        final_place_error = None
        if "metadata/final_place_error" in f:
            final_place_error = f["metadata/final_place_error"][:].astype(np.float32)

    return {
        "num_steps": num_steps,
        "seed": seed,
        "valid_demo": valid_demo,
        "success": success,
        "image_shape": image_shape,
        "state_shape": state_shape,
        "action_shape": action_shape,
        "final_place_error": final_place_error,
    }


def build_episode_list(dataset_dir, image_key, state_key, action_key, keep_failed=False):
    hdf5_paths = sorted(glob.glob(os.path.join(dataset_dir, "episode_*.hdf5")))

    if len(hdf5_paths) == 0:
        raise RuntimeError(f"No episode_*.hdf5 found in: {dataset_dir}")

    episodes = []
    skipped = []

    for path in hdf5_paths:
        info = read_episode_basic_info(
            hdf5_path=path,
            image_key=image_key,
            state_key=state_key,
            action_key=action_key,
        )

        if (not keep_failed) and (not info["valid_demo"] or not info["success"]):
            skipped.append(path)
            continue

        episodes.append(
            {
                "path": os.path.abspath(path),
                **info,
            }
        )

    if len(episodes) == 0:
        raise RuntimeError("No valid episodes found after filtering.")

    return episodes, skipped


def check_shapes(episodes):
    first = episodes[0]

    image_shape = first["image_shape"]
    state_shape = first["state_shape"]
    action_shape = first["action_shape"]

    image_frame_shape = image_shape[1:]
    state_dim = state_shape[1]
    action_dim = action_shape[1]

    for ep in episodes:
        if ep["image_shape"][1:] != image_frame_shape:
            raise ValueError(
                f"Image shape mismatch:\n"
                f"first={image_frame_shape}, current={ep['image_shape'][1:]}, path={ep['path']}"
            )

        if ep["state_shape"][1] != state_dim:
            raise ValueError(
                f"State dim mismatch:\n"
                f"first={state_dim}, current={ep['state_shape'][1]}, path={ep['path']}"
            )

        if ep["action_shape"][1] != action_dim:
            raise ValueError(
                f"Action dim mismatch:\n"
                f"first={action_dim}, current={ep['action_shape'][1]}, path={ep['path']}"
            )

        if ep["image_shape"][0] != ep["num_steps"]:
            raise ValueError(
                f"Image T != action T in {ep['path']}: "
                f"image_T={ep['image_shape'][0]}, action_T={ep['num_steps']}"
            )

        if ep["state_shape"][0] != ep["num_steps"]:
            raise ValueError(
                f"State T != action T in {ep['path']}: "
                f"state_T={ep['state_shape'][0]}, action_T={ep['num_steps']}"
            )

    return {
        "image_frame_shape": tuple(image_frame_shape),
        "state_dim": int(state_dim),
        "action_dim": int(action_dim),
    }


def create_zarr_arrays(
    output_zarr,
    total_steps,
    num_episodes,
    image_frame_shape,
    state_dim,
    action_dim,
    image_chunk,
    state_chunk,
    action_chunk,
):
    if os.path.exists(output_zarr):
        raise FileExistsError(
            f"Output zarr already exists: {output_zarr}\n"
            f"Use --overwrite if you want to replace it."
        )

    root = zarr.open_group(output_zarr, mode="w")

    data_group = root.create_group("data")
    meta_group = root.create_group("meta")

    compressor = Blosc(cname="zstd", clevel=3, shuffle=Blosc.BITSHUFFLE)

    h, w, c = image_frame_shape

    image_ds = data_group.create_dataset(
        "image",
        shape=(total_steps, h, w, c),
        chunks=(image_chunk, h, w, c),
        dtype=np.uint8,
        compressor=compressor,
    )

    state_ds = data_group.create_dataset(
        "robot_state",
        shape=(total_steps, state_dim),
        chunks=(state_chunk, state_dim),
        dtype=np.float32,
        compressor=compressor,
    )

    action_ds = data_group.create_dataset(
        "action",
        shape=(total_steps, action_dim),
        chunks=(action_chunk, action_dim),
        dtype=np.float32,
        compressor=compressor,
    )

    episode_id_ds = data_group.create_dataset(
        "episode_id",
        shape=(total_steps,),
        chunks=(max(image_chunk, 1024),),
        dtype=np.int32,
        compressor=compressor,
    )

    timestep_ds = data_group.create_dataset(
        "timestep",
        shape=(total_steps,),
        chunks=(max(image_chunk, 1024),),
        dtype=np.int32,
        compressor=compressor,
    )

    episode_ends_ds = meta_group.create_dataset(
        "episode_ends",
        shape=(num_episodes,),
        chunks=(min(num_episodes, 1024),),
        dtype=np.int64,
        compressor=compressor,
    )

    episode_lengths_ds = meta_group.create_dataset(
        "episode_lengths",
        shape=(num_episodes,),
        chunks=(min(num_episodes, 1024),),
        dtype=np.int32,
        compressor=compressor,
    )

    seeds_ds = meta_group.create_dataset(
        "seeds",
        shape=(num_episodes,),
        chunks=(min(num_episodes, 1024),),
        dtype=np.int32,
        compressor=compressor,
    )

    return root, {
        "image": image_ds,
        "robot_state": state_ds,
        "action": action_ds,
        "episode_id": episode_id_ds,
        "timestep": timestep_ds,
        "episode_ends": episode_ends_ds,
        "episode_lengths": episode_lengths_ds,
        "seeds": seeds_ds,
    }


def convert_hdf5_to_zarr(
    dataset_dir,
    output_zarr,
    image_key="observations/images/top",
    state_key="observations/robot_state",
    action_key="actions",
    keep_failed=False,
    overwrite=False,
    image_chunk=256,
    state_chunk=4096,
    action_chunk=4096,
):
    if os.path.exists(output_zarr):
        if overwrite:
            print(f"[INFO] Removing existing zarr: {output_zarr}")
            shutil.rmtree(output_zarr)
        else:
            raise FileExistsError(
                f"Output zarr already exists: {output_zarr}\n"
                f"Pass --overwrite to replace it."
            )

    episodes, skipped = build_episode_list(
        dataset_dir=dataset_dir,
        image_key=image_key,
        state_key=state_key,
        action_key=action_key,
        keep_failed=keep_failed,
    )

    shape_info = check_shapes(episodes)

    total_steps = int(sum(ep["num_steps"] for ep in episodes))
    num_episodes = int(len(episodes))

    print("=" * 100)
    print("[INFO] HDF5 -> Zarr conversion")
    print(f"dataset_dir: {dataset_dir}")
    print(f"output_zarr: {output_zarr}")
    print(f"num_episodes: {num_episodes}")
    print(f"skipped_failed: {len(skipped)}")
    print(f"total_steps: {total_steps}")
    print(f"image_frame_shape: {shape_info['image_frame_shape']}")
    print(f"state_dim: {shape_info['state_dim']}")
    print(f"action_dim: {shape_info['action_dim']}")
    print("=" * 100)

    root, arrays = create_zarr_arrays(
        output_zarr=output_zarr,
        total_steps=total_steps,
        num_episodes=num_episodes,
        image_frame_shape=shape_info["image_frame_shape"],
        state_dim=shape_info["state_dim"],
        action_dim=shape_info["action_dim"],
        image_chunk=image_chunk,
        state_chunk=state_chunk,
        action_chunk=action_chunk,
    )

    episode_infos = []
    cursor = 0

    for episode_id, ep in enumerate(tqdm(episodes, desc="Converting episodes")):
        path = ep["path"]
        t = ep["num_steps"]
        start = cursor
        end = cursor + t

        with h5py.File(path, "r") as f:
            images = f[image_key][:]
            states = f[state_key][:]
            actions = f[action_key][:]

            arrays["image"][start:end] = images.astype(np.uint8)
            arrays["robot_state"][start:end] = states.astype(np.float32)
            arrays["action"][start:end] = actions.astype(np.float32)

            arrays["episode_id"][start:end] = episode_id
            arrays["timestep"][start:end] = np.arange(t, dtype=np.int32)

            arrays["episode_ends"][episode_id] = end
            arrays["episode_lengths"][episode_id] = t
            arrays["seeds"][episode_id] = ep["seed"]

            final_place_error = None
            if "metadata/final_place_error" in f:
                final_place_error = f["metadata/final_place_error"][:].astype(np.float32).tolist()

        episode_infos.append(
            {
                "episode_id": int(episode_id),
                "source_path": path,
                "start": int(start),
                "end": int(end),
                "num_steps": int(t),
                "seed": int(ep["seed"]),
                "valid_demo": bool(ep["valid_demo"]),
                "success": bool(ep["success"]),
                "final_place_error": final_place_error,
            }
        )

        cursor = end

    # Zarr attrs 保存元信息
    root.attrs["dataset_dir"] = os.path.abspath(dataset_dir)
    root.attrs["output_zarr"] = os.path.abspath(output_zarr)
    root.attrs["num_episodes"] = num_episodes
    root.attrs["total_steps"] = total_steps
    root.attrs["image_key"] = "data/image"
    root.attrs["state_key"] = "data/robot_state"
    root.attrs["action_key"] = "data/action"
    root.attrs["episode_ends_key"] = "meta/episode_ends"
    root.attrs["image_frame_shape"] = list(shape_info["image_frame_shape"])
    root.attrs["state_dim"] = shape_info["state_dim"]
    root.attrs["action_dim"] = shape_info["action_dim"]
    root.attrs["source_image_key"] = image_key
    root.attrs["source_state_key"] = state_key
    root.attrs["source_action_key"] = action_key

    # 额外保存一个 JSON，方便不用 zarr 也能快速查看
    meta_json = {
        "dataset_dir": os.path.abspath(dataset_dir),
        "output_zarr": os.path.abspath(output_zarr),
        "num_episodes": num_episodes,
        "total_steps": total_steps,
        "image_key": "data/image",
        "state_key": "data/robot_state",
        "action_key": "data/action",
        "episode_ends_key": "meta/episode_ends",
        "image_frame_shape": list(shape_info["image_frame_shape"]),
        "state_dim": shape_info["state_dim"],
        "action_dim": shape_info["action_dim"],
        "episodes": episode_infos,
        "skipped": skipped,
    }

    meta_json_path = output_zarr.rstrip("/") + "_metadata.json"
    with open(meta_json_path, "w", encoding="utf-8") as f:
        json.dump(meta_json, f, indent=2)

    print("=" * 100)
    print("[OK] Conversion complete")
    print(f"Zarr saved to: {output_zarr}")
    print(f"Metadata JSON saved to: {meta_json_path}")
    print(f"num_episodes: {num_episodes}")
    print(f"total_steps: {total_steps}")
    print("=" * 100)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset_dir",
        type=str,
        default="data/pick_place_scripted_200",
        help="Directory containing episode_*.hdf5 files.",
    )
    parser.add_argument(
        "--output_zarr",
        type=str,
        default="data/pick_place_scripted_200.zarr",
        help="Output zarr directory.",
    )
    parser.add_argument("--image_key", type=str, default="observations/images/top")
    parser.add_argument("--state_key", type=str, default="observations/robot_state")
    parser.add_argument("--action_key", type=str, default="actions")
    parser.add_argument("--keep_failed", action="store_true")
    parser.add_argument("--overwrite", action="store_true")

    parser.add_argument("--image_chunk", type=int, default=256)
    parser.add_argument("--state_chunk", type=int, default=4096)
    parser.add_argument("--action_chunk", type=int, default=4096)

    args = parser.parse_args()

    convert_hdf5_to_zarr(
        dataset_dir=args.dataset_dir,
        output_zarr=args.output_zarr,
        image_key=args.image_key,
        state_key=args.state_key,
        action_key=args.action_key,
        keep_failed=args.keep_failed,
        overwrite=args.overwrite,
        image_chunk=args.image_chunk,
        state_chunk=args.state_chunk,
        action_chunk=args.action_chunk,
    )


if __name__ == "__main__":
    main()
