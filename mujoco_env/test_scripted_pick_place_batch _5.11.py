import mujoco
import numpy as np

from envs.pick_place_env import PickPlaceEnv
from controllers.ee_delta_controller import EEDeltaController
from experts.scripted_pick_place import ScriptedPickPlaceExpert, PickPlaceStage

"""
保存数据即操作之前，目前这个版本修改了place_xy_offset导致其成功率到达100%
"""

def run_one(seed, render=False):
    env = PickPlaceEnv(
        render_width=224,
        render_height=224,
        camera_name="top",
        seed=seed,
    )

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

    expert = ScriptedPickPlaceExpert(
        env=env,
        max_delta=0.010,
        reach_tol=0.018,
        z_reach_tol=0.015,
        pregrasp_height=0.20,
        grasp_height=0.105,
        lift_height=0.25,
        place_height=0.22,
        place_down_height=0.115,
        retreat_height=0.25,
        close_steps=120,
        open_steps=60,
        # 如果你当前 ScriptedPickPlaceExpert 还没有这个参数，
        # 先把这一行注释掉。
        grasp_xy_offset=(-0.01, 0.006),
        place_xy_offset=(-0.050, -0.005),
    )

    env.reset()
    expert.reset()

    max_steps = 1800

    ever_grasp_success = False
    ever_place_success = False
    final_stage = None

    max_cube_z = -1e9
    min_place_xy_dist = 1e9

    initial_cube = env.get_cube_pos().copy()
    initial_target = env.get_target_pos().copy()

    for step in range(max_steps):
        action, expert_info = expert.get_action()

        ctrl, ctrl_info = controller.compute_control(
            dx=action[0],
            dy=action[1],
            dz=action[2],
            droll=action[3],
            dpitch=action[4],
            dyaw=action[5],
            gripper=action[6],
        )

        env.step_sim(ctrl=ctrl, n_substeps=20)

        cube_pos = env.get_cube_pos()
        target_pos = env.get_target_pos()

        cube_z = float(cube_pos[2])
        max_cube_z = max(max_cube_z, cube_z)

        place_xy_dist = float(np.linalg.norm(cube_pos[:2] - target_pos[:2]))
        min_place_xy_dist = min(min_place_xy_dist, place_xy_dist)

        if env.is_grasp_success():
            ever_grasp_success = True

        if env.is_place_success():
            ever_place_success = True

        final_stage = expert_info["stage"]

        if expert.stage == PickPlaceStage.DONE:
            break

    final_cube = env.get_cube_pos()
    final_target = env.get_target_pos()

    final_xy_dist = float(np.linalg.norm(final_cube[:2] - final_target[:2]))
    final_cube_lift = float(max_cube_z - env.cube_z)

    final_place_error = final_cube[:2] - final_target[:2]

    final_place_success = env.is_place_success()
    expert_done = expert.stage == PickPlaceStage.DONE

    valid_demo = (
        expert_done
        and ever_grasp_success
        and final_place_success
        and final_cube_lift > 0.03
    )

    if valid_demo:
        failure_reason = "none"
    elif not ever_grasp_success:
        failure_reason = "grasp_failed"
    elif final_cube_lift <= 0.03:
        failure_reason = "insufficient_lift"
    elif not final_place_success:
        failure_reason = "place_failed"
    elif not expert_done:
        failure_reason = "timeout_or_not_done"
    else:
        failure_reason = "unknown"

    env.close()

    return {
        "seed": seed,

        # 推荐以后用这个作为“是否保存进数据集”的标准
        "valid_demo": valid_demo,

        # 这个只是最终位置是否满足 place metric
        "final_place_success": final_place_success,

        # 这个表示 expert 状态机是否完整走到 DONE
        "expert_done": expert_done,

        # 过程指标
        "ever_grasp": ever_grasp_success,
        "ever_place": ever_place_success,
        "max_cube_z": max_cube_z,
        "final_cube_lift": final_cube_lift,
        "min_place_xy_dist": min_place_xy_dist,
        "final_xy_dist": final_xy_dist,

        # 终局状态
        "final_stage": final_stage,
        "final_cube": final_cube,
        "final_target": final_target,
        "initial_cube": initial_cube,
        "initial_target": initial_target,
        "steps": step + 1,

        # 失败原因
        "failure_reason": failure_reason,

        # 为了兼容你原 main() 里的 result["success"]
        # 这里先让 success 等于 valid_demo，而不是 env.is_place_success()
        "success": valid_demo,
        "final_place_error": final_place_error,
    }


def main():
    num_trials = 50
    results = []
    failed_seeds = []

    for seed in range(num_trials):
        result = run_one(seed)
        results.append(result)

        if not result["success"]:
            failed_seeds.append(seed)

        print(
            f"seed={seed:03d} "
            f"valid_demo={result['valid_demo']} "
            # f"final_place={result['final_place_success']} "
            # f"expert_done={result['expert_done']} "
            # f"ever_grasp={result['ever_grasp']} "
            # f"ever_place={result['ever_place']} "
            # f"max_cube_z={result['max_cube_z']:.4f} "
            # f"lift={result['final_cube_lift']:.4f} "
            # f"min_xy={result['min_place_xy_dist']:.4f} "
            # f"final_xy={result['final_xy_dist']:.4f} "
            # f"stage={result['final_stage']} "
            # f"steps={result['steps']} "
            # f"reason={result['failure_reason']} "
            # f"cube={result['final_cube']} "
            # f"target={result['final_target']}"
            f"place_err={result['final_place_error']} "
        )


    success_rate = sum(r["success"] for r in results) / len(results)
    grasp_rate = sum(r["ever_grasp"] for r in results) / len(results)
    ever_place_rate = sum(r["ever_place"] for r in results) / len(results)

    print("=" * 80)
    print(f"ever_grasp_rate: {grasp_rate:.3f}")
    print(f"ever_place_rate: {ever_place_rate:.3f}")
    print(f"final_success_rate: {success_rate:.3f}")
    print(f"failed_seeds: {failed_seeds}")
    print("=" * 80)



if __name__ == "__main__":
    main()
