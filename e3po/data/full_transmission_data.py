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
from tqdm import tqdm
from copy import deepcopy
import json

from e3po.utils.registry import data_registry
from e3po.utils import write_json
from .base_data import BaseData


@data_registry.register()
class FullTransmissionData(BaseData):
    """
    Full transmission data.

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
        super().__init__(opt)
        self.chunk_duration = opt['method_settings']['chunk_duration']
        if self.video_duration % self.chunk_duration != 0:
            self.logger.error("[error] video_duration mod chunk_duration != 0")
            exit(0)
        self.chunk_num = int(self.video_duration / self.chunk_duration)
        json_path = osp.join(self.work_folder, 'video_size.json')
        if os.path.exists(json_path):
            with open(json_path, encoding='UTF-8') as f:
                self.video_size = json.load(f)

    def process_video(self):
        self._convert_ori_video()
        self._generate_chunk()
        self._get_chunk_size()
        self._del_intermediate_file(self.work_folder, ['converted'], ['.json'])

    def _generate_chunk(self):
        """Segment the video into chunks"""
        self.logger.info("[generating chunk] start")

        quality_bar = tqdm(self.quality_list, leave=False)
        for quality in quality_bar:
            quality_bar.set_description(f"[generating chunk] qp={quality}")

            chunk_directory = osp.join(self.work_folder, f'qp{quality}')
            os.makedirs(chunk_directory, exist_ok=True)
            input_video_path = osp.join(self.work_folder, f"converted_{quality}.mp4")

            chunk_bar = tqdm(range(self.chunk_num), leave=False)
            for chunk_index in chunk_bar:
                chunk_bar.set_description(f"[generating chunk] chunk_idx={chunk_index}")

                # Default meets condition (60 mod chunk_duration) == 0
                s_1 = str(chunk_index * self.chunk_duration % 60).zfill(2)
                m_1 = str(chunk_index * self.chunk_duration // 60).zfill(2)
                h_1 = str(chunk_index * self.chunk_duration // 3600).zfill(2)
                s_2 = str(((chunk_index + 1) * self.chunk_duration) % 60).zfill(2)
                m_2 = str(((chunk_index + 1) * self.chunk_duration) // 60).zfill(2)
                h_2 = str(((chunk_index + 1) * self.chunk_duration) // 3600).zfill(2)
                cmd = f"{self.ffmpeg} " \
                      f"-i {input_video_path} " \
                      f"-threads {self.ffmpeg_thread} " \
                      f"-preset faster " \
                      f"-c:v libx264 " \
                      f"-bf 0 " \
                      f"-ss {h_1}:{m_1}:{s_1} " \
                      f"-to {h_2}:{m_2}:{s_2} " \
                      f"-y {osp.join(chunk_directory, f'chunk_{str(chunk_index).zfill(5)}.mp4')} " \
                      f"-loglevel {self.ffmpeg_loglevel}"
                self.logger.debug(cmd)
                os.system(cmd)
            chunk_bar.close()
        quality_bar.close()
        self.logger.info("[generating chunk] end")

    def _get_chunk_size(self):
        """Read the processed video file size and write it to video_size.json"""
        json_path = osp.join(self.work_folder, 'video_size.json')
        self.logger.info(f'[get chunk size] path:{json_path}')
        video_size = []

        for chunk_index in range(self.chunk_num):
            tmp_result = {}
            tmp_result['chunk_idx'] = chunk_index
            tmp_result['chunk_meta_data'] = []

            for quality in self.quality_list:
                file_path = osp.join(self.work_folder, f"qp{quality}", f"chunk_{str(chunk_index).zfill(5)}.mp4")
                chunk_size = os.path.getsize(file_path)
                tmp_result['chunk_meta_data'].append({"qp": quality, "chunk_size": chunk_size})

            video_size.append(deepcopy(tmp_result))

        write_json(video_size, json_path)
        self.logger.info(f'[write json] path: {json_path}')

    def get_size(self, *args):
        """Read the corresponding file size from video_size.json based on the parameter list"""
        assert self.video_size is not None, f"[get size error] {osp.join(self.work_folder, 'video_size.json')} doesn\'t exist."
        chunk_idx, qp_level = args
        assert 0 <= chunk_idx < len(self.video_size), f"[get size error] chunk_idx={chunk_idx} not found!"
        chunks = self.video_size[chunk_idx]['chunk_meta_data']
        for chunk in chunks:
            if int(chunk['qp']) == qp_level:
                return chunk['chunk_size']
            self.logger.error(f"[get size error] chunk_idx={chunk_idx}, qp_level={qp_level} not found!")
            exit(0)
        self.logger.error(f"[get size error] chunk_idx={chunk_idx}, qp_level={qp_level} not found!")
        exit(0)
