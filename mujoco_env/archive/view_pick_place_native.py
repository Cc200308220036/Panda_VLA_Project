import os
import time
import mujoco
import mujoco.viewer

xml_path = os.path.expanduser(
    "~/panda_vla_project/mujoco_env/assets/robots/franka_panda/panda_pick_place.xml"
)

model = mujoco.MjModel.from_xml_path(xml_path)
data = mujoco.MjData(model)

# 设置一个比较自然的 Panda 初始姿态
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
    qpos_adr = model.jnt_qposadr[joint_id]
    data.qpos[qpos_adr] = home_qpos[i]

mujoco.mj_forward(model, data)

with mujoco.viewer.launch_passive(model, data) as viewer:
    while viewer.is_running():
        mujoco.mj_step(model, data)
        viewer.sync()
        time.sleep(model.opt.timestep)
