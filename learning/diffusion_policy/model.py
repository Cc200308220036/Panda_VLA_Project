"""
实现目标：
    定义 state-only Behavior Cloning 策略网络。
    该模型用于 Diffusion Policy 之前的 baseline sanity check：
    输入连续若干步 robot_state，直接回归未来若干步 action。

输入：
    state:
        torch.Tensor
        shape = [batch_size, obs_horizon, state_dim]
        内容是已经归一化后的 robot_state 序列。

输出：
    action_pred:
        torch.Tensor
        shape = [batch_size, pred_horizon, action_dim]
        内容是已经归一化后的 action 预测序列。

说明：
    当前模型不使用图像，不使用语言，只使用 robot_state。
    它的目的不是追求最终任务成功率，而是验证数据集、归一化、训练循环和 checkpoint 流程是否正确。
"""

import torch
import torch.nn as nn


class StateBCPolicy(nn.Module):
    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        obs_horizon: int,
        pred_horizon: int,
        hidden_dim: int = 256,
        dropout: float = 0.0,
    ):
        super().__init__()

        self.state_dim = int(state_dim)
        self.action_dim = int(action_dim)
        self.obs_horizon = int(obs_horizon)
        self.pred_horizon = int(pred_horizon)

        input_dim = self.obs_horizon * self.state_dim
        output_dim = self.pred_horizon * self.action_dim

        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.SiLU(),
            nn.Dropout(dropout),

            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.SiLU(),
            nn.Dropout(dropout),

            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.SiLU(),

            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """
        输入：
            state:
                shape = [B, obs_horizon, state_dim]

        输出：
            action_pred:
                shape = [B, pred_horizon, action_dim]
        """
        if state.ndim != 3:
            raise ValueError(
                f"state should have shape [B, obs_horizon, state_dim], "
                f"but got {tuple(state.shape)}"
            )

        batch_size, obs_horizon, state_dim = state.shape

        if obs_horizon != self.obs_horizon:
            raise ValueError(
                f"obs_horizon mismatch: model={self.obs_horizon}, input={obs_horizon}"
            )

        if state_dim != self.state_dim:
            raise ValueError(
                f"state_dim mismatch: model={self.state_dim}, input={state_dim}"
            )

        x = state.reshape(batch_size, self.obs_horizon * self.state_dim)
        y = self.net(x)
        y = y.reshape(batch_size, self.pred_horizon, self.action_dim)

        return y


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
