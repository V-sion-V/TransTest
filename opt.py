﻿import torch

# Data
train_dataset_path = './dataset/train'
eval_dataset_path = './dataset/val'
lr_dir_name = 'thermal/LR_x8'
guide_dir_name = 'visible'
hr_dir_name = 'thermal/GT'
HR_image_size = (448, 640)

# Model
batch_size = 2
window_size = (7, 10)
num_heads = 8
num_channels_list = [64, 128, 256]
num_conv_down_layers_list = [3, 3, 3]
num_conv_up_layers_list = [3, 3, 3]
dropout = 0.5

# Loss
pixel_loss_method = torch.nn.functional.mse_loss
pixel_loss_weight = 0.8
ssim_loss_weight = 0.1
gradient_loss_weight = 0.1

# Train
epochs = 100
print_loss_in_one_epoch = 20
save_model_epoch = 1
checkpoints_dir = 'checkpoints'

# Device
gpu = torch.device('cuda:0') # Set to cuda:0 in DataParallel

# Eval
test_batch_size = 4
output_dir = 'output'
checkpoint_path = "./checkpoints/GSRNet_2025-03-08_04-05-41/model28.pth"
