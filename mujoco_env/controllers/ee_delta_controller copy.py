import numpy as np

from controllers.ik_solver import PandaIKSolver


class EEDeltaController:
    def __init__(
        self,
        model,
        data,
        joint_names,
        ee_body_name="hand",
        table_top_z=0.40,
        max_pos_delta=0.02,
        min_ee_z_above_table=0.03,
        workspace_low=(0.25, -0.35, 0.43),
        workspace_high=(0.85, 0.35, 0.95),
        open_gripper_ctrl=255.0,
        close_gripper_ctrl=0.0,
    ):
        self.model = model
        self.data = data
        self.joint_names = joint_names
        self.ee_body_name = ee_body_name

        self.table_top_z = table_top_z
        self.max_pos_delta = max_pos_delta
        self.min_ee_z_above_table = min_ee_z_above_table

        self.workspace_low = np.asarray(workspace_low, dtype=np.float64)
        self.workspace_high = np.asarray(workspace_high, dtype=np.float64)

        self.open_gripper_ctrl = float(open_gripper_ctrl)
        self.close_gripper_ctrl = float(close_gripper_ctrl)

        # self.ik = PandaIKSolver(
        #     model=model,
        #     data=data,
        #     joint_names=joint_names,
        #     ee_body_name=ee_body_name,
        #     damping=1e-3,
        #     max_iters=80,
        #     pos_tol=2e-3,
        #     step_size=0.7,
        #     max_dq=0.05,
        # )

        self.ik = PandaIKSolver(
            model=model,
            data=data,
            joint_names=joint_names,
            ee_body_name=ee_body_name,
            control_point="hand",
            damping=1e-3,
            max_iters=80,
            pos_tol=2e-3,
            step_size=0.7,
            max_dq=0.05,
        )


        self.last_q_target = self.ik.get_q()

    # def get_current_ee_pos(self):
    #     return self.ik.get_ee_pos()
    def get_current_ee_pos(self):
        return self.ik.get_control_pos()

    def gripper_action_to_ctrl(self, gripper):
        """
        Convention:
            gripper > 0: open
            gripper <= 0: close

        For Franka menagerie, ctrl[7] often uses:
            255.0 = open
            0.0   = close

        If your model behaves opposite, swap open_gripper_ctrl and close_gripper_ctrl.
        """
        if gripper > 0:
            return self.open_gripper_ctrl
        return self.close_gripper_ctrl

    def compute_control(
        self,
        dx,
        dy,
        dz,
        droll=0.0,
        dpitch=0.0,
        dyaw=0.0,
        gripper=1.0,
    ):
        """
        Input:
            dx, dy, dz: end-effector position delta in world frame, meters.
            droll, dpitch, dyaw: ignored in first version.
            gripper: >0 open, <=0 close.

        Returns:
            ctrl: np.ndarray, shape [model.nu]
            info: dict
        """
        del droll, dpitch, dyaw

        delta = np.array([dx, dy, dz], dtype=np.float64)
        delta = np.clip(delta, -self.max_pos_delta, self.max_pos_delta)

        current_pos = self.get_current_ee_pos()
        target_pos = current_pos + delta

        # Safety: keep end-effector above table.
        min_z = self.table_top_z + self.min_ee_z_above_table
        target_pos[2] = max(target_pos[2], min_z)

        # Safety: keep target inside workspace.
        target_pos = np.clip(target_pos, self.workspace_low, self.workspace_high)

        q_current = self.ik.get_q()
        q_target, ik_success, ik_error = self.ik.solve_position_ik(
            target_pos=target_pos,
            q_init=q_current,
        )

        if not ik_success:
            # If IK fails, hold current joints.
            q_target = q_current.copy()

        ctrl = np.zeros(self.model.nu, dtype=np.float64)
        ctrl[:7] = q_target

        if self.model.nu >= 8:
            ctrl[7] = self.gripper_action_to_ctrl(gripper)

        self.last_q_target = q_target.copy()

        info = {
            "ik_success": bool(ik_success),
            "ik_error": float(ik_error),
            "current_pos": current_pos.astype(np.float32),
            "target_pos": target_pos.astype(np.float32),
            "delta": delta.astype(np.float32),
            "gripper_ctrl": float(ctrl[7]) if self.model.nu >= 8 else None,
        }

        return ctrl, info
