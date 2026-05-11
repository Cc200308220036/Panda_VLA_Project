import enum
import numpy as np

"""
该版本未加入了place_xy_offset，有grasp_xy_offset
"""
class PickPlaceStage(enum.Enum):
    MOVE_ABOVE_CUBE = 0
    MOVE_TO_GRASP = 1
    CLOSE_GRIPPER = 2
    LIFT = 3
    MOVE_ABOVE_TARGET = 4
    MOVE_TO_PLACE = 5
    OPEN_GRIPPER = 6
    RETREAT = 7
    DONE = 8


class ScriptedPickPlaceExpert:
    """
    Scripted top-down pick-and-place expert.

    It outputs:
        action = [dx, dy, dz, droll, dpitch, dyaw, gripper]

    Convention:
        gripper > 0: open
        gripper <= 0: close

    This expert uses object privileged state:
        cube_pos
        target_pos

    That is fine for generating demonstrations.
    But cube_pos / target_pos should NOT be used as policy input later.
    """

    def __init__(
        self,
        env,
        max_delta=0.010,
        reach_tol=0.015,
        z_reach_tol=0.012,
        pregrasp_height=0.20,
        grasp_height=0.105,
        lift_height=0.25,
        place_height=0.20,
        place_down_height=0.115,
        retreat_height=0.25,
        close_steps=50,
        open_steps=40,

        grasp_xy_offset=(0.0, 0.0),
        place_xy_offset=(0.0, 0.0),

    ):
        self.env = env

        self.max_delta = float(max_delta)
        self.reach_tol = float(reach_tol)
        self.z_reach_tol = float(z_reach_tol)

        # These heights are offsets relative to cube/target/table position.
        # They need tuning depending on which body you use as end-effector.
        self.pregrasp_height = float(pregrasp_height)
        self.grasp_height = float(grasp_height)
        self.lift_height = float(lift_height)
        self.place_height = float(place_height)
        self.place_down_height = float(place_down_height)
        self.retreat_height = float(retreat_height)

        self.close_steps = int(close_steps)
        self.open_steps = int(open_steps)

        self.grasp_xy_offset = np.asarray(grasp_xy_offset, dtype=np.float64)
        self.place_xy_offset = np.asarray(place_xy_offset, dtype=np.float64)


        self.stage = PickPlaceStage.MOVE_ABOVE_CUBE
        self.stage_step = 0

        self.grasp_xy = None
        self.target_xy = None

    def reset(self):
        self.stage = PickPlaceStage.MOVE_ABOVE_CUBE
        self.stage_step = 0
        self.grasp_xy = None
        self.target_xy = None

    def get_ee_pos(self):
        ee_pos, _ = self.env.get_ee_pose()
        return ee_pos.astype(np.float64)

    def get_cube_pos(self):
        return self.env.get_cube_pos().astype(np.float64)

    def get_target_pos(self):
        return self.env.get_target_pos().astype(np.float64)

    def make_action_to_target(self, target_pos, gripper):
        """
        Convert desired end-effector target position into small delta action.

        Policy:
        - MOVE_ABOVE_CUBE: if still not high enough, move up first.
        - MOVE_TO_GRASP: align xy before descending.
        - LIFT: allow small xy correction while lifting, do not set xy to zero.
        """
        ee_pos = self.get_ee_pos()
        target_pos = np.asarray(target_pos, dtype=np.float64)

        delta = target_pos - ee_pos
        xy_dist = np.linalg.norm(delta[:2])
        z_dist = abs(delta[2])

        if self.stage == PickPlaceStage.MOVE_ABOVE_CUBE:
            # First get close to pregrasp height, then move laterally.
            if z_dist > self.z_reach_tol:
                delta[0] = 0.0
                delta[1] = 0.0

            max_xy_delta = self.max_delta
            max_z_delta = self.max_delta

        elif self.stage == PickPlaceStage.MOVE_TO_GRASP:
            # Do not descend until xy is centered.
            if xy_dist > self.reach_tol:
                delta[2] = 0.0

            max_xy_delta = 0.004
            max_z_delta = 0.004

        elif self.stage == PickPlaceStage.CLOSE_GRIPPER:
            # Hold pose during closing, but still allow small correction.
            
            # 闭合夹爪时，不要继续下压。
            # 允许较强的 z 修正，把 hand 保持在抓取高度附近。
            if delta[2] < 0.0:
                delta[2] = 0.0
            max_xy_delta = 0.002
            max_z_delta = 0.002

        elif self.stage == PickPlaceStage.LIFT:
            # Important:
            # Do not zero xy. Allow small xy correction to keep hand above grasp point.
            # Lift slowly to reduce slipping.

            # LIFT 阶段明确向上抬，允许很小 xy 修正。
            if delta[2] < 0.0:
                delta[2] = 0.0
            max_xy_delta = 0.0015
            max_z_delta = 0.012
        
        elif self.stage == PickPlaceStage.RETREAT:
            if delta[2] < 0.0:
                delta[2] = 0.0

            max_xy_delta = 0.002
            max_z_delta = 0.012


        elif self.stage in [
            PickPlaceStage.MOVE_TO_PLACE,
            PickPlaceStage.OPEN_GRIPPER,
        ]:
            max_xy_delta = 0.004
            max_z_delta = 0.004

        else:
            max_xy_delta = self.max_delta
            max_z_delta = self.max_delta

        delta[0] = np.clip(delta[0], -max_xy_delta, max_xy_delta)
        delta[1] = np.clip(delta[1], -max_xy_delta, max_xy_delta)
        delta[2] = np.clip(delta[2], -max_z_delta, max_z_delta)

        action = np.zeros(7, dtype=np.float32)
        action[0:3] = delta.astype(np.float32)
        action[3:6] = 0.0
        action[6] = float(gripper)

        return action


    def reached_position(self, target_pos):
        ee_pos = self.get_ee_pos()
        target_pos = np.asarray(target_pos, dtype=np.float64)

        xy_dist = np.linalg.norm(ee_pos[:2] - target_pos[:2])
        z_dist = abs(ee_pos[2] - target_pos[2])

        return bool(xy_dist < self.reach_tol and z_dist < self.z_reach_tol)

    def advance_stage(self, next_stage):
        self.stage = next_stage
        self.stage_step = 0

    def get_current_target(self):
        """
        Return target end-effector position and gripper command for current stage.

        gripper:
            +1.0 open
            -1.0 close
        """
        cube_pos = self.get_cube_pos()
        target_pos = self.get_target_pos()

        cube_xy = cube_pos[:2]
        target_xy = target_pos[:2]
        place_xy = target_xy + self.place_xy_offset

        if self.grasp_xy is None and self.stage in [
            PickPlaceStage.MOVE_ABOVE_CUBE,
            PickPlaceStage.MOVE_TO_GRASP,
            PickPlaceStage.CLOSE_GRIPPER,
            PickPlaceStage.LIFT,
        ]:
            self.grasp_xy = cube_xy.copy()

            self.grasp_xy = cube_xy.copy() + self.grasp_xy_offset

        table_top_z = self.env.table_top_z

        if self.stage == PickPlaceStage.MOVE_ABOVE_CUBE:
            target_ee = np.array(
                [
                    self.grasp_xy[0],
                    self.grasp_xy[1],
                    self.env.cube_z + self.pregrasp_height,
                ],
                dtype=np.float64,
            )
            gripper = 1.0
            return target_ee, gripper

        if self.stage == PickPlaceStage.MOVE_TO_GRASP:
            target_ee = np.array(
                [
                    self.grasp_xy[0],
                    self.grasp_xy[1],
                    self.env.cube_z + self.grasp_height,
                ],
                dtype=np.float64,
            )
            gripper = 1.0
            return target_ee, gripper

        if self.stage == PickPlaceStage.CLOSE_GRIPPER:
            if self.grasp_xy is None:
                self.grasp_xy = cube_xy.copy()

            target_ee = np.array(
                [
                    self.grasp_xy[0],
                    self.grasp_xy[1],
                    self.env.cube_z + self.grasp_height,
                ],
                dtype=np.float64,
            )
            gripper = -1.0
            return target_ee, gripper

        if self.stage == PickPlaceStage.LIFT:
            if self.grasp_xy is None:
                self.grasp_xy = cube_xy.copy()

            target_ee = np.array(
                [
                    self.grasp_xy[0],
                    self.grasp_xy[1],
                    table_top_z + self.lift_height,
                ],
                dtype=np.float64,
            )
            gripper = -1.0
            return target_ee, gripper

        if self.stage == PickPlaceStage.MOVE_ABOVE_TARGET:
            if self.target_xy is None:
                self.target_xy = target_xy.copy()

            target_ee = np.array(
                [
                    self.target_xy[0],
                    self.target_xy[1],
                    table_top_z + self.place_height,
                ],
                dtype=np.float64,
            )
            gripper = -1.0
            return target_ee, gripper

        if self.stage == PickPlaceStage.MOVE_TO_PLACE:
            if self.target_xy is None:
                self.target_xy = target_xy.copy()

            target_ee = np.array(
                [
                    self.target_xy[0],
                    self.target_xy[1],
                    table_top_z + self.place_down_height,
                ],
                dtype=np.float64,
            )
            gripper = -1.0
            return target_ee, gripper

        if self.stage == PickPlaceStage.OPEN_GRIPPER:
            if self.target_xy is None:
                self.target_xy = target_xy.copy()

            target_ee = np.array(
                [
                    self.target_xy[0],
                    self.target_xy[1],
                    table_top_z + self.place_down_height,
                ],
                dtype=np.float64,
            )
            gripper = 1.0
            return target_ee, gripper

        if self.stage == PickPlaceStage.RETREAT:
            if self.target_xy is None:
                self.target_xy = target_xy.copy()

            target_ee = np.array(
                [
                    self.target_xy[0],
                    self.target_xy[1],
                    table_top_z + self.retreat_height,
                ],
                dtype=np.float64,
            )
            gripper = 1.0
            return target_ee, gripper

        # DONE
        ee_pos = self.get_ee_pos()
        return ee_pos, 1.0

    def update_stage(self, target_ee):
        """
        Advance finite-state machine when target reached or dwell time completed.
        """
        self.stage_step += 1

        if self.stage == PickPlaceStage.MOVE_ABOVE_CUBE:
            if self.reached_position(target_ee):
                self.advance_stage(PickPlaceStage.MOVE_TO_GRASP)

        elif self.stage == PickPlaceStage.MOVE_TO_GRASP:
            if self.reached_position(target_ee):
                self.advance_stage(PickPlaceStage.CLOSE_GRIPPER)

        elif self.stage == PickPlaceStage.CLOSE_GRIPPER:
            if self.stage_step >= self.close_steps:
                self.advance_stage(PickPlaceStage.LIFT)

        elif self.stage == PickPlaceStage.LIFT:
            if self.reached_position(target_ee):
                self.advance_stage(PickPlaceStage.MOVE_ABOVE_TARGET)

        elif self.stage == PickPlaceStage.MOVE_ABOVE_TARGET:
            if self.reached_position(target_ee):
                self.advance_stage(PickPlaceStage.MOVE_TO_PLACE)

        elif self.stage == PickPlaceStage.MOVE_TO_PLACE:
            if self.reached_position(target_ee):
                self.advance_stage(PickPlaceStage.OPEN_GRIPPER)

        elif self.stage == PickPlaceStage.OPEN_GRIPPER:
            if self.stage_step >= self.open_steps:
                self.advance_stage(PickPlaceStage.RETREAT)

        elif self.stage == PickPlaceStage.RETREAT:
            if self.reached_position(target_ee):
                self.advance_stage(PickPlaceStage.DONE)

    def get_action(self):
        """
        Main expert API.

        Returns:
            action: np.ndarray, shape [7]
            info: dict
        """
        target_ee, gripper = self.get_current_target()

        if self.stage == PickPlaceStage.DONE:
            action = np.zeros(7, dtype=np.float32)
            action[6] = 1.0
            return action, {
                "stage": self.stage.name,
                "target_ee": target_ee.astype(np.float32),
                "done": True,
            }

        action = self.make_action_to_target(target_ee, gripper)

        info = {
            "stage": self.stage.name,
            "target_ee": target_ee.astype(np.float32),
            "done": False,
        }

        self.update_stage(target_ee)

        return action, info
