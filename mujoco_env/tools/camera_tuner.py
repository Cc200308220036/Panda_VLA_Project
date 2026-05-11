import os
import time
import argparse
import numpy as np
import cv2
import mujoco


WINDOW_NAME = "MuJoCo Camera Tuner"


def normalize(v, eps=1e-8):
    v = np.asarray(v, dtype=np.float64)
    n = np.linalg.norm(v)
    if n < eps:
        return v
    return v / n


def lookat_to_xyaxes(cam_pos, lookat, world_up=np.array([0.0, 0.0, 1.0])):
    """
    MuJoCo camera convention:
    - xyaxes defines camera x-axis and y-axis in world/body frame.
    - camera looks along negative z-axis.
    Therefore:
        forward = lookat - cam_pos
        z_axis = -forward
    """
    cam_pos = np.asarray(cam_pos, dtype=np.float64)
    lookat = np.asarray(lookat, dtype=np.float64)

    forward = normalize(lookat - cam_pos)
    z_axis = normalize(-forward)

    world_up = np.asarray(world_up, dtype=np.float64)

    # If z_axis is nearly parallel to world_up, choose another up vector.
    if abs(np.dot(z_axis, world_up)) > 0.98:
        world_up = np.array([0.0, 1.0, 0.0], dtype=np.float64)

    x_axis = normalize(np.cross(world_up, z_axis))
    y_axis = normalize(np.cross(z_axis, x_axis))

    return x_axis, y_axis, z_axis


def rotation_matrix_to_quat_wxyz(R):
    quat = np.zeros(4, dtype=np.float64)
    mujoco.mju_mat2Quat(quat, R.reshape(-1))
    return quat


def format_vec(v, precision=4):
    return " ".join([f"{x:.{precision}f}" for x in v])


def make_camera_snippet(camera_name, cam_pos, x_axis, y_axis, fovy):
    xyaxes = np.concatenate([x_axis, y_axis])
    snippet = (
        f'<camera name="{camera_name}"\n'
        f'        pos="{format_vec(cam_pos)}"\n'
        f'        xyaxes="{format_vec(xyaxes)}"\n'
        f'        fovy="{fovy:.1f}"/>'
    )
    return snippet


def set_home_pose(model, data):
    home_qpos = [
        0.0,
        -0.785,
        0.0,
        -2.356,
        0.0,
        1.571,
        0.785,
    ]

    joint_names = [
        "joint1",
        "joint2",
        "joint3",
        "joint4",
        "joint5",
        "joint6",
        "joint7",
    ]

    for i, joint_name in enumerate(joint_names):
        joint_id = mujoco.mj_name2id(
            model,
            mujoco.mjtObj.mjOBJ_JOINT,
            joint_name,
        )
        if joint_id < 0:
            raise RuntimeError(f"Cannot find joint: {joint_name}")

        qpos_adr = int(model.jnt_qposadr[joint_id])
        data.qpos[qpos_adr] = home_qpos[i]

    mujoco.mj_forward(model, data)


def create_slider(name, value, min_val, max_val, scale=1000):
    cv2.createTrackbar(name, WINDOW_NAME, 0, scale, lambda x: None)
    pos = int((value - min_val) / (max_val - min_val) * scale)
    pos = max(0, min(scale, pos))
    cv2.setTrackbarPos(name, WINDOW_NAME, pos)


