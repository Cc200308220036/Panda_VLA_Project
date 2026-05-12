"""
实现目标：
    统一构造 privileged-state BC 的输入向量。

输入：
    方式一：训练时从 Zarr 数组读取：
        robot_state: float32 [..., 23]
        cube_pos:    float32 [..., 3]
        target_pos:  float32 [..., 3]

    方式二：rollout 时从 MuJoCo obs 字典读取：
        obs["joint_pos"]
        obs["joint_vel"]
        obs["ee_pos"]
        obs["ee_quat"]
        obs["gripper_qpos"]
        obs["cube_pos"]
        obs["target_pos"]

输出：
    privileged_state:
        simple 模式：
            robot_state + cube_pos + target_pos
            维度 = 23 + 3 + 3 = 29

        relative 模式，默认推荐：
            robot_state
            cube_pos
            target_pos
            cube_pos - ee_pos
            target_pos - cube_pos
            target_pos - ee_pos
            维度 = 23 + 3 + 3 + 3 + 3 + 3 = 38
"""

from typing import Dict, Any

import numpy as np


EE_POS_SLICE = slice(16, 19)


def build_robot_state_from_obs(obs: Dict[str, Any]) -> np.ndarray:
    if "robot_state" in obs:
        robot_state = np.asarray(obs["robot_state"], dtype=np.float32).reshape(-1)
        if robot_state.shape[0] != 23:
            raise ValueError(f"Expected robot_state dim 23, got {robot_state.shape[0]}")
        return robot_state

    joint_pos = np.asarray(obs["joint_pos"], dtype=np.float32).reshape(-1)
    joint_vel = np.asarray(obs["joint_vel"], dtype=np.float32).reshape(-1)
    ee_pos = np.asarray(obs["ee_pos"], dtype=np.float32).reshape(-1)
    ee_quat = np.asarray(obs["ee_quat"], dtype=np.float32).reshape(-1)

    if "gripper_qpos" in obs:
        gripper_qpos = np.asarray(obs["gripper_qpos"], dtype=np.float32).reshape(-1)
    else:
        gripper_qpos = np.zeros(2, dtype=np.float32)

    robot_state = np.concatenate(
        [
            joint_pos,      # 7, indices 0:7
            joint_vel,      # 7, indices 7:14
            gripper_qpos,   # 2, indices 14:16
            ee_pos,         # 3, indices 16:19
            ee_quat,        # 4, indices 19:23
        ],
        axis=0,
    ).astype(np.float32)

    if robot_state.shape[0] != 23:
        raise ValueError(f"Expected robot_state dim 23, got {robot_state.shape[0]}")

    return robot_state


def build_privileged_state_from_arrays(
    robot_state: np.ndarray,
    cube_pos: np.ndarray,
    target_pos: np.ndarray,
    mode: str = "relative",
) -> np.ndarray:
    robot_state = np.asarray(robot_state, dtype=np.float32)
    cube_pos = np.asarray(cube_pos, dtype=np.float32)
    target_pos = np.asarray(target_pos, dtype=np.float32)

    if robot_state.shape[-1] != 23:
        raise ValueError(f"Expected robot_state last dim 23, got {robot_state.shape}")

    if cube_pos.shape[-1] != 3:
        raise ValueError(f"Expected cube_pos last dim 3, got {cube_pos.shape}")

    if target_pos.shape[-1] != 3:
        raise ValueError(f"Expected target_pos last dim 3, got {target_pos.shape}")

    ee_pos = robot_state[..., EE_POS_SLICE]

    if mode == "simple":
        state = np.concatenate(
            [
                robot_state,
                cube_pos,
                target_pos,
            ],
            axis=-1,
        )

    elif mode == "relative":
        state = np.concatenate(
            [
                robot_state,
                cube_pos,
                target_pos,
                cube_pos - ee_pos,
                target_pos - cube_pos,
                target_pos - ee_pos,
            ],
            axis=-1,
        )

    else:
        raise ValueError(f"Unsupported privileged state mode: {mode}")

    return state.astype(np.float32)


def build_privileged_state_from_obs(
    obs: Dict[str, Any],
    mode: str = "relative",
) -> np.ndarray:
    robot_state = build_robot_state_from_obs(obs)

    if "cube_pos" not in obs:
        raise KeyError(
            "obs missing cube_pos. Privileged-state rollout requires obs['cube_pos']."
        )

    if "target_pos" not in obs:
        raise KeyError(
            "obs missing target_pos. Privileged-state rollout requires obs['target_pos']."
        )

    cube_pos = np.asarray(obs["cube_pos"], dtype=np.float32).reshape(3)
    target_pos = np.asarray(obs["target_pos"], dtype=np.float32).reshape(3)

    state = build_privileged_state_from_arrays(
        robot_state=robot_state,
        cube_pos=cube_pos,
        target_pos=target_pos,
        mode=mode,
    )

    return state.reshape(-1).astype(np.float32)


def get_privileged_state_dim(mode: str = "relative") -> int:
    if mode == "simple":
        return 29
    if mode == "relative":
        return 38
    raise ValueError(f"Unsupported privileged state mode: {mode}")
