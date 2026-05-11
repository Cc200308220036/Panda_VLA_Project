from setuptools import find_packages
from setuptools import setup

setup(
    name='panda_mujoco_msgs',
    version='0.0.0',
    packages=find_packages(
        include=('panda_mujoco_msgs', 'panda_mujoco_msgs.*')),
)
