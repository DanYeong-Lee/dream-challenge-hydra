import numpy as np
import linecache
import torch
from torch.utils.data import Dataset


base2vec = {"A": [1., 0., 0., 0.],
            "T": [0., 1., 0., 0.],
            "C": [0., 0., 1., 0.],
            "G": [0., 0., 0., 1.],
            "N": [0.25, 0.25, 0.25, 0.25]
           }

def seq2mat(seq, max_len=110):
    seq = seq[:max_len]
    mat = torch.tensor(list(map(lambda x: base2vec[x], seq)), dtype=torch.float32)
    mat = torch.cat([mat, torch.zeros((max_len - len(seq), 4), dtype=torch.float32)])
    return mat

def get_len(file):
    n = 0
    with open(file) as f:
        for line in f:
            n += 1
    
    return n


class MyDataset(Dataset):
    def __init__(self, file_path, fold_idx):
        self.file_path = file_path
        self.fold_idx = fold_idx
        self.length = len(fold_idx)
    
    def reverse_complement(self, fwd_tensor):
        temp = fwd_tensor.flip(0)
        rev_tensor = temp.index_select(dim=1, index=torch.LongTensor([1, 0, 3, 2]))
        
        return rev_tensor

    def __len__(self):
        return self.length
    
    def __getitem__(self, idx):
        line_idx = self.fold_idx[idx]
        line = linecache.getline(self.file_path, line_idx + 1).strip()
        seq, target = line.split("\t")
        X = seq2mat(seq)
        X_rev = self.reverse_complement(X)
        y = torch.tensor(float(target), dtype=torch.float32)
        
        return X, X_rev, y