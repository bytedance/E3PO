# E3PO, an open platform for 360˚ video streaming simulation and evaluation.
# Copyright 2023 ByteDance Ltd. and/or its affiliates
#
# This file is part of E3PO.
#
# E3PO is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# E3PO is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see:
#    <https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html>

import cv2
import numpy as np
import torch
import torch.nn.functional as fun
from .logger import get_logger


def calculate_psnr_ssim_mse(img1_uri, img2_uri, use_cuda_flag=False, psnr_flag=True, ssim_flag=True):
    """
    Calculate PSNR (Peak Signal-to-Noise Ratio) or/and SSIM (structural similarity) for two input images.

    Parameters
    ----------
    img1_uri : ndarray
        The range of each pixel value is [0, 255].
    img2_uri : ndarray
        The range of each pixel value is [0, 255].
    use_cuda_flag : bool
        Whether to use cuda to accelerate operations.
    psnr_flag : bool
        Whether to calculate psnr.
    ssim_flag : bool
        Whether to calculate ssim.

    Returns
    -------
    list
        [psnr, ssim]
    """
    img1 = np.array(cv2.imread(img1_uri))
    img2 = np.array(cv2.imread(img2_uri))
    assert img1.shape == img2.shape, f'[error] Input images have different shapes: {img1.shape}, {img2.shape}!'
    psnr = 0
    ssim = 0
    mse = 0
    _logger = get_logger()
    if use_cuda_flag:
        img1 = torch.from_numpy(img1.transpose(2, 0, 1)).float()
        img2 = torch.from_numpy(img2.transpose(2, 0, 1)).float()
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        if psnr_flag:
            _logger.debug(f'[evaluation] start cal psnr')
            img1_ = img1.to(dtype=torch.float64, device=device)
            img2_ = img2.to(dtype=torch.float64, device=device)
            mse = torch.mean((img1_ - img2_) ** 2, dim=[0, 1, 2])
            psnr = float(10. * torch.log10(255. * 255. / (mse + 1e-8)))
            _logger.debug(f'[evaluation] end cal psnr')
        if ssim_flag:
            _logger.debug(f'[evaluation] start cal ssim')
            img1_ = img1.unsqueeze(0).to(dtype=torch.float64, device=device)
            img2_ = img2.unsqueeze(0).to(dtype=torch.float64, device=device)
            ssim = float(_cal_ssim_gpu(img1_, img2_))
            _logger.debug(f'[evaluation] end cal ssim')
    else:
        img1 = img1.astype(np.float64)
        img2 = img2.astype(np.float64)
        if psnr_flag:
            _logger.debug(f'[evaluation] start cal psnr')
            mse = np.mean((img1 - img2) ** 2)
            if mse == 0:
                psnr = float('inf')
            else:
                psnr = 10. * np.log10(255. * 255. / mse)
            _logger.debug(f'[evaluation] end cal psnr')
        if ssim_flag:
            _logger.debug(f'[evaluation] start cal ssim')
            ssims = []
            for i in range(img1.shape[2]):
                ssims.append(_cal_ssim(img1[..., i], img2[..., i]))
            ssim = np.array(ssims).mean()
            _logger.debug(f'[evaluation] end cal ssim')
    return psnr, ssim, mse


def _cal_ssim(img1, img2):
    """
    Calculate the SSIM (structural similarity index measure) metric for two input images.

    Parameters
    ----------
    img1 : ndarray
        The range of each pixel value is [0, 255].
    img2 : ndarray
        The range of each pixel value is [0, 255].

    Returns
    -------
    float
        The calculated SSIM result.
    """
    k_1 = 0.01
    k_2 = 0.03
    L = 255                                            # The dynamic range of pixel-value: 2^8 - 1

    c_1 = (k_1 * L) ** 2
    c_2 = (k_2 * L) ** 2
    ssim_kernel = cv2.getGaussianKernel(11, 1.5)       # The gaussianKernel
    ssim_window = np.outer(ssim_kernel, ssim_kernel.transpose())
    mean_img1 = cv2.filter2D(img1, -1, ssim_window)[5:-5, 5:-5]
    mean_img2 = cv2.filter2D(img2, -1, ssim_window)[5:-5, 5:-5]

    mean_img1_square = mean_img1 ** 2
    mean_img2_square = mean_img2 ** 2
    mean_img1_img2 = mean_img1 * mean_img2

    var_img1 = cv2.filter2D(img1**2, -1, ssim_window)[5:-5, 5:-5] - mean_img1_square
    var_img2 = cv2.filter2D(img2**2, -1, ssim_window)[5:-5, 5:-5] - mean_img2_square
    var_img12 = cv2.filter2D(img1 * img2, -1, ssim_window)[5:-5, 5:-5] - mean_img1_img2

    ssim_img12 = ((2 * mean_img1_img2 + c_1) * (2 * var_img12 + c_2)) / \
                 ((mean_img1_square + mean_img2_square + c_1) * (var_img1 + var_img2 + c_2))

    return ssim_img12.mean()


def _cal_ssim_gpu(img1, img2):
    """
    Calculate the SSIM (structural similarity index measure) metric for two input images, with GPU acceleration.

    Parameters
    ----------
    img1 : Tensor
        The range of each pixel value is [0, 255], shape (1, 3/1, h, w).
    img2 : Tensor
        The range of each pixel value is [0, 255], shape (1, 3/1, h, w).

    Returns
    -------
    float
        The calculated SSIM result.
    """
    k_1 = 0.01
    k_2 = 0.03
    L = 255                 # The dynamic range of pixel-value: 2^8 - 1

    c_1 = (k_1 * L) ** 2
    c_2 = (k_2 * L) ** 2
    ssim_kernel = cv2.getGaussianKernel(11, 1.5)       # The gaussianKernel
    ssim_window = np.outer(ssim_kernel, ssim_kernel.transpose())

    ssim_window = torch.from_numpy(ssim_window).view(1, 1, 11, 11).expand(img1.size(1), 1, 11, 11).to(img1.dtype).to(img1.device)
    mean_img1 = fun.conv2d(img1, ssim_window, stride=1, padding=0, groups=img1.shape[1])
    mean_img2 = fun.conv2d(img2, ssim_window, stride=1, padding=0, groups=img2.shape[1])

    mean_img1_square = mean_img1 ** 2
    mean_img2_square = mean_img2 ** 2
    mean_img1_img2 = mean_img1 * mean_img2

    var_img1 = fun.conv2d(img1 ** 2, ssim_window, stride=1, padding=0, groups=img1.shape[1]) - mean_img1_square
    var_img2 = fun.conv2d(img2 ** 2, ssim_window, stride=1, padding=0, groups=img1.shape[1]) - mean_img2_square
    var_img12 = fun.conv2d(img1 * img2, ssim_window, stride=1, padding=0, groups=img1.shape[1]) - mean_img1_img2

    ssim_img12 = ((2 * mean_img1_img2 + c_1) * (2 * var_img12 + c_2)) / \
                 ((mean_img1_square + mean_img2_square + c_1) * (var_img1 + var_img2 + c_2))

    return ssim_img12.mean([0, 1, 2, 3])
