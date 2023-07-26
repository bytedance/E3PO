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
import json
import os
import numpy as np
import cv2
import shutil

from e3po.utils import calculate_psnr_ssim
from e3po.utils.registry import evaluation_registry
from .base_eval import BaseEvaluation
from e3po.data import build_data


@evaluation_registry.register()
class Freedom1Evaluation(BaseEvaluation):
    """
    Freedom1 Evaluation.

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
        super(Freedom1Evaluation, self).__init__(opt)

        self.data = build_data(opt)
        self.playable_record = self._decision_to_playable()
        self.video_fps = opt['video']['video_fps']
        self.base_frame_idx = int(self.pre_download_duration * self.video_fps // 1000.0)
        self.vam_size = opt['method_settings']['vam_size']
        self.crop_factor = [eval(v) for v in opt['method_settings']['crop_factor']]
        self.scale_factors = {k: eval(v) for k, v in opt['method_settings']['scale_factors'].items()}
        self.sampling_num = opt['metric']['sampling_size'][0] * opt['metric']['sampling_size'][1]
        self.range_num = opt['metric']['range_fov'][0] * opt['metric']['range_fov'][1]

    def _decision_to_playable(self):
        """Calculate the playable timestamp of each VAM on the client, and read the transmission amount of each chunk"""
        self.logger.info("[decision to playable] start")

        rendering_delay = self.opt['video']['rendering_delay']
        decision_location = self.opt['method_settings']['decision_location']
        assert decision_location in ['client', 'server'], "[error] Decision_location wrong. It should be set to the value in ['client', 'server']"
        rtt = self.opt['network_trace']['rtt'] * 0.5 if decision_location == 'server' else self.opt['network_trace']['rtt']
        bandwidth = self.opt['network_trace']['bandwidth']

        decision_path = osp.join(self.opt['project_path'], 'result', self.opt['test_group'], self.opt['method_name'], 'decision.json')
        with open(decision_path, encoding="utf-8") as f:
            decision_record = json.load(f)

        playable_record = {}
        for row in decision_record:
            for vam in row['decision_data'][1:]:
                vam_size = self.data.get_size(int(vam['vam_idx']), vam['qp'])
                download_delay = vam_size / bandwidth / 1000
                tmp_ts = vam['pw_ts'] + download_delay + rtt + rendering_delay
                playable_record[int(vam['vam_idx'])] = {'ts': tmp_ts, 'vam_size': vam_size, 'vam_motion': row['decision_data'][0]}

        self.logger.info("[decision to playable] end")
        return playable_record

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

        if img_index > list(self.playable_record.keys())[-1]:
            return []

        tmp_psnr_ssim_flag = (self.psnr_flag or self.ssim_flag) and (img_index - self.base_frame_idx) % self.psnr_ssim_frequency == 0
        if self.playable_record[img_index]['ts'] > fov_ts:
            self.logger.info(f"[evaluation] no content to play at {fov_ts}. img_index: {img_index}, playable_record_ts: {self.playable_record[img_index]['ts']}")
            if self.save_result_img_flag and os.path.exists(osp.join(self.result_img_path, f"{img_index - 1}.png")):
                shutil.copyfile(osp.join(self.result_img_path, f"{img_index - 1}.png"), osp.join(self.result_img_path, f"{img_index}.png"))
            if tmp_psnr_ssim_flag:
                self.psnr.append(0)
                self.ssim.append(0)
            self.out_percent.append(1)
            return [{'motion_timestamp': fov_ts, 'location': 'no_content', 'out_area_percent': 1, 'psnr': 0, 'ssim': 0}]

        client_fov_pitch = fov_direction['pitch']
        client_fov_yaw = fov_direction['yaw']
        client_fov = [client_fov_yaw, client_fov_pitch, 0]
        client_fov_uv = self.projection.sphere_to_uv(client_fov, self.opt['metric']['sampling_size'])
        coord_x, coord_y = self.projection.uv_to_coor(client_fov_uv, self.playable_record[img_index]['vam_motion'])
        coord_x[(coord_x >= 0) & (coord_x < self.vam_size[0])] = 0
        coord_y[(coord_y >= 0) & (coord_y < self.vam_size[1])] = 0
        coord_array = np.where((coord_x + coord_y), 0, 1)
        number_fov_in_vam = np.sum(coord_array)
        if number_fov_in_vam < self.sampling_num:
            location = 'out'
        else:
            location = 'in'
        self.out_percent.append(1 - number_fov_in_vam / self.sampling_num)

        if tmp_psnr_ssim_flag:
            psnr, ssim = self._calculate_psnr_ssim(fov_direction, img_index)
            self.psnr.append(psnr)
            self.ssim.append(ssim)
            self.logger.info(
                f"[evaluation] ts:{fov_ts}, frame_idx:{img_index}, out_percent:{round(self.out_percent[-1], 3)}, psnr:{round(psnr, 3)}, ssim:{round(ssim, 3)}")
        else:
            psnr, ssim = [0, 0]

        return [
            {'motion_timestamp': fov_ts, 'frame_idx': img_index, 'location': location, 'out_area_percent': self.out_percent[-1], 'psnr': psnr,
             'ssim': ssim}]

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
        self.logger.debug(f'[evaluation] start read client img')
        # If there is an adaptive bit rate, it should also be selected here.
        client_img = self.extract_frame(self.projection_mode, min(self.quality_list), img_index)
        self.logger.debug(f'[evaluation] end read client img')

        self.logger.debug(f'[evaluation] start cal fov_uv')
        fov_ypr = [float(fov_direction['yaw']), float(fov_direction['pitch']), 0]
        fov_uv = self.projection.sphere_to_uv(fov_ypr, self.fov_resolution)
        self.logger.debug(f'[evaluation] end cal fov_uv')

        self.logger.debug(f'[evaluation] start get ground truth img')
        ground_truth = self._get_ground_truth_img(img_index, fov_uv, fov_direction)
        self.logger.debug(f'[evaluation] end get ground truth img')

        self.logger.debug(f'[evaluation] start generate client_img')
        fov_result = self.projection.get_fov(client_img, fov_uv, self.playable_record[img_index]['vam_motion'])
        fov_result_name = osp.join(self.result_img_path, f"{img_index}.png")
        self.logger.debug(f'[evaluation] end generate client_img')

        self.logger.debug(f'[evaluation] start save img')
        if self.save_result_img_flag and not os.path.exists(fov_result_name):
            cv2.imwrite(fov_result_name, fov_result, [cv2.IMWRITE_JPEG_QUALITY, 100])
        self.logger.debug(f'[evaluation] end save img')

        self.img2video('encode', fov_result)

        return calculate_psnr_ssim(ground_truth, fov_result, self.use_gpu, self.psnr_flag, self.ssim_flag)

    def evaluate_misc(self):
        """Calculate remaining evaluation indicators"""
        super(Freedom1Evaluation, self).evaluate_misc()

        # The pre-downloaded portion is not included in the playable_record, and bandwidth is calculated in seconds.
        playable_frame_idxs = list(self.playable_record.keys())
        total_size = 0
        max_bandwidth = 0
        tmp_size = 0
        tmp_base_ts = self.playable_record[playable_frame_idxs[0]]['ts']
        for vam_idx in playable_frame_idxs:
            total_size += self.playable_record[vam_idx]['vam_size']
            if self.playable_record[vam_idx]['ts'] - tmp_base_ts > 1000:
                tmp_bandwidth = tmp_size * 1000 / (self.playable_record[vam_idx - 1]['ts'] - tmp_base_ts + 1000 / self.video_fps)
                if max_bandwidth < tmp_bandwidth:
                    max_bandwidth = tmp_bandwidth
                tmp_size = 0
                tmp_base_ts = self.playable_record[vam_idx]['ts']
            tmp_size += self.playable_record[vam_idx]['vam_size']

        self.write_dict['MAX bandwidth'] = f"{round(max_bandwidth / 125 / 1000, 3)}Mbps"
        self.write_dict[
            'AVG bandwidth'] = f"{round(total_size / (self.opt['video']['video_duration'] - self.pre_download_duration / 1000) / 125 / 1000, 3)}Mbps"
        self.write_dict['Total transfer size'] = f"{round(total_size / 1000 / 1000, 6)}MB"
        return [self.write_dict]
