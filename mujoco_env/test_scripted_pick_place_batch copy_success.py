import mujoco

from envs.pick_place_env import PickPlaceEnv
from controllers.ee_delta_controller import EEDeltaController
from experts.scripted_pick_place import ScriptedPickPlaceExpert, PickPlaceStage


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
        max_pos_delta=0.008,
        min_ee_z_above_table=0.035,
        workspace_low=(0.25, -0.35, 0.43),
        workspace_high=(0.90, 0.35, 1.00),
        open_gripper_ctrl=255.0,
        close_gripper_ctrl=0.0,
    )

    expert = ScriptedPickPlaceExpert(
        env=env,
        max_delta=0.006,
        reach_tol=0.010,
        z_reach_tol=0.010,
        pregrasp_height=0.20,
        grasp_height=0.100,
        lift_height=0.25,
        place_height=0.22,
        place_down_height=0.110,
        retreat_height=0.25,
        close_steps=100,
        open_steps=60,
    )

    env.reset()
    expert.reset()

    max_steps = 1200

    ever_grasp_success = False
    ever_place_success = False
    final_stage = None

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

        if env.is_grasp_success():
            ever_grasp_success = True

        if env.is_place_success():
            ever_place_success = True

        final_stage = expert_info["stage"]

        if expert.stage == PickPlaceStage.DONE:
            break

    final_success = env.is_place_success()

    final_cube = env.get_cube_pos()
    final_target = env.get_target_pos()

    env.close()

    return {
        "seed": seed,
        "success": final_success,
        "ever_grasp": ever_grasp_success,
        "ever_place": ever_place_success,
        "final_stage": final_stage,
        "final_cube": final_cube,
        "final_target": final_target,
        "steps": step + 1,
    }



def main():
    num_trials = 20
    results = []
    failed_seeds = []

    for seed in range(num_trials):
        result = run_one(seed)
        results.append(result)

        if not result["success"]:
            failed_seeds.append(seed)

        print(
            f"seed={seed:03d} "
            f"success={result['success']} "
            f"ever_grasp={result['ever_grasp']} "
            f"ever_place={result['ever_place']} "
            f"stage={result['final_stage']} "
            f"steps={result['steps']} "
            f"cube={result['final_cube']} "
            f"target={result['final_target']}"
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
