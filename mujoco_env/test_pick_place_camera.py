import os
import cv2
import mujoco

xml_path = os.path.expanduser(
    "~/panda_vla_project/mujoco_env/assets/robots/franka_panda/panda_pick_place.xml"
)

model = mujoco.MjModel.from_xml_path(xml_path)
data = mujoco.MjData(model)

renderer = mujoco.Renderer(model, height=480, width=640)

for _ in range(50):
    mujoco.mj_step(model, data)

for camera_name in ["top", "front_policy", "front_debug", "side"]:
    renderer.update_scene(data, camera=camera_name)
    rgb = renderer.render()

    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    out_path = f"{camera_name}_camera_test.png"
    cv2.imwrite(out_path, bgr)

    print("saved:", out_path, "shape:", rgb.shape)

renderer.close()
