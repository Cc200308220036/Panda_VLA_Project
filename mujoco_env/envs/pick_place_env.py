import os
import numpy as np
import mujoco

from mujoco_env.envs.panda_base_env import PandaBaseEnv


class PickPlaceEnv(PandaBaseEnv):
    def __init__(
        self,
        xml_path=None,
        render_width=224,
        render_height=224,
        camera_name="top",
        seed=0,
    ):
        if xml_path is None:
            xml_path = os.path.expanduser(
                "~/panda_vla_project/mujoco_env/assets/robots/franka_panda/panda_pick_place.xml"
            )

        self.rng = np.random.default_rng(seed)

        self.table_top_z = 0.40
        self.cube_half_size = 0.025
        self.cube_z = self.table_top_z + self.cube_half_size
        self.target_z = self.table_top_z + 0.003

        self.cube_body_name = "red_cube"
        self.target_body_name = "green_target"

        self.cube_joint_name = "red_cube_freejoint"

        # 工作空间不要太大，先保证 scripted expert 容易成功
        self.cube_x_range = (0.5, 0.56)
        self.cube_y_range = (-0.14, -0.07)

        self.target_x_range = (0.62, 0.70)
        self.target_y_range = (0.08, 0.18)

        self.max_episode_steps = 300
        self.step_count = 0

        super().__init__(
            xml_path=xml_path,
            render_width=render_width,
            render_height=render_height,
            camera_name=camera_name,
            auto_reset=False,
        )

        self.cube_body_id = mujoco.mj_name2id(
            self.model,
            mujoco.mjtObj.mjOBJ_BODY,
            self.cube_body_name,
        )

        self.target_body_id = mujoco.mj_name2id(
            self.model,
            mujoco.mjtObj.mjOBJ_BODY,
            self.target_body_name,
        )

        self.cube_joint_id = mujoco.mj_name2id(
            self.model,
            mujoco.mjtObj.mjOBJ_JOINT,
            self.cube_joint_name,
        )

        if self.cube_body_id < 0:
            raise RuntimeError(f"Cannot find body: {self.cube_body_name}")

        if self.target_body_id < 0:
            raise RuntimeError(f"Cannot find body: {self.target_body_name}")

        if self.cube_joint_id < 0:
            raise RuntimeError(f"Cannot find joint: {self.cube_joint_name}")

        self.cube_qpos_adr = int(self.model.jnt_qposadr[self.cube_joint_id])

        self.reset()
        
    def sample_cube_xy(self):
        x = self.rng.uniform(*self.cube_x_range)
        y = self.rng.uniform(*self.cube_y_range)
        return np.array([x, y], dtype=np.float64)

    def sample_target_xy(self):
        x = self.rng.uniform(*self.target_x_range)
        y = self.rng.uniform(*self.target_y_range)
        return np.array([x, y], dtype=np.float64)

    def set_cube_pose(self, xy):
        """
        Freejoint qpos layout:
        [x, y, z, qw, qx, qy, qz]
        """
        qadr = self.cube_qpos_adr

        self.data.qpos[qadr + 0] = xy[0]
        self.data.qpos[qadr + 1] = xy[1]
        self.data.qpos[qadr + 2] = self.cube_z

        self.data.qpos[qadr + 3] = 1.0
        self.data.qpos[qadr + 4] = 0.0
        self.data.qpos[qadr + 5] = 0.0
        self.data.qpos[qadr + 6] = 0.0

        # 清掉 cube 对应 freejoint 的速度，避免 reset 后滑动
        dof_adr = int(self.model.jnt_dofadr[self.cube_joint_id])
        self.data.qvel[dof_adr:dof_adr + 6] = 0.0

    def set_target_pose(self, xy):
        self.model.body_pos[self.target_body_id, 0] = xy[0]
        self.model.body_pos[self.target_body_id, 1] = xy[1]
        self.model.body_pos[self.target_body_id, 2] = self.target_z

    def reset(self):
        # 先 reset robot 和整个 sim
        mujoco.mj_resetData(self.model, self.data)

        # 设置 Panda home pose
        for i, joint_name in enumerate(self.joint_names):
            joint_id = mujoco.mj_name2id(
                self.model,
                mujoco.mjtObj.mjOBJ_JOINT,
                joint_name,
            )
            qpos_adr = int(self.model.jnt_qposadr[joint_id])
            self.data.qpos[qpos_adr] = self.home_qpos[i]

        # 随机 cube 和 target
        cube_xy = self.sample_cube_xy()
        target_xy = self.sample_target_xy()

        self.set_cube_pose(cube_xy)
        self.set_target_pose(target_xy)

        self.step_count = 0

        mujoco.mj_forward(self.model, self.data)

        return self.get_obs()

    def get_cube_pos(self):
        return self.data.xpos[self.cube_body_id].copy().astype(np.float32)

    def get_target_pos(self):
        return self.data.xpos[self.target_body_id].copy().astype(np.float32)

    def get_robot_state(self):
        joint_pos = self.get_joint_pos()
        joint_vel = self.get_joint_vel()
        gripper_qpos = self.get_gripper_qpos()
        ee_pos, ee_quat = self.get_ee_pose()

        return np.concatenate(
            [
                joint_pos,
                joint_vel,
                gripper_qpos,
                ee_pos,
                ee_quat,
            ],
            axis=0,
        ).astype(np.float32)

    def get_obs(self):
        obs = super().get_obs()

        obs["robot_state"] = self.get_robot_state()

        # 注意：cube_pos / target_pos 后续只给 expert 和 success 判断用
        # 训练视觉策略时不要作为 policy 输入
        obs["cube_pos"] = self.get_cube_pos()
        obs["target_pos"] = self.get_target_pos()

        return obs

    def get_place_xy_dist(self):
        cube_pos = self.get_cube_pos()
        target_pos = self.get_target_pos()
        return float(np.linalg.norm(cube_pos[:2] - target_pos[:2]))


    def is_grasp_success(self):
        cube_pos = self.get_cube_pos()
 
        # cube 在桌面上的中心高度大约是 self.cube_z = 0.425
        # 只要比桌面初始高度再高 1.5cm，就认为抓起来过
        return bool(cube_pos[2] > self.cube_z + 0.015)

    def is_place_success(self, strict=True):
        cube_pos = self.get_cube_pos()
        target_pos = self.get_target_pos()

        xy_dist = np.linalg.norm(cube_pos[:2] - target_pos[:2])

        # cube 放回桌面附近即可
        z_ok = abs(cube_pos[2] - self.cube_z) < 0.03

        if strict:
            # 更适合“高质量 demo”判定：要求更居中
            return bool(xy_dist < 0.05 and z_ok)
        else:
            # 调试阶段用：只要 cube 落在 target 附近/覆盖 target 大部分区域即可
            return bool(xy_dist < 0.085 and z_ok)

    def compute_reward(self):
        cube_pos = self.get_cube_pos()
        target_pos = self.get_target_pos()
        ee_pos, _ = self.get_ee_pose()

        dist_ee_cube = np.linalg.norm(ee_pos - cube_pos)
        dist_cube_target = np.linalg.norm(cube_pos[:2] - target_pos[:2])

        reward = 0.0
        reward += -dist_ee_cube
        reward += -dist_cube_target

        if self.is_grasp_success():
            reward += 1.0

        if self.is_place_success():
            reward += 5.0

        return float(reward)

    def step_env(self, ctrl=None, n_substeps=10):
        self.step_count += 1

        obs = self.step(ctrl=ctrl, n_substeps=n_substeps)

        reward = self.compute_reward()
        success = self.is_place_success()

        done = False
        if success:
            done = True
        if self.step_count >= self.max_episode_steps:
            done = True

        info = {
            "success": success,
            "grasp_success": self.is_grasp_success(),
            "cube_pos": self.get_cube_pos(),
            "target_pos": self.get_target_pos(),
            "step_count": self.step_count,
        }

        return obs, reward, done, info
