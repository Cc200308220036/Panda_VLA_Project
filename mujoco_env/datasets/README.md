# Dataset Scripts

所有脚本建议从 `mujoco_env/` 根目录运行。
collect_scripted_pick_place_hdf5.py
    用当前成功链路采集 HDF5 demo

inspect_hdf5_episode.py
    检查单个 HDF5 文件结构、shape、metadata

replay_hdf5_episode.py
    读取一条 HDF5 action，用 controller + step_sim 回放

replay_hdf5_batch.py
    批量 replay 检查数据集复现率

build_dataset_index.py
    为 Diffusion Policy 构建 dataset_index.json

## 1. Collect debug dataset

```bash
python datasets/collect_scripted_pick_place_hdf5.py \
  --output_dir data/raw/pick_place_scripted_debug_10 \
  --num_episodes 10
