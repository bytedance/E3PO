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
import shutil
import os
import numpy as np
import cv2

from e3po.utils import calculate_psnr_ssim
from e3po.utils.registry import evaluation_registry
from .base_eval import BaseEvaluation
from e3po.data import build_data


@evaluation_registry.register()
class TileBasedEvaluation(BaseEvaluation):
    """
    Tile based Evaluation.

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
        super(TileBasedEvaluation, self).__init__(opt)

        self.video_fps = opt['video']['video_fps']
        self.chunk_duration = opt['method_settings']['chunk_duration']
        self.base_frame_idx = int(self.pre_download_duration * self.video_fps // 1000.0)
        self.data = build_data(opt)
        self.playable_record = self._decision_to_playable()

    def _decision_to_playable(self):
        """Calculate the playable timestamp of each chunk on the client, and read the transmission amount of each chunk"""
        self.logger.info("[decision to playable] start")

        rendering_delay = self.opt['video']['rendering_delay']
        decision_location = self.opt['method_settings']['decision_location']
        assert decision_location in ['client', 'server'], "[error] decision_location wrong. It should be set to the value in ['client', 'server']"
        rtt = self.opt['network_trace']['rtt'] * 0.5 if decision_location == 'server' else self.opt['network_trace']['rtt']
        bandwidth = self.opt['network_trace']['bandwidth']

        decision_path = osp.join(self.opt['project_path'], 'result', self.opt['test_group'], self.opt['method_name'], 'decision.json')
        with open(decision_path, encoding="utf-8") as f:
            decision_record = json.load(f)

        playable_record = {}
        for row in decision_record:
            chunk_size = 0
            for tile in row['decision_data'][1:]:
                chunk_size += self.data.get_size(row['chunk_idx'], int(tile['tile_idx']), tile['tile_bitrate'])
            download_delay = chunk_size / bandwidth / 1000
            tmp_ts = row['decision_data'][0]['pw_ts'] + download_delay + rtt + rendering_delay
            playable_record[row['chunk_idx']] = {'ts': tmp_ts, 'chunk_size': chunk_size, 'tile_list': list(row['decision_data'][1:])}

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

        chunk_idx = (fov_ts - self.base_ts) // (self.chunk_duration * 1000)
        tmp_psnr_ssim_flag = (self.psnr_flag or self.ssim_flag) and (img_index - self.base_frame_idx) % self.psnr_ssim_frequency == 0
        if self.playable_record[chunk_idx]['ts'] > fov_ts:
            self.logger.info(f"[evaluation] no content to play at {fov_ts}. chunk_idx: {chunk_idx}, playable_record_ts: {self.playable_record[chunk_idx]['ts']}")
            if self.save_result_img_flag and os.path.exists(osp.join(self.result_img_path, f"{img_index - 1}.png")):
                shutil.copyfile(osp.join(self.result_img_path, f"{img_index - 1}.png"), osp.join(self.result_img_path, f"{img_index}.png"))
            if tmp_psnr_ssim_flag:
                self.psnr.append(0)
                self.ssim.append(0)
            self.out_percent.append(1)
            return [{'motion_timestamp': fov_ts, 'location': 'no_content', 'out_area_percent': 1, 'psnr': 0, 'ssim': 0}]

        fov_tile_list, fov_pixel_tile_list = self.projection.sphere_to_tile(fov_direction)

        server_tile_list = []
        for item in self.playable_record[chunk_idx]['tile_list']:
            server_tile_list.append(item['tile_idx'])

        if len(np.setdiff1d(fov_tile_list, server_tile_list)) == 0:
            location = 'in'
            self.out_percent.append(0)
        else:
            fov_diff_tile = np.setdiff1d(fov_tile_list, server_tile_list)
            location = 'out'
            out_pixel_num = 0
            fov_pixel_tile_list = np.array(fov_pixel_tile_list.reshape(1, -1)[0])
            fov_pixel_tile_list = np.sort(fov_pixel_tile_list)
            for j in fov_diff_tile:
                out_pixel_num += len(np.where(fov_pixel_tile_list == j)[0])
            self.out_percent.append(out_pixel_num / (self.opt['metric']['sampling_size'][0] * self.opt['metric']['sampling_size'][1]))

        if tmp_psnr_ssim_flag:
            psnr, ssim = self._calculate_psnr_ssim(fov_direction, server_tile_list, img_index)
            self.psnr.append(psnr)
            self.ssim.append(ssim)
            self.logger.info(f"[evaluation] ts:{fov_ts}, frame_idx:{img_index}, out_percent:{round(self.out_percent[-1], 3)}, psnr:{round(psnr, 3)}, ssim:{round(ssim, 3)}")
        else:
            psnr, ssim = [0, 0]
        
        return [{'motion_timestamp': fov_ts, 'frame_idx': img_index, 'yaw': fov_direction['yaw'], 'pitch': fov_direction['pitch'], 'location': location, 'out_area_percent': self.out_percent[-1], 'psnr': psnr, 'ssim': ssim}]

    def _calculate_psnr_ssim(self, fov_direction, server_tile_list, img_index):
        """
        Calculate PSNR and SSIM.

        Parameters
        ----------
        fov_direction : dict
            Motion description information:
                {'yaw': yaw, 'pitch': pitch, 'scale': scale}
        server_tile_list : list
            List of tile sequence numbers for transmission of server decision.
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
        # Assuming that the quality of tiles is the same
        client_img = self.extract_frame(self.projection_mode, min(self.quality_list), img_index)
        self.logger.debug(f'[evaluation] end read client img')

        self.logger.debug(f'[evaluation] start concat img')
        if self.background_flag:
            background_width = self.opt['method_settings']['background']['width']
            background_height = self.opt['method_settings']['background']['height']
            background_img = self.extract_frame('background', '', img_index)
            concat_img = np.zeros((max(converted_height, background_height), converted_width + background_width, 3), np.uint8)
            concat_img[:converted_height, :converted_width, :] = client_img
            concat_img[:background_height, converted_width: converted_width + background_width, :] = background_img
        else:
            concat_img = client_img
        concat_img[0][0] = [128, 128, 128]
        self.logger.debug(f'[evaluation] end concat img')

        self.logger.debug(f'[evaluation] start cal fov_uv')
        fov_ypr = [float(fov_direction['yaw']), float(fov_direction['pitch']), 0]
        fov_uv = self.projection.sphere_to_uv(fov_ypr, self.fov_resolution)
        self.logger.debug(f'[evaluation] end cal fov_uv')

        self.logger.debug(f'[evaluation] start get ground truth img')
        ground_truth = self._get_ground_truth_img(img_index, fov_uv, fov_direction)
        self.logger.debug(f'[evaluation] end get ground truth img')

        self.logger.debug(f'[evaluation] start generate client_img')
        fov_result = self.projection.get_fov(concat_img, converted_width, converted_height, fov_uv, server_tile_list)
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
        super(TileBasedEvaluation, self).evaluate_misc()

        total_size = 0
        max_bandwidth = 0
        # The pre-downloaded portion is not included in the playable_record
        for chunk_idx in self.playable_record.keys():
            chunk_size = self.playable_record[chunk_idx]['chunk_size']
            if self.background_flag:
                chunk_size += self.data.get_background_size(chunk_idx)
            if max_bandwidth < chunk_size / self.chunk_duration:
                max_bandwidth = chunk_size / self.chunk_duration
            total_size += chunk_size

        self.write_dict['MAX bandwidth'] = f"{round(max_bandwidth / 125 / 1000, 3)}Mbps"
        self.write_dict['AVG bandwidth'] = f"{round(total_size / (self.opt['video']['video_duration'] - self.pre_download_duration / 1000) / 125 / 1000, 3)}Mbps"
        self.write_dict['Total transfer size'] = f"{round(total_size / 1000 / 1000, 6)}MB"
        return [self.write_dict]
