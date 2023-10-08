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
class TranscodingEvaluation(BaseEvaluation):
    """
    Transcoding Evaluation

    Parameters
    ----------
    opt : dict
        Configurations.

    Notes
    ----------
    Almost all class public attributes are directly read or indirectly processed from the yaml configuration file.
    Their specific meanings can be found in 'docs/Config.md'.
    """

    def __init__(self, opt):
        super(TranscodingEvaluation, self).__init__(opt)

        self.data = build_data(opt)
        self.playable_record = self._decision_to_playable()
        self.video_fps = opt['video']['video_fps']
        self.base_frame_idx = int(self.pre_download_duration * self.video_fps // 1000.0)
        self.vam_size = opt['method_settings']['vam_size']
        self.crop_factor = [eval(v) for v in opt['method_settings']['crop_factor']]
        self.scale_factors = {k: eval(v) for k, v in opt['method_settings']['scale_factors'].items()}
        self.sampling_num = opt['metric']['sampling_size'][0] * opt['metric']['sampling_size'][1]
        self.range_num = opt['metric']['range_fov'][0] * opt['metric']['range_fov'][1]
        self.gc_w1 = 0.09    #gc_score weight value
        self.gc_w2 = 0.000015
        self.gc_w3 = opt['video']['video_duration'] / 3600.0    # (s)

    def _decision_to_playable(self):
        """Calculate the playable timestamp of each VAM on the client, and read the transmission amount of each chunk"""
        self.logger.info("[decision to playable] start")

        rendering_delay = self.opt['video']['rendering_delay']
        decision_location = self.opt['method_settings']['decision_location']
        assert decision_location in ['client', 'server'], "[error] Decision_location wrong. It should be set to the value in ['client', 'server']"
        rtt = self.opt['network_trace']['rtt'] * 0.5 if decision_location == 'server' else self.opt['network_trace']['rtt']
        bandwidth = self.opt['network_trace']['bandwidth']

        decision_path = osp.join(self.opt['project_path'], 'result', self.opt['test_group'], self.opt['video']['origin']['video_name'].split('.')[0],
                                 self.opt['method_name'], 'decision.json')
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

        # evaluate only once per frame.
        img_index = int((fov_ts - self.base_ts) * self.video_fps // 1000.0)
        if self.last_img_index == img_index:
            return[]
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
        coord_x, coord_y = self.projection.uv_to_coor(client_fov_uv, self.playable_record[img_index]['vam_motion'])[:2]
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
            self.logger.info(f"[evaluation] ts:{fov_ts}, frame_idx:{img_index}, out_percent:{round(self.out_percent[-1], 3)}, psnr:{round(psnr, 3)}, ssim:{round(ssim, 3)}")
        else:
            psnr, ssim = [0, 0]

        return [{'motion_timestamp': fov_ts, 'frame_idx': img_index, 'location': location, 'out_area_percent': self.out_percent[-1], 'psnr': psnr, 'ssim': ssim}]


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
        ground_truth = self._get_ground_truth_img(img_index, fov_uv)
        self.logger.debug(f'[evaluation] end get ground truth img')

        self.logger.debug(f'[evaluation] start generate client_img')

        # Get the coordinates of the viewport of different projections
        coor_x_arr, coor_y_arr = self.projection.generate_fov_coor(client_img, fov_uv, self.playable_record[img_index]['vam_motion'])

        # Generate the required fov image from the concat image
        fov_result = self.generate_fov_img(client_img, coor_x_arr, coor_y_arr)
        fov_result_name = osp.join(self.result_img_path, f"{img_index}.png")
        self.logger.debug(f'[evaluation] end generate client_img')

        self.logger.debug(f'[evaluation] start save img')
        if self.save_result_img_flag and not os.path.exists(fov_result_name):
            cv2.imwrite(fov_result_name, fov_result, [cv2.IMWRITE_JPEG_QUALITY, 100])
        self.logger.debug(f'[evaluation] end save img')

        self.img2video('encode', fov_result)

        return calculate_psnr_ssim(ground_truth, fov_result, self.use_gpu, self.psnr_flag, self.ssim_flag)


    def evaluate_misc(self):
        """
        Calculate remaining evaluation indicators, i.e., the maximum bandwidth, average bandwidth.

        Returns
        -------
        A dictionary records these indicators.
        """

        super(TranscodingEvaluation, self).evaluate_misc()
        # The pre-downloaded portion is not included in the playable_record, and bandwidth is calculated in seconds.
        playable_frame_idxs = list(self.playable_record.keys())
        total_size = 0
        max_bandwidth = 0
        tmp_size = 0
        tmp_base_ts = self.playable_record[playable_frame_idxs[0]]['ts']
        for vam_idx in playable_frame_idxs:
            total_size += self.playable_record[vam_idx]['vam_size']
            if self.playable_record[vam_idx]['ts'] - tmp_base_ts > 1000:
                tmp_bandwidth = tmp_size / ((self.playable_record[vam_idx - 1]['ts'] - tmp_base_ts + 1000 / self.video_fps) / 1000)
                if max_bandwidth < tmp_bandwidth:
                    max_bandwidth = tmp_bandwidth
                tmp_size = 0
                tmp_base_ts = self.playable_record[vam_idx]['ts']
            tmp_size += self.playable_record[vam_idx]['vam_size']

        assert self.background_flag == False
        background_size = 0
        gc_score = self.calculate_gc_score(total_size, background_size)

        self.write_dict['MAX bandwidth'] = f"{round(max_bandwidth / 125 / 1000, 3)}Mbps"
        self.write_dict['AVG bandwidth'] = f"{round(total_size / (self.opt['video']['video_duration'] - self.pre_download_duration / 1000) / 125 / 1000, 3)}Mbps"
        self.write_dict['Total transfer size'] = f"{round(total_size / 1000 / 1000, 6)}MB"
        self.write_dict['GC Score'] = f"{round(gc_score, 6)}"

        return [self.write_dict]


    def generate_fov_img(self, concat_img, coor_x_arr, coor_y_arr):
        """
        Generate FoV images that client actually viewing.

        Parameters
        ----------
        concat_img : ndarray
            An array including the concatenated high-resolution tiles and low-resolution background image
            (if there is a background stream).
        coor_x_arr:
            An array including the row coordinates of all pixel points in the FoV image.
        coor_y_arr:
            An array including the column coordinates of all pixel points in the FoV image.
        not_in_server_mask: ndarray
        The positions of the problematic pixel points.

        Returns
        -------
        numpy.ndarray
            FoV images for client viewing.
        """
        inter_mode = self.opt['metric']['inter_mode']
        if inter_mode == 'bilinear':
            inter_order = cv2.INTER_LINEAR
        elif inter_mode == 'nearest':
            inter_order = cv2.INTER_NEAREST
        elif inter_mode == 'cubic':
            inter_order = cv2.INTER_CUBIC
        elif inter_mode == 'area':
            inter_order = cv2.INTER_AREA
        elif inter_mode == 'lanczos4':
            inter_order = cv2.INTER_LANCZOS4
        else:
            raise NotImplementedError('unknown mode')

        dst_map_u, dst_map_v = cv2.convertMaps(coor_x_arr.astype(np.float32), coor_y_arr.astype(np.float32), cv2.CV_16SC2)
        fov_result = cv2.remap(concat_img, dst_map_u, dst_map_v, inter_order)

        return fov_result


    def calculate_gc_score(self, total_bandwidth, background_storage):
        """
        Calculate the final grand challenge score.

        Parameters
        ----------
        total_bandwidth
        background_storage

        Returns
        -------
        gc_score: the calculated final score
        """
        total_storage = 0
        # The storage cost of transcoding mode is temporally set as 0. To enable it, just uncomment it.
        # for chunk_idx in range(len(self.data.video_size)):
        #     chunk_data = self.data.video_size[chunk_idx]
        #     vam_storge_data = chunk_data['chunk_meta_data'][1]['vam_size_list']
        #     for qp_idx in range(len(vam_storge_data)):
        #         total_storage += vam_storge_data[qp_idx]['vam_size']

        total_bandwidth = round(total_bandwidth / 1000 / 1000 / 1000, 6)   # GB

        total_storage = round((total_storage + background_storage) / 1000 / 1000 / 1000, 6)   # GB

        total_computation = 1.204 if self.use_gpu else 0

        vpsnr = round(np.average(self.psnr), 3)

        w_1, w_2, w_3 = self.gc_w1, self.gc_w2, self.gc_w3
        gc_score = vpsnr / (w_1 * total_bandwidth + w_2 * total_storage + w_3 * total_computation)

        return gc_score