def read_slider(name, min_val, max_val, scale=1000):
    pos = cv2.getTrackbarPos(name, WINDOW_NAME)
    return min_val + (max_val - min_val) * float(pos) / float(scale)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--xml",
        type=str,
        default="~/panda_vla_project/mujoco_env/assets/robots/franka_panda/panda_pick_place.xml",
    )
    parser.add_argument("--camera", type=str, default="front")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)

    parser.add_argument("--cam_x", type=float, default=1.05)
    parser.add_argument("--cam_y", type=float, default=-0.75)
    parser.add_argument("--cam_z", type=float, default=0.90)

    parser.add_argument("--look_x", type=float, default=0.58)
    parser.add_argument("--look_y", type=float, default=0.00)
    parser.add_argument("--look_z", type=float, default=0.50)

    parser.add_argument("--fovy", type=float, default=55.0)

    args = parser.parse_args()

    xml_path = os.path.expanduser(args.xml)
    if not os.path.exists(xml_path):
        raise FileNotFoundError(xml_path)

    model = mujoco.MjModel.from_xml_path(xml_path)
    data = mujoco.MjData(model)

    camera_id = mujoco.mj_name2id(
        model,
        mujoco.mjtObj.mjOBJ_CAMERA,
        args.camera,
    )

    if camera_id < 0:
        raise RuntimeError(
            f"Cannot find camera '{args.camera}'. "
            f"Please add a camera with this name in panda_pick_place.xml first."
        )

    set_home_pose(model, data)

    # Let cube/table settle a bit.
    for _ in range(50):
        mujoco.mj_step(model, data)

    renderer = mujoco.Renderer(model, height=args.height, width=args.width)

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, args.width, args.height)

    # Slider ranges.
    ranges = {
        "cam_x": (0.30, 1.40),
        "cam_y": (-1.20, 1.20),
        "cam_z": (0.35, 1.80),
        "look_x": (0.35, 0.85),
        "look_y": (-0.35, 0.35),
        "look_z": (0.20, 0.85),
        "fovy": (25.0, 90.0),
    }

    create_slider("cam_x", args.cam_x, *ranges["cam_x"])
    create_slider("cam_y", args.cam_y, *ranges["cam_y"])
    create_slider("cam_z", args.cam_z, *ranges["cam_z"])

    create_slider("look_x", args.look_x, *ranges["look_x"])
    create_slider("look_y", args.look_y, *ranges["look_y"])
    create_slider("look_z", args.look_z, *ranges["look_z"])

    create_slider("fovy", args.fovy, *ranges["fovy"])

    print("=" * 80)
    print("Camera tuner controls:")
    print("  Move sliders to adjust camera position, look-at point, and fovy.")
    print("  Press 'p' to print current XML camera snippet.")
    print("  Press 's' to save screenshot and snippet.")
    print("  Press 'q' or ESC to quit.")
    print("=" * 80)

    last_snippet = None

    while True:
        cam_pos = np.array(
            [
                read_slider("cam_x", *ranges["cam_x"]),
                read_slider("cam_y", *ranges["cam_y"]),
                read_slider("cam_z", *ranges["cam_z"]),
            ],
            dtype=np.float64,
        )

        lookat = np.array(
            [
                read_slider("look_x", *ranges["look_x"]),
                read_slider("look_y", *ranges["look_y"]),
                read_slider("look_z", *ranges["look_z"]),
            ],
            dtype=np.float64,
        )

        fovy = read_slider("fovy", *ranges["fovy"])

        x_axis, y_axis, z_axis = lookat_to_xyaxes(cam_pos, lookat)
        R = np.column_stack([x_axis, y_axis, z_axis])
        quat = rotation_matrix_to_quat_wxyz(R)

        model.cam_pos[camera_id] = cam_pos
        model.cam_quat[camera_id] = quat
        model.cam_fovy[camera_id] = fovy

        mujoco.mj_forward(model, data)

        renderer.update_scene(data, camera=args.camera)
        rgb = renderer.render()
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        snippet = make_camera_snippet(
            args.camera,
            cam_pos,
            x_axis,
            y_axis,
            fovy,
        )
        last_snippet = snippet

        overlay_lines = [
            f"camera: {args.camera}",
            f"cam_pos: [{cam_pos[0]:.3f}, {cam_pos[1]:.3f}, {cam_pos[2]:.3f}]",
            f"lookat:  [{lookat[0]:.3f}, {lookat[1]:.3f}, {lookat[2]:.3f}]",
            f"fovy: {fovy:.1f}",
            "p: print | s: save | q/esc: quit",
        ]

        y = 24
        for line in overlay_lines:
            cv2.putText(
                bgr,
                line,
                (12, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
            y += 24

        cv2.imshow(WINDOW_NAME, bgr)

        key = cv2.waitKey(30) & 0xFF

        if key == ord("p"):
            print("\n" + "=" * 80)
            print(last_snippet)
            print("=" * 80 + "\n")

        elif key == ord("s"):
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            image_path = f"camera_tune_{args.camera}_{timestamp}.png"
            txt_path = f"camera_tune_{args.camera}_{timestamp}.txt"

            cv2.imwrite(image_path, bgr)

            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(last_snippet + "\n")
                f.write("\n")
                f.write(f"lookat = {format_vec(lookat)}\n")

            print("\nSaved:")
            print(" ", image_path)
            print(" ", txt_path)
            print("\n" + last_snippet + "\n")

        elif key == ord("q") or key == 27:
            break

    renderer.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
