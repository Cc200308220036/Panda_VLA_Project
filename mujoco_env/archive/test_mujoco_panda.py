import os
import mujoco

xml_path = os.path.expanduser(
    "~/panda_vla_project/mujoco_env/assets/robots/franka_panda/scene.xml"
)

model = mujoco.MjModel.from_xml_path(xml_path)
data = mujoco.MjData(model)

print("MuJoCo model loaded.")
print("nq:", model.nq)
print("nv:", model.nv)
print("nu:", model.nu)
print("nbody:", model.nbody)

for _ in range(10):
    mujoco.mj_step(model, data)

print("MuJoCo step ok.")
