import numpy as np
import linecache
import torch
from torch.utils.data import Dataset
from Bio.Seq import Seq


def get_len(file):
    n = 0
    with open(file) as f:
        for line in f:
            n += 1
    
    return n

class OneHotDataset(Dataset):
    def __init__(
        self, 
        df,
        fold_idx
    ):
        self.records = df.to_records()
        self.fold_idx = fold_idx
        self.base2vec = {
            "A": [1., 0., 0., 0.],
            "T": [0., 1., 0., 0.],
            "C": [0., 0., 1., 0.],
            "G": [0., 0., 0., 1.],
            "N": [0.25, 0.25, 0.25, 0.25]
        }
    
    def seq2mat(self, seq, max_len=110):
        seq = seq[:max_len]
        mat = torch.tensor(list(map(lambda x: self.base2vec[x], seq)), dtype=torch.float32)
        mat = torch.cat([mat, torch.zeros((max_len - len(seq), 4), dtype=torch.float32)])
        return mat
    
    def reverse_complement(self, fwd_tensor):
        temp = fwd_tensor.flip(0)
        rev_tensor = temp.index_select(dim=1, index=torch.LongTensor([1, 0, 3, 2]))
        
        return rev_tensor

    def __len__(self):
        return len(self.fold_idx)
    
    def __getitem__(self, idx):
        line_idx = self.fold_idx[idx]
        _, seq, target = self.records[line_idx]
        X = self.seq2mat(seq)
        X_rev = self.reverse_complement(X)
        y = torch.tensor(float(target), dtype=torch.float32)
        
        return X, X_rev, y

    
class IndexDataset(Dataset):
    def __init__(
        self, 
        df,
        fold_idx
    ):
        self.records = df.to_records()
        self.fold_idx = fold_idx
        self.base2idx = {"A": 0, "T": 1, "C": 2, "G": 3, "N": 4}
    
    def seq2vec(self, seq, max_len=110):
        seq = seq[:max_len]
        mat = torch.tensor(list(map(lambda x: self.base2idx[x], seq)), dtype=torch.long)
        mat = torch.cat([mat, 4 * torch.ones(max_len - len(seq), dtype=torch.long)])
        return mat

    def __len__(self):
        return len(self.fold_idx)
    
    def __getitem__(self, idx):
        line_idx = self.fold_idx[idx]
        _, seq, target = self.records[line_idx]
        seq, target = line.split("\t")
        X = self.seq2vec(seq)
        X_rev = self.seq2vec(Seq(seq).reverse_complement())
        y = torch.tensor(float(target), dtype=torch.float32)
        
        return X, X_rev, y