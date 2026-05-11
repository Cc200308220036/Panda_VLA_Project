import numpy as np
import mujoco


class PandaIKSolver:
    def __init__(
        self,
        model,
        data,
        joint_names,
        ee_body_name="hand",
        damping=1e-3,
        max_iters=80,
        pos_tol=2e-3,
        step_size=0.7,
        max_dq=0.05,
    ):
        self.model = model
        self.data = data
        self.joint_names = joint_names
        self.ee_body_name = ee_body_name

        self.damping = damping
        self.max_iters = max_iters
        self.pos_tol = pos_tol
        self.step_size = step_size
        self.max_dq = max_dq

        self.ee_body_id = mujoco.mj_name2id(
            self.model,
            mujoco.mjtObj.mjOBJ_BODY,
            self.ee_body_name,
        )

        if self.ee_body_id < 0:
            raise RuntimeError(f"Cannot find ee body: {self.ee_body_name}")

        self.joint_ids = []
        self.qpos_adrs = []
        self.dof_adrs = []

        for name in self.joint_names:
            joint_id = mujoco.mj_name2id(
                self.model,
                mujoco.mjtObj.mjOBJ_JOINT,
                name,
            )
            if joint_id < 0:
                raise RuntimeError(f"Cannot find joint: {name}")

            self.joint_ids.append(joint_id)
            self.qpos_adrs.append(int(self.model.jnt_qposadr[joint_id]))
            self.dof_adrs.append(int(self.model.jnt_dofadr[joint_id]))

        self.qpos_adrs = np.asarray(self.qpos_adrs, dtype=np.int32)
        self.dof_adrs = np.asarray(self.dof_adrs, dtype=np.int32)

    def get_q(self):
        return self.data.qpos[self.qpos_adrs].copy()

    def set_q(self, q):
        q = np.asarray(q, dtype=np.float64)
        self.data.qpos[self.qpos_adrs] = q
        mujoco.mj_forward(self.model, self.data)

    def get_ee_pos(self):
        return self.data.xpos[self.ee_body_id].copy()

    def solve_position_ik(self, target_pos, q_init=None):
        """
        Solve IK for end-effector position only.

        Returns:
            q_solution: np.ndarray, shape [7]
            success: bool
            final_error: float
        """
        target_pos = np.asarray(target_pos, dtype=np.float64).reshape(3)

        q_backup = self.get_q()

        if q_init is None:
            q = q_backup.copy()
        else:
            q = np.asarray(q_init, dtype=np.float64).copy()

        success = False
        final_error = np.inf

        for _ in range(self.max_iters):
            self.set_q(q)

            current_pos = self.get_ee_pos()
            error = target_pos - current_pos
            final_error = float(np.linalg.norm(error))

            if final_error < self.pos_tol:
                success = True
                break

            jacp = np.zeros((3, self.model.nv), dtype=np.float64)
            jacr = np.zeros((3, self.model.nv), dtype=np.float64)

            mujoco.mj_jacBody(
                self.model,
                self.data,
                jacp,
                jacr,
                self.ee_body_id,
            )

            J = jacp[:, self.dof_adrs]

            # Damped least squares:
            # dq = J^T (J J^T + lambda I)^-1 error
            A = J @ J.T + self.damping * np.eye(3)
            dq = J.T @ np.linalg.solve(A, error)

            dq = self.step_size * dq
            dq = np.clip(dq, -self.max_dq, self.max_dq)

            q = q + dq

        q_solution = q.copy()

        # Restore original simulation state.
        self.set_q(q_backup)

        return q_solution, success, final_error


# import numpy as np
# import mujoco


# class PandaIKSolver:
#     def __init__(
#         self,
#         model,
#         data,
#         joint_names,
#         ee_body_name="hand",
#         control_point="hand",
#         left_finger_body_name="left_finger",
#         right_finger_body_name="right_finger",
#         damping=1e-3,
#         max_iters=80,
#         pos_tol=2e-3,
#         step_size=0.7,
#         max_dq=0.05,
#     ):
#         self.model = model
#         self.data = data
#         self.joint_names = joint_names
#         self.ee_body_name = ee_body_name
#         self.control_point = control_point

#         self.left_finger_body_name = left_finger_body_name
#         self.right_finger_body_name = right_finger_body_name

#         self.damping = damping
#         self.max_iters = max_iters
#         self.pos_tol = pos_tol
#         self.step_size = step_size
#         self.max_dq = max_dq

#         self.ee_body_id = mujoco.mj_name2id(
#             self.model,
#             mujoco.mjtObj.mjOBJ_BODY,
#             self.ee_body_name,
#         )

#         if self.ee_body_id < 0:
#             raise RuntimeError(f"Cannot find ee body: {self.ee_body_name}")

