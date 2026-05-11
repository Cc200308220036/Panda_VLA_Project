from envs.pick_place_env import PickPlaceEnv


def main():
    env = PickPlaceEnv(
        render_width=224,
        render_height=224,
        camera_name="front_debug",
        seed=0,
    )

    obs = env.reset()

    print("hand ee_pos:", obs["ee_pos"])
    print("gripper_center_pos:", obs["gripper_center_pos"])
    print("cube_pos:", obs["cube_pos"])
    print("target_pos:", obs["target_pos"])
    print("hand - gripper_center:", obs["ee_pos"] - obs["gripper_center_pos"])

    env.close()


if __name__ == "__main__":
    main()
