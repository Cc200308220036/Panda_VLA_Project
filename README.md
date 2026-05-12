# Panda_VLA_Project
使用mujuco平台进行pand机械臂仿真工作

## 5.11
晚上提交的版本主要针对于抓取任务中增加了place_xy_offset使得抓取batch任务成功率达到100%，因此作为一个存档记录

## 5.12
### 代码规范记录
目前已经更新了数据集录制代码，在mujoco_env/datasets下的文件，目前可以成功录制200组数据，并打包zarr文件，通过验证replay也能够成功实现
```
```bash
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
```bash
```
### BC训练记录
#### 训练脚本参数
```
固定场景
```bash
python -m learning.diffusion_policy.train_bc_privileged_state \
  --zarr_path data/zarr/pick_place_scripted_200.zarr \
  --output_dir experiments/bc_privileged_state_v2 \
  --state_mode relative \
  --obs_horizon 2 \
  --pred_horizon 16 \
  --batch_size 256 \
  --epochs 100
```bash

随机场景
```bash
python -m learning.diffusion_policy.eval_bc_privileged_state_rollout \
  --checkpoint experiments/bc_privileged_state_v2/best.pt \
  --stats_path experiments/bc_privileged_state_v2/privileged_state_stats.json \
  --output_dir experiments/bc_privileged_state_v2/eval_random_50 \
  --num_episodes 50 \
  --start_seed 1000 \
  --max_steps 2000 \
  --save_video \
  --video_fps 20
```bash
```