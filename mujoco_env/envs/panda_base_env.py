import os
import numpy as np
import mujoco


class PandaBaseEnv:
    def __init__(
        self,
        xml_path: str,
        render_width: int = 224,
        render_height: int = 224,
        camera_name=None,
        auto_reset: bool = True,
    ):
        self.xml_path = xml_path
        self.render_width = render_width
        self.render_height = render_height
        self.camera_name = camera_name

        self.model = mujoco.MjModel.from_xml_path(xml_path)
        self.data = mujoco.MjData(self.model)

        self.renderer = mujoco.Renderer(
            self.model,
            height=render_height,
            width=render_width,
        )

        self.joint_names = [
            "joint1",
            "joint2",
            "joint3",
            "joint4",
            "joint5",
            "joint6",
            "joint7",
        ]

        self.ee_body_name = "hand"

        self.home_qpos = np.array([
            0.0,
            -0.785,
            0.0,
            -2.356,
            0.0,
            1.571,
            0.785,
        ], dtype=np.float64)

        if auto_reset:
            self.reset()

    # def reset(self):
    #     mujoco.mj_resetData(self.model, self.data)

    #     for i, joint_name in enumerate(self.joint_names):
    #         qpos_adr = self.model.joint(joint_name).qposadr
    #         self.data.qpos[qpos_adr] = self.home_qpos[i]

    #     mujoco.mj_forward(self.model, self.data)
    #     return self.get_obs()
    
    def reset(self):
        mujoco.mj_resetData(self.model, self.data)

        for i, joint_name in enumerate(self.joint_names):
            joint_id = mujoco.mj_name2id(
                self.model,
                mujoco.mjtObj.mjOBJ_JOINT,
                joint_name,
            )
            qpos_adr = int(self.model.jnt_qposadr[joint_id])
            self.data.qpos[qpos_adr] = self.home_qpos[i]
            
        mujoco.mj_forward(self.model, self.data)
        return self.get_obs()

    def step_sim(self, ctrl=None, n_substeps: int = 10):
        """
        Only step MuJoCo physics.
        Does not render image and does not return observation.
        Use this for fast control loops and native MuJoCo viewer.
        """
        if ctrl is not None:
            ctrl = np.asarray(ctrl, dtype=np.float64)
            n_ctrl = min(len(ctrl), self.model.nu)
            self.data.ctrl[:n_ctrl] = ctrl[:n_ctrl]

        for _ in range(n_substeps):
            mujoco.mj_step(self.model, self.data)

    def step(self, ctrl=None, n_substeps: int = 10):
        """
        Step physics and return full observation including image.
        Use this when you really need rendered image.
        """
        self.step_sim(ctrl=ctrl, n_substeps=n_substeps)
        return self.get_obs()

    def get_joint_pos(self):
        q = []
        for joint_name in self.joint_names:
            joint_id = mujoco.mj_name2id(
                self.model,
                mujoco.mjtObj.mjOBJ_JOINT,
                joint_name,
            )
            qpos_adr = int(self.model.jnt_qposadr[joint_id])
            q.append(float(self.data.qpos[qpos_adr]))

        return np.asarray(q, dtype=np.float32).reshape(-1)

    # def get_joint_vel(self):
    #     dq = []
    #     for joint_name in self.joint_names:
    #         dof_adr = int(np.asarray(self.model.joint(joint_name).dofadr).item())
    #         dq.append(float(self.data.qvel[dof_adr]))
    #     return np.asarray(dq, dtype=np.float32)

    def get_joint_vel(self):
        dq = []
        for joint_name in self.joint_names:
            joint_id = mujoco.mj_name2id(
                self.model,
                mujoco.mjtObj.mjOBJ_JOINT,
                joint_name,
            )
            dof_adr = int(self.model.jnt_dofadr[joint_id])
            dq.append(float(self.data.qvel[dof_adr]))

        return np.asarray(dq, dtype=np.float32).reshape(-1)

    def get_gripper_qpos(self):
        # Panda menagerie 一般有两个 finger joint
        # nq=9，前 7 个是 arm，后 2 个通常是 fingers
        return self.data.qpos[7:9].copy().astype(np.float32)

    def get_ee_pose(self):
        body_id = self.model.body(self.ee_body_name).id

        pos = self.data.xpos[body_id].copy()
        mat = self.data.xmat[body_id].reshape(3, 3).copy()

        quat = np.zeros(4, dtype=np.float64)
        mujoco.mju_mat2Quat(quat, mat.reshape(-1))

        return pos.astype(np.float32), quat.astype(np.float32)

    def get_body_pos(self, body_name):
        body_id = mujoco.mj_name2id(
            self.model,
            mujoco.mjtObj.mjOBJ_BODY,
            body_name,
        )

        if body_id < 0:
            raise RuntimeError(f"Cannot find body: {body_name}")

        return self.data.xpos[body_id].copy().astype(np.float32)

    def get_gripper_center_pos(self):
        """
        Approximate TCP / grasp point as the midpoint between left and right finger bodies.
        This is better than using the 'hand' body origin for pick-and-place.
        """
        left_pos = self.get_body_pos("left_finger")
        right_pos = self.get_body_pos("right_finger")

        return 0.5 * (left_pos + right_pos)


    def render(self):
        if self.camera_name is None:
            self.renderer.update_scene(self.data)
        else:
            self.renderer.update_scene(self.data, camera=self.camera_name)

        rgb = self.renderer.render()
        return rgb

    def get_state_obs(self):
        joint_pos = self.get_joint_pos()
        joint_vel = self.get_joint_vel()
        ee_pos, ee_quat = self.get_ee_pose()

        obs = {
            "joint_pos": joint_pos,
            "joint_vel": joint_vel,
            "gripper_qpos": self.get_gripper_qpos(),
            "ee_pos": ee_pos,
            "ee_quat": ee_quat,
        }


        return obs

    def get_obs(self):
        obs = self.get_state_obs()
        obs["image"] = self.render()
        return obs

    def close(self):
        self.renderer.close()
