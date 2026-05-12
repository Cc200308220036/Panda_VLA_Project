import os
import mujoco

xml_path = os.path.expanduser(
    "~/panda_vla_project/mujoco_env/assets/robots/franka_panda/panda_pick_place.xml"
)

print("xml_path:", xml_path)
print("exists:", os.path.exists(xml_path))

model = mujoco.MjModel.from_xml_path(xml_path)
data = mujoco.MjData(model)

print("MuJoCo pick-place model loaded.")
print("nq:", model.nq)
print("nv:", model.nv)
print("nu:", model.nu)
print("nbody:", model.nbody)
print("ngeom:", model.ngeom)
print("ncam:", model.ncam)

for _ in range(20):
    mujoco.mj_step(model, data)

print("MuJoCo step ok.")

for name in ["red_cube", "green_target", "table"]:
    body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
    print(name, "body_id:", body_id)

for name in ["front", "top", "side", "front_policy", "front_debug"]:
    cam_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, name)
    print(name, "camera_id:", cam_id)

