import argparse
import h5py
import numpy as np


def print_dataset(name, obj):
    """
    h5py visititems callback.
    打印 HDF5 内部所有 group / dataset 的结构。
    """
    if isinstance(obj, h5py.Dataset):
        print(f"{name}: shape={obj.shape}, dtype={obj.dtype}")
    elif isinstance(obj, h5py.Group):
        print(f"{name}/")


def decode_stage_array(stage_array, max_items=20):
    """
    HDF5 里 stage 通常保存为 bytes，需要 decode 成字符串。
    """
    stages = []
    for x in stage_array[:max_items]:
        if isinstance(x, bytes):
            stages.append(x.decode("utf-8"))
        else:
            stages.append(str(x))
    return stages


def inspect_episode(path, show_stages=True, max_stage_items=30):
    with h5py.File(path, "r") as f:
        print("=" * 100)
        print(f"HDF5 file: {path}")
        print("=" * 100)

        print("\n[1] File tree")
        print("-" * 100)
        f.visititems(print_dataset)

        print("\n[2] Metadata attributes")
        print("-" * 100)

        if "metadata" not in f:
            print("[ERROR] No metadata group found.")
        else:
            for key, value in f["metadata"].attrs.items():
                print(f"{key}: {value}")

        print("\n[3] Core training keys")
        print("-" * 100)

        required_keys = [
            "observations/images/top",
            "observations/robot_state",
            "actions",
        ]

        optional_debug_keys = [
            "ctrls",
            "observations/joint_pos",
            "observations/joint_vel",
            "observations/gripper_qpos",
            "observations/ee_pos",
            "observations/ee_quat",
            "privileged/cube_pos",
            "privileged/target_pos",
            "privileged/stage",
        ]

        for key in required_keys:
            if key in f:
                print(f"[OK] {key}: shape={f[key].shape}, dtype={f[key].dtype}")
            else:
                print(f"[MISSING] {key}")

        print("\n[4] Optional debug keys")
        print("-" * 100)

        for key in optional_debug_keys:
            if key in f:
                print(f"[OK] {key}: shape={f[key].shape}, dtype={f[key].dtype}")
            else:
                print(f"[MISSING] {key}")

        print("\n[5] Shape consistency check")
        print("-" * 100)

        lengths = {}

        keys_to_check = [
            "observations/images/top",
            "observations/robot_state",
            "observations/joint_pos",
            "observations/joint_vel",
            "observations/gripper_qpos",
            "observations/ee_pos",
            "observations/ee_quat",
            "actions",
            "ctrls",
            "privileged/cube_pos",
            "privileged/target_pos",
            "privileged/stage",
        ]

        for key in keys_to_check:
            if key in f:
                lengths[key] = f[key].shape[0]

        for key, length in lengths.items():
            print(f"{key}: T={length}")

        unique_lengths = sorted(set(lengths.values()))

        if len(unique_lengths) == 1:
            print(f"[OK] All time-series lengths match: T={unique_lengths[0]}")
        else:
            print(f"[WARNING] Time-series lengths differ: {unique_lengths}")

        print("\n[6] Value sanity check")
        print("-" * 100)

        if "actions" in f:
            actions = f["actions"][:]
            print(f"actions min: {actions.min(axis=0)}")
            print(f"actions max: {actions.max(axis=0)}")
            print(f"actions mean: {actions.mean(axis=0)}")
            print(f"actions std: {actions.std(axis=0)}")

            if np.isnan(actions).any():
                print("[ERROR] actions contain NaN")
            else:
                print("[OK] actions contain no NaN")

        if "observations/robot_state" in f:
            robot_state = f["observations/robot_state"][:]
            print(f"robot_state shape: {robot_state.shape}")
            print(f"robot_state min first 10: {robot_state.min(axis=0)[:10]}")
            print(f"robot_state max first 10: {robot_state.max(axis=0)[:10]}")

            if np.isnan(robot_state).any():
                print("[ERROR] robot_state contains NaN")
            else:
                print("[OK] robot_state contains no NaN")

        if "observations/images/top" in f:
            images = f["observations/images/top"]
            print(f"image shape: {images.shape}")
            print(f"image dtype: {images.dtype}")
            print(f"image min/max first frame: {images[0].min()} / {images[0].max()}")

            if images.dtype == np.uint8:
                print("[OK] image dtype is uint8")
            else:
                print("[WARNING] image dtype is not uint8")

        print("\n[7] Task final state")
        print("-" * 100)

        metadata_keys = [
            "initial_cube",
            "initial_target",
            "final_cube",
            "final_target",
            "final_place_error",
        ]

        for key in metadata_keys:
            full_key = f"metadata/{key}"
            if full_key in f:
                print(f"{key}: {f[full_key][:]}")
            else:
                print(f"[MISSING] {full_key}")

        if "metadata/final_place_error" in f:
            err = f["metadata/final_place_error"][:]
            print(f"final_place_error_norm: {np.linalg.norm(err):.6f}")

        print("\n[8] Stage preview")
        print("-" * 100)

        if show_stages and "privileged/stage" in f:
            stage_array = f["privileged/stage"][:]
            stage_preview = decode_stage_array(stage_array, max_items=max_stage_items)

            print(f"num_stages_saved: {len(stage_array)}")
            print(f"first {max_stage_items} stages:")
            for i, s in enumerate(stage_preview):
                print(f"  t={i:03d}: {s}")

            unique_stages = []
            for x in stage_array:
                s = x.decode("utf-8") if isinstance(x, bytes) else str(x)
                if len(unique_stages) == 0 or unique_stages[-1] != s:
                    unique_stages.append(s)

            print("\nstage transitions:")
            for s in unique_stages:
                print(f"  {s}")

        print("\n[9] Summary")
        print("-" * 100)

        success = None
        valid_demo = None
        num_steps = None

        if "metadata" in f:
            if "success" in f["metadata"].attrs:
                success = bool(f["metadata"].attrs["success"])
            if "valid_demo" in f["metadata"].attrs:
                valid_demo = bool(f["metadata"].attrs["valid_demo"])
            if "num_steps" in f["metadata"].attrs:
                num_steps = int(f["metadata"].attrs["num_steps"])

        print(f"success: {success}")
        print(f"valid_demo: {valid_demo}")
        print(f"num_steps: {num_steps}")

        if success and valid_demo:
            print("[OK] This episode looks valid.")
        else:
            print("[WARNING] This episode may not be valid.")

        print("=" * 100)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", type=str, required=True)
    parser.add_argument("--no_stages", action="store_true")
    parser.add_argument("--max_stage_items", type=int, default=30)
    args = parser.parse_args()

    inspect_episode(
        path=args.episode,
        show_stages=not args.no_stages,
        max_stage_items=args.max_stage_items,
    )


if __name__ == "__main__":
    main()
