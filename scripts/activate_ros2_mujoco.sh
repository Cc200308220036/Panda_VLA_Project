#!/bin/bash

source ~/venvs/ros2_mujoco/bin/activate
source /opt/ros/humble/setup.bash

export PYTHONPATH="$HOME/venvs/ros2_mujoco/lib/python3.10/site-packages:$PYTHONPATH"

if [ -f ~/panda_vla_project/ros2_ws/install/setup.bash ]; then
  source ~/panda_vla_project/ros2_ws/install/setup.bash
fi

echo "Activated ROS2 + MuJoCo bridge environment"
echo "Python: $(which python)"
echo "ROS_DISTRO: $ROS_DISTRO"
echo "PYTHONPATH includes venv site-packages"
