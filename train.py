﻿import os
import sys
import shutil
from datetime import datetime

import torch
import torchvision.utils
from torch.utils.data import DataLoader

from main import dataset, utils
import opt
from main.model import get_model

from tensorboardX import SummaryWriter
import torchvision.utils as vutils

train_set = dataset.get_dataset(mode='train', progressive=opt.progressive, start_scale=opt.start_scale)
train_loader = DataLoader(train_set, batch_size=opt.batch_size, shuffle=True)

eval_set = dataset.get_dataset(mode='eval', progressive=opt.progressive, start_scale=opt.start_scale)
eval_loader = DataLoader(eval_set, batch_size=opt.batch_size, shuffle=False)

model = get_model(opt.model_name)
if torch.cuda.device_count() > 1 and opt.data_parallel:
    model = torch.nn.DataParallel(model)
model.to(opt.gpu)
optim = torch.optim.Adam(model.parameters(), lr=opt.learning_rate)
scheduler = torch.optim.lr_scheduler.StepLR(optim, step_size=opt.lr_decay_step, gamma=opt.lr_decay_rate)

start_train_datetime = datetime.now()
start_train_time_str = str(start_train_datetime).split(" ")[0] + '_' + start_train_datetime.strftime("%H-%M-%S")
current_checkpoint_dir = os.path.join(opt.checkpoints_dir, f"GSRNet_{start_train_time_str}")
print(f"Checkpoints saved in directory: {current_checkpoint_dir}")
os.mkdir(current_checkpoint_dir)
shutil.copy("opt.py", os.path.join(current_checkpoint_dir, "opt.txt"))

writer = SummaryWriter(logdir=os.path.join(opt.tensorboard_log_dir, f"GSRNet_{start_train_time_str}"))

for epoch in range(1, opt.epochs+1):
    model.train()
    total_train_loss = 0
    range_train_loss = 0
    for (batch_idx, data) in enumerate(train_loader):
        lr, hr, guide = data["LR"].to(opt.gpu), data["HR"].to(opt.gpu), data["Guide"].to(opt.gpu)
        optim.zero_grad()
        pred_hr = model(lr, guide)
        pred_hr = torch.clamp(pred_hr, 0, 1)
        loss = utils.calc_loss(pred_hr, hr)
        total_train_loss += loss.item()
        range_train_loss += loss.item()
        loss.backward()
        optim.step()

        writer.add_scalar(f'Train/BatchLoss', loss.item(), (epoch-1) * train_loader.__len__() + batch_idx)

        batch_to_print = train_loader.__len__() // opt.print_loss_in_one_epoch
        if batch_idx % batch_to_print == batch_to_print - 1:
            print(f"Epoch: {epoch}, {batch_idx * 1000 // train_loader.__len__() / 10:02.1f}%, "
                  f"Average Train Loss: {range_train_loss / batch_to_print:.16f}")
            sys.stdout.flush()
            range_train_loss = 0

    total_train_loss /= train_loader.__len__()
    scheduler.step()

    model.eval()
    with torch.no_grad():
        total_eval_loss = 0
        total_eval_psnr = 0
        total_eval_ssim = 0
        for (batch_idx, data) in enumerate(eval_loader):
            lr, hr, guide = data["LR"].to(opt.gpu), data["HR"].to(opt.gpu), data["Guide"].to(opt.gpu)
            pred_hr = model(lr, guide)
            pred_hr = torch.clamp(pred_hr, 0, 1)
            loss = utils.calc_loss(pred_hr, hr)
            total_eval_loss += loss.item()
            total_eval_psnr += utils.psnr(pred_hr, hr).item()
            total_eval_ssim += utils.ssim(pred_hr, hr).item()

            for i in range(lr.shape[0]):
                writer.add_image(f"Eval/Predict{data['Name'][i]}", pred_hr[i], epoch)

        total_eval_loss /= eval_loader.__len__()
        total_eval_psnr /= eval_loader.__len__()
        total_eval_ssim /= eval_loader.__len__()
        print(f"Epoch {epoch} Finished:")
        print(f"Total Train Loss: {total_train_loss}, Eval Loss: {total_eval_loss}")
        print(f"Eval PSNR: {total_eval_psnr}, Eval SSIM: {total_eval_ssim}")

        writer.add_scalar(f'Train/TotalLoss', total_train_loss, epoch)
        writer.add_scalar(f'Eval/TotalLoss', total_eval_loss, epoch)
        writer.add_scalar(f'Eval/PSNR', total_eval_psnr, epoch)
        writer.add_scalar(f'Eval/SSIM', total_eval_ssim, epoch)

    if epoch % opt.save_model_epoch == opt.save_model_epoch - 1:
        print(f"Epoch {epoch} model saved.")
        torch.save(model.state_dict(), os.path.join(current_checkpoint_dir, f"model{epoch}.pth"))

torch.save(model.state_dict(), os.path.join(current_checkpoint_dir, f"model{opt.epochs}.pth"))