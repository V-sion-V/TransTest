﻿import os.path

import cv2

import torch
from torch.utils.data import DataLoader

import dataset
import opt
import utils
from model import GSRNet

eval_set = dataset.get_dataset(train=False)
eval_loader = DataLoader(eval_set, batch_size=opt.test_batch_size, shuffle=False)

def load_model(ckpt_path):
    model = GSRNet(opt.HR_image_size, opt.window_size, opt.num_heads, 
                opt.num_channels_list, opt.num_conv_down_layers_list, opt.num_conv_up_layers_list, 
                opt.dropout, opt.upsample_mode).to(opt.gpu)

    checkpoint = torch.load(ckpt_path, map_location=opt.gpu)
    new_state_dict = {}
    for k, v in checkpoint.items():
        if(k.startswith("module.")):
            new_key = k.replace("module.", "")  # 弱智数据并行
            new_state_dict[new_key] = v

    model.load_state_dict(new_state_dict)
    model.eval()
    
    return model

model = load_model("./checkpoints/v3.0 one model/GSRNet_2025-03-08_16-13-20/model58.pth")

total_ssim = 0
total_psnr = 0

with torch.no_grad():
    for (idx, data) in enumerate(eval_loader):
        lr, hr, guide = data["LR"].to(opt.gpu), data["HR"].to(opt.gpu), data["Guide"].to(opt.gpu)
        pred_hr = model(lr, guide)
        pred_hr = torch.clamp(pred_hr, 0, 1)
        ssim = utils.ssim(pred_hr, hr).item()
        psnr = utils.psnr(pred_hr, hr).item()
        total_ssim += ssim
        total_psnr += psnr
        print(f"Image {idx} SSIM: {ssim}, PSNR: {psnr}")

        for i in range(opt.test_batch_size):
            pred_hr_img = pred_hr[i].detach().permute(1, 2, 0).cpu().numpy() * 255

            cv2.imwrite(str(os.path.join(opt.output_dir, data['Name'][i])), pred_hr_img.astype('uint8'))

    total_ssim /= eval_loader.__len__()
    total_psnr /= eval_loader.__len__()

    print(f"Average SSIM: {total_ssim}, Average PSNR: {total_psnr}")