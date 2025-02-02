from typing import List
import math
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
    
    
class DropPosition(nn.Module):
    def __init__(self, p=0.1):
        super().__init__()
        self.p = p
    
    def forward(self, x):
        if not self.training: 
            return x
        # x: (N, C, L)
        n, c, l = x.size()
        mask = torch.bernoulli(1 - (torch.ones(n, 1, l) * self.p)).to(x.device)
        x = x * mask
        
        return x * 1 / (1 - p)
    

class Dropout1d(nn.Module):
    def __init__(self, p=0.1):
        super().__init__()
        self.p = p
    
    def forward(self, x):
        if not self.training: 
            return x
        # x: (N, C, L)
        n, c, l = x.size()
        mask = torch.bernoulli(1 - (torch.ones(n, c, 1) * self.p)).to(x.device)
        x = x * mask
        
        return x * 1 / (1 - p)

    
class ConvBlock(nn.Module):
    def __init__(
        self,
        input_dim: int = 4,
        out_dim: int = 320,
        kernel_size: int = 15,
        pool_size: int = 3,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.main = nn.Sequential(
            nn.Conv1d(in_channels=input_dim, out_channels=out_dim, kernel_size=kernel_size, padding="same"),
            nn.ReLU(),
            nn.MaxPool1d(pool_size),
            DropPosition(dropout)
        )
    
    def forward(self, x):
        # x: (N, C, L)
        
        return self.main(x)
    

class ConvBlock_DO(nn.Module):
    def __init__(
        self,
        input_dim: int = 4,
        out_dim: int = 320,
        kernel_size: int = 15,
        pool_size: int = 3,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.main = nn.Sequential(
            nn.Conv1d(in_channels=input_dim, out_channels=out_dim, kernel_size=kernel_size, padding="same"),
            nn.ReLU(),
            nn.MaxPool1d(pool_size),
            nn.Dropout(dropout)
        )
    
    def forward(self, x):
        # x: (N, C, L)
        
        return self.main(x)
    

class ConvBlock_DO1d(nn.Module):
    def __init__(
        self,
        input_dim: int = 4,
        out_dim: int = 320,
        kernel_size: int = 15,
        pool_size: int = 3,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.main = nn.Sequential(
            nn.Conv1d(in_channels=input_dim, out_channels=out_dim, kernel_size=kernel_size, padding="same"),
            nn.ReLU(),
            nn.MaxPool1d(pool_size),
            Dropout1d(dropout)
        )
    
    def forward(self, x):
        # x: (N, C, L)
        
        return self.main(x)


class DeepFamQ_multilayerLSTMDP(nn.Module):
    def __init__(
        self,
        conv_out_dim: int = 320,
        conv_kernel_size: List = [10, 15],
        pool_size: int = 3,
        lstm_hidden_dim: int = 320,
        fc_hidden_dim: int = 64,
        dropout1: float = 0.2,
        dropout2: float = 0.5,
        dropout3: float = 0.5
    ):
        super().__init__()
        pool_out_len = int(1 + ((110 - pool_size) / pool_size))
        fc_input_dim = lstm_hidden_dim * 2 * pool_out_len
        conv_each_dim = int(conv_out_dim / len(conv_kernel_size))
        
        self.conv_blocks = nn.ModuleList([ConvBlock_DO(4, conv_each_dim, k, pool_size, dropout1) for k in conv_kernel_size])
        self.lstm1 = nn.LSTM(input_size=conv_out_dim, hidden_size=lstm_hidden_dim, bidirectional=True)
        self.dp = DropPosition(dropout2)
        self.lstm2 = nn.LSTM(input_size=lstm_hidden_dim * 2, hidden_size=lstm_hidden_dim, bidirectional=True)
        
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(dropout3),
            nn.Linear(fc_input_dim, fc_hidden_dim),
            nn.ReLU(),
            nn.Linear(fc_hidden_dim, fc_hidden_dim),
            nn.ReLU(),
            nn.Linear(fc_hidden_dim, 1)
        )
        
    def forward(self, x):
        # x: (N, L, C)
        x = x.transpose(1, 2)  # (N, C, L)
        conv_outs = []
        for conv in self.conv_blocks:
            conv_outs.append(conv(x))
        x = torch.cat(conv_outs, dim=1)  # (N, C, L)
        x = x.permute(2, 0, 1)  # (L, N, C)
        x, (h, c) = self.lstm1(x)  # (L, N, C)
        x = x.permute(1, 2, 0)  # (N, C, L)
        x = self.dp(x)  # (N, C, L)
        x = x.permute(2, 0, 1)  # (L, N, C)
        x, (h, c) = self.lstm2(x, (h, c))  # (L, N, C)
        x = x.transpose(0, 1)  # (N, L, C)
        x = self.fc(x)
        x = x.squeeze()
        
        return x
    

class DeepFamQ_DO1d(nn.Module):
    def __init__(
        self,
        conv_out_dim: int = 320,
        conv_kernel_size: List = [10, 15],
        pool_size: int = 3,
        lstm_hidden_dim: int = 320,
        fc_hidden_dim: int = 64,
        dropout1: float = 0.2,
        dropout2: float = 0.5
    ):
        super().__init__()
        pool_out_len = int(1 + ((110 - pool_size) / pool_size))
        fc_input_dim = lstm_hidden_dim * 2 * pool_out_len
        conv_each_dim = int(conv_out_dim / len(conv_kernel_size))
        
        self.conv_blocks = nn.ModuleList([ConvBlock_DO1d(4, conv_each_dim, k, pool_size, dropout1) for k in conv_kernel_size])
        self.lstm = nn.LSTM(input_size=conv_out_dim, hidden_size=lstm_hidden_dim, bidirectional=True)
        
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(dropout2),
            nn.Linear(fc_input_dim, fc_hidden_dim),
            nn.ReLU(),
            nn.Linear(fc_hidden_dim, fc_hidden_dim),
            nn.ReLU(),
            nn.Linear(fc_hidden_dim, 1)
        )
        
    def forward(self, x):
        # x: (N, L, C)
        x = x.transpose(1, 2)  # (N, C, L)
        conv_outs = []
        for conv in self.conv_blocks:
            conv_outs.append(conv(x))
        x = torch.cat(conv_outs, dim=1)  # (N, C, L)
        x = x.permute(2, 0, 1)  # (L, N, C)
        x, (h, c) = self.lstm(x)  # (L, N, C)
        x = x.permute(1, 2, 0)  # (N, C, L)
        x = self.fc(x)
        x = x.squeeze()
        
        return x