#         self.left_finger_body_id = mujoco.mj_name2id(
#             self.model,
#             mujoco.mjtObj.mjOBJ_BODY,
#             self.left_finger_body_name,
#         )

#         self.right_finger_body_id = mujoco.mj_name2id(
#             self.model,
#             mujoco.mjtObj.mjOBJ_BODY,
#             self.right_finger_body_name,
#         )

#         if self.control_point == "gripper_center":
#             if self.left_finger_body_id < 0:
#                 raise RuntimeError(f"Cannot find body: {self.left_finger_body_name}")
#             if self.right_finger_body_id < 0:
#                 raise RuntimeError(f"Cannot find body: {self.right_finger_body_name}")

#         self.joint_ids = []
#         self.qpos_adrs = []
#         self.dof_adrs = []

#         for name in self.joint_names:
#             joint_id = mujoco.mj_name2id(
#                 self.model,
#                 mujoco.mjtObj.mjOBJ_JOINT,
#                 name,
#             )
#             if joint_id < 0:
#                 raise RuntimeError(f"Cannot find joint: {name}")

#             self.joint_ids.append(joint_id)
#             self.qpos_adrs.append(int(self.model.jnt_qposadr[joint_id]))
#             self.dof_adrs.append(int(self.model.jnt_dofadr[joint_id]))

#         self.qpos_adrs = np.asarray(self.qpos_adrs, dtype=np.int32)
#         self.dof_adrs = np.asarray(self.dof_adrs, dtype=np.int32)

#     def get_q(self):
#         return self.data.qpos[self.qpos_adrs].copy()

#     def set_q(self, q):
#         q = np.asarray(q, dtype=np.float64)
#         self.data.qpos[self.qpos_adrs] = q
#         mujoco.mj_forward(self.model, self.data)

#     def get_control_pos(self):
#         if self.control_point == "hand":
#             return self.data.xpos[self.ee_body_id].copy()

#         if self.control_point == "gripper_center":
#             left_pos = self.data.xpos[self.left_finger_body_id].copy()
#             right_pos = self.data.xpos[self.right_finger_body_id].copy()
#             return 0.5 * (left_pos + right_pos)

#         raise ValueError(f"Unknown control_point: {self.control_point}")

#     def get_control_jacobian(self):
#         if self.control_point == "hand":
#             jacp = np.zeros((3, self.model.nv), dtype=np.float64)
#             jacr = np.zeros((3, self.model.nv), dtype=np.float64)

#             mujoco.mj_jacBody(
#                 self.model,
#                 self.data,
#                 jacp,
#                 jacr,
#                 self.ee_body_id,
#             )

#             return jacp[:, self.dof_adrs]

#         if self.control_point == "gripper_center":
#             left_jacp = np.zeros((3, self.model.nv), dtype=np.float64)
#             left_jacr = np.zeros((3, self.model.nv), dtype=np.float64)

#             right_jacp = np.zeros((3, self.model.nv), dtype=np.float64)
#             right_jacr = np.zeros((3, self.model.nv), dtype=np.float64)

#             mujoco.mj_jacBody(
#                 self.model,
#                 self.data,
#                 left_jacp,
#                 left_jacr,
#                 self.left_finger_body_id,
#             )

#             mujoco.mj_jacBody(
#                 self.model,
#                 self.data,
#                 right_jacp,
#                 right_jacr,
#                 self.right_finger_body_id,
#             )

#             jacp = 0.5 * (left_jacp + right_jacp)
#             return jacp[:, self.dof_adrs]

#         raise ValueError(f"Unknown control_point: {self.control_point}")

#     def solve_position_ik(self, target_pos, q_init=None):
#         target_pos = np.asarray(target_pos, dtype=np.float64).reshape(3)

#         q_backup = self.get_q()

#         if q_init is None:
#             q = q_backup.copy()
#         else:
#             q = np.asarray(q_init, dtype=np.float64).copy()

#         success = False
#         final_error = np.inf

#         for _ in range(self.max_iters):
#             self.set_q(q)

#             current_pos = self.get_control_pos()
#             error = target_pos - current_pos
#             final_error = float(np.linalg.norm(error))

#             if final_error < self.pos_tol:
#                 success = True
#                 break

#             J = self.get_control_jacobian()

#             A = J @ J.T + self.damping * np.eye(3)
#             dq = J.T @ np.linalg.solve(A, error)

#             dq = self.step_size * dq
#             dq = np.clip(dq, -self.max_dq, self.max_dq)

#             q = q + dq

#         q_solution = q.copy()

#         # Restore original simulation state.
#         self.set_q(q_backup)

#         return q_solution, success, final_error
