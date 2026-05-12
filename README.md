# Panda_VLA_Project
使用mujuco平台进行pand机械臂仿真工作

5.11晚上提交的版本主要针对于抓取任务中增加了place_xy_offset使得抓取batch任务成功率达到100%，因此作为一个存档记录

5.12
目前已经更新了数据集录制代码，在mujoco_env/datasets下的文件，目前可以成功录制200组数据，并打包zarr文件，通过验证replay也能够成功实现

规范代码结构：
    mujoco_env/datasets
    mujoco_env/data
    mujoco_env/experiments
改为
    mujoco_env/data_collection
    learning/datasets
    data/raw
    data/zarr
    data/metadata
    experiments
