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

import os.path as osp
import os
import cv2

from e3po.utils import calculate_psnr_ssim
from e3po.utils.registry import evaluation_registry
from .base_eval import BaseEvaluation
from e3po.data import build_data


@evaluation_registry.register()
class FullTransmissionEvaluation(BaseEvaluation):
    """
    Full transmission Evaluation.

    Parameters
    ----------
    opt : dict
        Configurations.

    Notes
    -----
    Almost all class public attributes are directly read or indirectly processed from the yaml configuration file.
    Their specific meanings can be found in 'docs/Config.md'.
    """
    def __init__(self, opt):
        super(FullTransmissionEvaluation, self).__init__(opt)

        self.video_fps = opt['video']['video_fps']
        self.chunk_duration = opt['method_settings']['chunk_duration']
        self.base_frame_idx = int(self.pre_download_duration * self.video_fps // 1000.0)

    def evaluate_motion(self, fov_ts, fov_direction):
        """
        Evaluate a motion.

        Parameters
        ----------
        fov_ts : int
            FoV motion timestamp.
        fov_direction : dict
            Motion description information:
                {'yaw': yaw, 'pitch': pitch, 'scale': scale}

        Returns
        -------
        list
            Evaluation result list, which may be empty list.
        """
        if fov_ts <= self.base_ts + self.pre_download_duration:
            return []

        # Evaluate only once per frame.
        img_index = int((fov_ts - self.base_ts) * self.video_fps // 1000.0)
        if self.last_img_index == img_index:
            return []
        self.last_img_index = img_index

        tmp_psnr_ssim_flag = (self.psnr_flag or self.ssim_flag) and (img_index - self.base_frame_idx) % self.psnr_ssim_frequency == 0
        self.out_percent.append(0)
        if tmp_psnr_ssim_flag:
            psnr, ssim = self._calculate_psnr_ssim(fov_direction, img_index)
            self.psnr.append(psnr)
            self.ssim.append(ssim)
            self.logger.info(
                f"[evaluation] ts:{fov_ts}, frame_idx:{img_index}, out_percent:0, psnr:{round(psnr, 3)}, ssim:{round(ssim, 3)}")
        else:
            psnr, ssim = [0, 0]

        return [{'motion_timestamp': fov_ts, 'frame_idx': img_index, 'location': 'in', 'out_area_percent': self.out_percent[-1], 'psnr': psnr, 'ssim': ssim}]

    def _calculate_psnr_ssim(self, fov_direction, img_index):
        """
        Calculate PSNR and SSIM.

        Parameters
        ----------
        fov_direction : dict
            Motion description information:
                {'yaw': yaw, 'pitch': pitch, 'scale': scale}
        img_index : int
            Frame number corresponding to fov.

        Returns
        -------
        list
            [psnr, ssim].
        """
        converted_width = self.opt['video']['converted']['width']
        converted_height = self.opt['video']['converted']['height']

        self.logger.debug(f'[evaluation] start read client img')
        # The default full transmission scheme transmits the highest quality.
        client_img = self.extract_frame(self.projection_mode, min(self.quality_list), img_index)
        client_img[0][0] = [128, 128, 128]
        self.logger.debug(f'[evaluation] end read client img')

        self.logger.debug(f'[evaluation] start cal fov_uv')
        fov_ypr = [float(fov_direction['yaw']), float(fov_direction['pitch']), 0]
        fov_uv = self.projection.sphere_to_uv(fov_ypr, self.fov_resolution)
        self.logger.debug(f'[evaluation] end cal fov_uv')

        self.logger.debug(f'[evaluation] start get ground truth img')
        ground_truth = self._get_ground_truth_img(img_index, fov_uv, fov_direction)
        self.logger.debug(f'[evaluation] end get ground truth img')

        self.logger.debug(f'[evaluation] start generate client_img')
        fov_result = self.projection.get_fov(client_img, converted_width, converted_height, fov_uv)
        fov_result_name = osp.join(self.result_img_path, f"{img_index}.png")
        self.logger.debug(f'[evaluation] end generate client_img')

        self.logger.debug(f'[evaluation] start save img')
        if self.save_result_img_flag and not os.path.exists(fov_result_name):
            cv2.imwrite(fov_result_name, fov_result, [cv2.IMWRITE_JPEG_QUALITY,100])
        self.logger.debug(f'[evaluation] end save img')

        self.img2video('encode', fov_result)

        return calculate_psnr_ssim(ground_truth, fov_result, self.use_gpu, self.psnr_flag, self.ssim_flag)

    def evaluate_misc(self):
        """Calculate remaining evaluation indicators"""
        super(FullTransmissionEvaluation, self).evaluate_misc()

        total_tile_size = 0
        max_bandwidth = 0
        data = build_data(self.opt)
        # The pre-downloaded portion is not included in the playable_record.
        for chunk_idx in range(self.opt['method_settings']['pre_download_duration'], self.opt['video']['video_duration']):
            chunk_size = data.get_size(chunk_idx, max(self.quality_list))
            if max_bandwidth < chunk_size / self.chunk_duration:
                max_bandwidth = chunk_size / self.chunk_duration
            total_tile_size += chunk_size

        self.write_dict['MAX bandwidth'] = f"{round(max_bandwidth / 125 / 1000, 3)}Mbps"
        self.write_dict[
            'AVG bandwidth'] = f"{round(total_tile_size / (self.opt['video']['video_duration'] - self.pre_download_duration / 1000) / 125 / 1000, 3)}Mbps"
        self.write_dict['Total transfer size'] = f"{round(total_tile_size / 1000 / 1000, 6)}MB"
        return [self.write_dict]

