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
from tqdm import tqdm

from e3po.utils import calculate_psnr_ssim
from e3po.utils.registry import evaluation_registry
from .base_eval import BaseEvaluation
from e3po.data import build_data

@evaluation_registry.register()
class OnDemandEvaluation(BaseEvaluation):
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
        super(OnDemandEvaluation, self).__init__(opt)

        self.video_fps = opt['video']['video_fps']
        self.chunk_duration = opt['method_settings']['chunk_duration']
        self.base_frame_idx = int(self.pre_download_duration * self.video_fps // 1000.0)
        self.data = build_data(opt)
        self.playable_record = self._decision_to_playable()         # Transform the decision.json file into playable_record
        self.gc_w1 = 0.09                                           # gc_score weight value
        self.gc_w2 = 0.000015
        self.gc_w3 = opt['video']['video_duration'] / 3600.0        # (s)

    def _decision_to_playable(self):
        """Calculate the playable timestamp of each chunk on the client, and read the transmission amount of each chunk"""
        self.logger.info("[decision to playable] start")

        rendering_delay = self.opt['video']['rendering_delay']
        decision_location = self.opt['method_settings']['decision_location']
        assert decision_location in ['client', 'server'], "[error] decision_location wrong. It should be set to the value in ['client', 'server']"
        rtt = self.opt['network_trace']['rtt'] * 0.5 if decision_location == 'server' else self.opt['network_trace']['rtt']
        bandwidth = self.opt['network_trace']['bandwidth']

        decision_path = osp.join(self.opt['project_path'], 'result', self.opt['test_group'], self.opt['video']['origin']['video_name'].split('.')[0],
                                 self.opt['method_name'], 'decision.json')
        with open(decision_path, encoding="utf-8") as f:
            decision_record = json.load(f)

        playable_record = {}
        last_chunk_idx = -1
        last_chunk_size = -1
        for row in decision_record:
            chunk_idx = row['chunk_idx']
            chunk_size = 0
            for tile in row['decision_data'][1:]:
                chunk_size += self.data.get_size(row['chunk_idx'], int(tile['tile_idx']), tile['tile_bitrate'])
            download_delay = chunk_size / bandwidth / 1000
            playable_ts = row['decision_data'][0]['pw_ts'] + download_delay + rtt + rendering_delay
            if chunk_idx != last_chunk_idx:     # new chunk
                tmp_playable_record = []
                for tile in row['decision_data'][1:]:
                    tmp_playable_record.append({'playable_ts': playable_ts, 'tile_idx': int(tile['tile_idx']),
                                                'tile_bitrate': tile['tile_bitrate']})
                playable_record[row['chunk_idx']] = {'chunk_size': chunk_size, 'tile_list': tmp_playable_record}
                last_chunk_idx = chunk_idx
                last_chunk_size = chunk_size
            else:                               # same chunk
                chunk_size += last_chunk_size
                last_chunk_size = chunk_size
                for tile in row['decision_data'][1:]:
                    playable_record[chunk_idx]['tile_list'].append({'playable_ts': playable_ts, 'tile_idx': int(tile['tile_idx']),
                                                                    'tile_bitrate': tile['tile_bitrate']})
                playable_record[chunk_idx]['chunk_size'] = chunk_size

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
        tmp_psnr_ssim_flag = (self.psnr_flag or self.ssim_flag) and \
                             (img_index - self.base_frame_idx) % self.psnr_ssim_frequency == 0

        if self.playable_record[chunk_idx]['tile_list'][0]['playable_ts'] > fov_ts:        # there should be content for current frame
            self.logger.info(
                f"[evaluation] no content to play at {fov_ts}. chunk_idx: {chunk_idx}, playable_record_ts: {self.playable_record[chunk_idx]['ts']}")
            if self.save_result_img_flag and os.path.exists(osp.join(self.result_img_path, f"{img_index - 1}.png")):
                shutil.copyfile(osp.join(self.result_img_path, f"{img_index - 1}.png"),
                                osp.join(self.result_img_path, f"{img_index}.png"))
            if tmp_psnr_ssim_flag:
                self.psnr.append(0)
                self.ssim.append(0)
            self.out_percent.append(1)
            return [{'motion_timestamp': fov_ts, 'location': 'no_content', 'out_area_percent': 1, 'psnr': 0, 'ssim': 0}]

        fov_tile_list, fov_pixel_tile_list = self.projection.sphere_to_tile(fov_direction)

        server_tile_list, server_qp_list = self._get_server_data(fov_ts)

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
            self.out_percent.append(
                out_pixel_num / (self.opt['metric']['sampling_size'][0] * self.opt['metric']['sampling_size'][1]))

        if tmp_psnr_ssim_flag:
            psnr, ssim = self._calculate_psnr_ssim(fov_direction, server_tile_list, img_index, server_qp_list)
            self.psnr.append(psnr)
            self.ssim.append(ssim)
            self.logger.info(
                f"[evaluation] ts:{fov_ts}, frame_idx:{img_index}, out_percent:{round(self.out_percent[-1], 3)}, "
                f"psnr:{round(psnr, 3)}, ssim:{round(ssim, 3)}")
        else:
            psnr, ssim = [0, 0]

        return [{'motion_timestamp': fov_ts, 'frame_idx': img_index, 'yaw': fov_direction['yaw'],
                 'pitch': fov_direction['pitch'], 'location': location, 'out_area_percent': self.out_percent[-1],
                 'psnr': psnr, 'ssim': ssim}]

    def _calculate_psnr_ssim(self, fov_direction, server_tile_list, img_index, server_qp_list):
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
        server_qp_list: list
            List of the qp values of different tiles, which are determined at the server.

        Returns
        -------
        list
            [psnr, ssim].
        """
        converted_width = self.opt['video']['converted']['width']
        converted_height = self.opt['video']['converted']['height']

        self.logger.debug(f'[evaluation] start read client img')
        # Assuming that the quality of tiles is the same
        quality_num = len(self.quality_list)
        client_img = np.zeros((converted_height, converted_width * quality_num, 3), np.uint8)             # images with different quality
        for quality_idx in range(0, quality_num):
            quality = self.quality_list[quality_idx]
            quality_img = self.extract_frame(self.projection_mode, quality, img_index)
            client_img[:converted_height, converted_width*quality_idx:converted_width*(quality_idx + 1), :] = quality_img
        self.logger.debug(f'[evaluation] end read client img')

        self.logger.debug(f'[evaluation] start concat img')
        if self.background_flag:
            background_width = self.opt['method_settings']['background']['width']
            background_height = self.opt['method_settings']['background']['height']
            background_img = self.extract_frame('background', '', img_index)
            concat_img = np.zeros((max(converted_height, background_height), converted_width * quality_num + background_width, 3), np.uint8)
            concat_img[:converted_height, :converted_width*quality_num, :] = client_img
            concat_img[:background_height, converted_width*quality_num:converted_width*quality_num+background_width, :] = background_img
        else:
            concat_img = client_img
        concat_img[0][0] = [128, 128, 128]
        self.logger.debug(f'[evaluation] end concat img')

        self.logger.debug(f'[evaluation] start cal fov_uv')
        fov_ypr = [float(fov_direction['yaw']), float(fov_direction['pitch']), 0]
        fov_uv = self.projection.sphere_to_uv(fov_ypr, self.fov_resolution)
        self.logger.debug(f'[evaluation] end cal fov_uv')

        self.logger.debug(f'[evaluation] start get ground truth img')
        ground_truth = self._get_ground_truth_img(img_index, fov_uv)
        self.logger.debug(f'[evaluation] end get ground truth img')

        self.logger.debug(f'[evaluation] start generate client_img')
        # Get the coordinates of the viewport of different projections
        coor_x_arr, coor_y_arr = self.projection.generate_fov_coor(concat_img, converted_width, converted_height, fov_uv, server_tile_list, server_qp_list)

        # Verify the correction of returned coordinates
        checkout_result = self.checkout_tile_list(converted_width, converted_height, coor_x_arr, coor_y_arr, server_tile_list, server_qp_list)

        # Generate the required fov image from the concat image
        fov_result = self.generate_fov_img(concat_img, coor_x_arr, coor_y_arr, checkout_result)

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
        super(OnDemandEvaluation, self).evaluate_misc()

        total_size = 0
        max_bandwidth = 0
        background_size = 0
        # The pre-downloaded portion is not included in the playable_record
        for chunk_idx in self.playable_record.keys():
            chunk_size = self.playable_record[chunk_idx]['chunk_size']
            if self.background_flag:
                temp_background_size = self.data.get_background_size(chunk_idx)
                background_size += temp_background_size
                chunk_size += temp_background_size
            if max_bandwidth < chunk_size / self.chunk_duration:
                max_bandwidth = chunk_size / self.chunk_duration
            total_size += chunk_size

        gc_score = self.calculate_gc_score(total_size, background_size)

        self.write_dict['MAX bandwidth'] = f"{round(max_bandwidth / 125 / 1000, 3)}Mbps"   # transform bytes to bits
        self.write_dict[
            'AVG bandwidth'] = f"{round(total_size / (self.opt['video']['video_duration'] - self.pre_download_duration / 1000) / 125 / 1000, 3)}Mbps"
        self.write_dict['Total transfer size'] = f"{round(total_size / 1000 / 1000, 6)}MB"
        self.write_dict['GC Score'] = f"{round(gc_score, 6)}"

        return [self.write_dict]

    def checkout_tile_list(self, src_width, src_height, coor_x_arr, coor_y_arr, server_tile_list, server_qp_list):
        """
        Generate FoV images that client actually viewing.

        Parameters
        ----------
        src_width: int
            The width of original full frame.
        src_height: int
            The height of original full frame.
        coor_x_arr:
            An array including the row coordinates of all pixel points in the FoV image.
        coor_y_arr:
            An array including the column coordinates of all pixel points in the FoV image.
        server_tile_list:
            After decision, selected tiles at the server.

        Returns
        -------
        not_in_server_mask: ndarray
            The positions of the problematic pixel points.
        """
        tile_list, client_tile_list = self.projection._coord_to_tile([coor_x_arr % src_width, coor_y_arr], src_width, src_height)

        set_server_qp_list = set(server_qp_list)
        server_mask = np.zeros((coor_x_arr.shape[:2]), np.uint8)
        for qp_value in set_server_qp_list:
            qp_idx = self.quality_list.index(qp_value)
            server_qp_mask = np.isin(server_qp_list, qp_value)
            server_tile_list_qp = np.array(server_tile_list)[server_qp_mask]
            temp_mask1 = np.where(qp_idx * src_width <= coor_x_arr, 1, -1) + np.where(coor_x_arr < (qp_idx + 1) * src_width, 0, -1)
            temp_mask2 = np.where(temp_mask1 == 1, 1, -1)
            temp_mask3 = np.where(np.isin(client_tile_list, server_tile_list_qp) == True, 1, 0)
            temp_server_mask = temp_mask2 + temp_mask3
            server_mask[temp_server_mask == 1] = 1

        not_in_server_mask = (server_mask == 1)
        return not_in_server_mask


    def generate_fov_img(self, concat_img, coor_x_arr, coor_y_arr, not_in_server_mask):
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

        coor_x_arr[not_in_server_mask], coor_y_arr[not_in_server_mask] = 0, 0

        # generate fov image with the given concat_img
        dst_map_u, dst_map_v = cv2.convertMaps(coor_x_arr.astype(np.float32), coor_y_arr.astype(np.float32), cv2.CV_16SC2)
        fov_result = cv2.remap(concat_img, dst_map_u, dst_map_v, inter_order)

        return fov_result

    def _get_server_data(self, fov_ts):
        """
        Parameters
        ----------
        fov_ts: the timestamp of current fov frame

        Returns
        -------
        server_tile_list_: the available tiles at current timestamp
        server_qp_list_: the corresponding qp of available tiles

        """
        server_tile_list_ = []
        server_qp_list_ = []
        chunk_idx = (fov_ts - self.base_ts) // (self.chunk_duration * 1000)
        tile_list = self.playable_record[chunk_idx]['tile_list']
        for tile in tile_list:
            if tile['playable_ts'] < fov_ts:
                server_tile_list_.append(tile['tile_idx'])
                server_qp_list_.append(tile['tile_bitrate'])

        return np.array(server_tile_list_), np.array(server_qp_list_)

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
        for chunk_idx in range(len(self.data.video_size)):
            chunk_data = self.data.video_size[chunk_idx]
            for tile_idx in range(len(chunk_data['chunk_meta_data'])):
                tile_data = chunk_data['chunk_meta_data'][tile_idx]
                for qp_idx in range(len(tile_data['tile_size_list'])):
                    total_storage += tile_data['tile_size_list'][qp_idx]['tile_size']

        total_bandwidth = round(total_bandwidth / 1000 / 1000 / 1000, 6)   # GB

        total_storage = round((total_storage + background_storage) / 1000 / 1000 / 1000, 6)   # GB

        total_computation = 1.204 if self.use_gpu else 0

        vpsnr = round(np.average(self.psnr), 3)

        w_1, w_2, w_3 = self.gc_w1, self.gc_w2, self.gc_w3
        gc_score = vpsnr / (w_1 * total_bandwidth + w_2 * total_storage + w_3 * total_computation)

        return gc_score


