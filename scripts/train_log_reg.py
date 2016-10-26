#!/bin/sh
''''exec python3 -u -- "$0" ${1+"$@"} # '''

# #! /usr/bin/env python3
# Copyright 2016 Euclidean Technologies Management LLC All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import time
import os
import sys
import copy
import pickle

import numpy as np
import tensorflow as tf
from sklearn.linear_model import LogisticRegression

import model_utils
from model_utils import get_tabular_data
import configs

from tensorflow.python.platform import gfile
from batch_generator import BatchGenerator


"""
Entry point and main loop for train_net.py. Uses command line arguments to get
model and training specification (see config.py).
"""
configs.DEFINE_string("train_datafile", '',"Training file")
configs.DEFINE_float("lr_decay",0.9, "Learning rate decay")
configs.DEFINE_float("initial_learning_rate",1.0,"Initial learning rate")
configs.DEFINE_float("validation_size",0.0,"Size of validation set as %")
configs.DEFINE_integer("passes",1,"Passes through day per epoch")
configs.DEFINE_integer("max_epoch",0,"Stop after max_epochs")
configs.DEFINE_integer("early_stop",None,"Early stop parameter")
configs.DEFINE_integer("seed",None,"Seed for deterministic training")

config = configs.get_configs()

train_path = model_utils.get_data_path(config.data_dir,config.train_datafile)

print("Loading training data ...")

rand_samp = True if config.use_fixed_k is True else False

VALID_MODE = True

############################################################################
#   If cached data doesn't exist, build it
############################################################################
if not config.use_cache:
    print("Generating Data from Scratch")

    data_bg = BatchGenerator(train_path, config,
          config.batch_size, config.num_unrollings,
          validation_size=config.validation_size,
          randomly_sample=False, valid_mode=VALID_MODE)

    train_bg = data_bg.train_batches()
    valid_bg = data_bg.valid_batches()

    print("Grabbing tabular data from batch generator")
    X_train_full, Y_train_full, dates_train = get_tabular_data(train_bg)
    X_valid_full, Y_valid_full, dates_valid = get_tabular_data(valid_bg)


############################################################################
#   Else load from cache
############################################################################
else:
    print("Loading data from cache (expecting to find ./datasets/rectangular/*.npy)")
    X_train_full = np.load(os.environ['DNN_QUANT_ROOT'] + "/datasets/rectangular/X_train_full.npy")
    Y_train_full = np.load(os.environ['DNN_QUANT_ROOT'] + "/datasets/rectangular/Y_train_full.npy")
    X_valid_full = np.load(os.environ['DNN_QUANT_ROOT'] + "/datasets/rectangular/X_valid_full.npy")
    Y_valid_full = np.load(os.environ['DNN_QUANT_ROOT'] + "/datasets/rectangular/Y_valid_full.npy")
    dates_train = np.load(os.environ['DNN_QUANT_ROOT'] + "/datasets/rectangular/dates_train.npy")
    dates_valid = np.load(os.environ['DNN_QUANT_ROOT'] + "/datasets/rectangular/dates_valid.npy")

#############################################################################
#   Take only those rows that finish before the end date
#############################################################################
train_indices = [i for i in range(len(dates_train)) if dates_train[i] <= config.end_date]
valid_indices = [i for i in range(len(dates_valid)) if dates_valid[i] <= config.end_date]

X_train = X_train_full[train_indices]
Y_train = Y_train_full[train_indices]
X_valid = X_valid_full[valid_indices]
Y_valid = Y_valid_full[valid_indices]

print("Data processing complete")

############################################################################
#   Instantiate logistic regression classifier (sk-learn) and train
############################################################################
clf = LogisticRegression(C=1)
print("Training logistic regression classifer")
clf.fit(X_train, Y_train)

training_accuracy = np.mean(clf.predict(X_train) == Y_train)
print("training accuracy: ", training_accuracy)

validation_accuracy = np.mean(clf.predict(X_valid) == Y_valid)
print("validation accuracy: ", validation_accuracy)

############################################################################
#   Save the model
############################################################################
if not os.path.exists(config.model_dir):
    print("Creating directory %s" % config.model_dir)
    os.mkdir(config.model_dir)

checkpoint_path = os.path.join(config.model_dir, "logreg.pkl" )

with open(checkpoint_path, "wb") as f:
    pickle.dump(clf, f)

