import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/cyw/panda_vla_project/ros2_ws/install/panda_mujoco_control'
