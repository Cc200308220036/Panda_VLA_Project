import os
import time
import mujoco
import mujoco.viewer

xml_path = os.path.expanduser(
    "~/panda_vla_project/mujoco_env/assets/robots/franka_panda/scene.xml"
)

model = mujoco.MjModel.from_xml_path(xml_path)
data = mujoco.MjData(model)

with mujoco.viewer.launch_passive(model, data) as viewer:
    while viewer.is_running():
        mujoco.mj_step(model, data)
        viewer.sync()
        time.sleep(model.opt.timestep)
