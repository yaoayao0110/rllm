# SGC for classification task in rel-movielens1M
# Paper: Simplifying Graph Convolutional Networks. arXiv:1902.07153
# Test f1_score micro: 0.4048, macro: 0.1038
# Runtime: 23.6416s (on a single 32G GPU)
# Cost: N/A
# Description: Simply apply SGC to movielens.
# Movies are linked iff a certain number of users rate them samely.
# Features were llm embeddings from table data to vectors.


from __future__ import division
from __future__ import print_function

import time
import argparse
import numpy as np

# import math
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import f1_score

from models import SGC

import sys
path = "../../../../rllm/dataloader"
sys.path.append(path)
from load_data import load_data

t_total = time.time()

# Training settings
parser = argparse.ArgumentParser()
parser.add_argument('--no-cuda', action='store_true', default=False,
                    help='Disables CUDA training.')
parser.add_argument('--fastmode', action='store_true', default=False,
                    help='Validate during training pass.')
parser.add_argument('--seed', type=int, default=42, help='Random seed.')
parser.add_argument('--epochs', type=int, default=200,
                    help='Number of epochs to train.')
parser.add_argument('--lr', type=float, default=0.01,
                    help='Initial learning rate.')
parser.add_argument('--weight_decay', type=float, default=1e-4,
                    help='Weight decay (L2 loss on parameters).')
parser.add_argument('--dropout', type=float, default=0.5,
                    help='Dropout rate (1 - keep probability).')

args = parser.parse_args()
args.cuda = not args.no_cuda and torch.cuda.is_available()
device = 'cuda' if args.cuda else 'cpu'

np.random.seed(args.seed)
torch.manual_seed(args.seed)
if args.cuda:
    torch.cuda.manual_seed(args.seed)

# Load data
data, adj, features, labels, \
    idx_train, idx_val, idx_test \
    = load_data('movielens-classification', device=device)

# Model and optimizer
model = SGC(nfeat=features.shape[1],
            nclass=labels.shape[1]).to(device)
optimizer = optim.Adam(model.parameters(),
                       lr=args.lr, weight_decay=args.weight_decay)

loss_func = nn.BCEWithLogitsLoss()


def train(epoch):
    t = time.time()
    model.train()
    optimizer.zero_grad()
    output = model(features, adj)
    pred = np.where(output.cpu() > -1.0, 1, 0)

    loss_train = loss_func(output[idx_train], labels[idx_train])
    f1_micro_train = f1_score(labels[idx_train].cpu(),
                              pred[idx_train.cpu()], average="micro")
    f1_macro_train = f1_score(labels[idx_train].cpu(),
                              pred[idx_train.cpu()], average="macro")
    loss_train.backward()
    optimizer.step()

    if not args.fastmode:
        # Evaluate validation set performance separately,
        # deactivates dropout during validation run.
        model.eval()
        output = model(features, adj)

    loss_val = loss_func(output[idx_val], labels[idx_val])
    f1_micro_val = f1_score(labels[idx_val].cpu(),
                            pred[idx_val.cpu()], average="micro")
    f1_macro_val = f1_score(labels[idx_val].cpu(),
                            pred[idx_val.cpu()], average="macro")

    print('Epoch: {:04d}'.format(epoch+1),
          'loss_train: {:.4f}'.format(loss_train.item()),
          'f1_train: {:.4f} {:.4f}'.format(f1_micro_train, f1_macro_train),
          'loss_val: {:.4f}'.format(loss_val.item()),
          'f1_val: {:.4f} {:.4f}'.format(f1_micro_val, f1_macro_val),
          'time: {:.4f}s'.format(time.time() - t))


def test():
    model.eval()
    output = model(features, adj)
    pred = np.where(output.cpu() > -1.0, 1, 0)
    loss_test = loss_func(output[idx_test], labels[idx_test])
    f1_micro_test = f1_score(labels[idx_test].cpu(),
                             pred[idx_test.cpu()], average="micro")
    f1_macro_test = f1_score(labels[idx_test].cpu(), pred[idx_test.cpu()],
                             average="macro")
    print("Test set results:",
          "loss = {:.4f}".format(loss_test.item()),
          "f1_macro_test = {:.4f} f1_micro_test = {:.4f}".format
          (f1_macro_test, f1_micro_test))


# Train model
for epoch in range(args.epochs):
    train(epoch)
print("Optimization Finished!")
print("Total time elapsed: {:.4f}s".format(time.time() - t_total))

# Testing
test()
