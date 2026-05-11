import cv2

from envs.pick_place_env import PickPlaceEnv


def main():
    env = PickPlaceEnv(
        render_width=640,
        render_height=480,
        camera_name="side",
        seed=42,
    )

    for i in range(5):
        obs = env.reset()

        print("=" * 50)
        print("reset:", i)
        print("joint_pos:", obs["joint_pos"])
        print("robot_state shape:", obs["robot_state"].shape)
        print("cube_pos:", obs["cube_pos"])
        print("target_pos:", obs["target_pos"])
        print("image shape:", obs["image"].shape)

        img = cv2.cvtColor(obs["image"], cv2.COLOR_RGB2BGR)
        out_path = f"reset_{i:02d}_top.png"
        cv2.imwrite(out_path, img)
        print("saved:", out_path)

    env.close()


if __name__ == "__main__":
    main()
