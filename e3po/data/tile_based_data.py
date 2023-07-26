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
from tqdm import tqdm
from copy import deepcopy

from e3po.utils.registry import data_registry
from e3po.utils import write_json
from .base_data import BaseData


@data_registry.register()
class TileBasedData(BaseData):
    """
    Tile based data.

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
        super(TileBasedData, self).__init__(opt)
        tile = opt['method_settings']
        self.chunk_duration = tile['chunk_duration']
        assert self.video_duration % self.chunk_duration == 0, "[error] video_duration mod chunk_duration != 0"
        self.chunk_num = int(self.video_duration / self.chunk_duration)
        self.tile_width_num = tile['tile_width_num']
        self.tile_height_num = tile['tile_height_num']

        self.video_size = None
        json_path = osp.join(self.work_folder, 'video_size.json')
        if os.path.exists(json_path):
            with open(json_path, encoding='UTF-8') as f:
                self.video_size = json.load(f)

        self.background_size = None
        json_path = osp.join(self.work_folder, 'background_size.json')
        if os.path.exists(json_path):
            with open(json_path, encoding='UTF-8') as f:
                self.background_size = json.load(f)

    def process_video(self):
        self._convert_ori_video()
        self._generate_chunk()
        self._generate_tile()
        self._get_tile_size()
        self._del_intermediate_file(self.work_folder, ['converted', 'background.mp4'], ['.json'])

    def _generate_chunk(self):
        """Segment the video into chunks"""
        self.logger.info("[generating chunk] start")

        background_directory = osp.join(self.work_folder, 'background_chunks')
        os.makedirs(background_directory, exist_ok=True)
        background_video_path = osp.join(self.work_folder, 'background.mp4')

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

                if self.opt['method_settings']['background']['background_flag']:
                    video_path = osp.join(background_directory, f"background_{str(chunk_index).zfill(5)}.mp4")
                    if not os.path.exists(video_path):
                        cmd = f"{self.ffmpeg} " \
                              f"-i {background_video_path} " \
                              f"-threads {self.ffmpeg_thread} " \
                              f"-preset faster " \
                              f"-c:v libx264 " \
                              f"-bf 0 " \
                              f"-ss {h_1}:{m_1}:{s_1} " \
                              f"-to {h_2}:{m_2}:{s_2} " \
                              f"-y {video_path} " \
                              f"-loglevel {self.ffmpeg_loglevel}"
                        self.logger.debug(cmd)
                        os.system(cmd)
            chunk_bar.close()
        quality_bar.close()
        self.logger.info("[generating chunk] end")

    def _generate_tile(self):
        """Split the video chunks into tiles."""
        self.logger.info("[generating tile] start")

        quality_bar = tqdm(self.quality_list, leave=False)
        for quality in quality_bar:
            quality_bar.set_description(f"[generating tile] qp={quality}")

            chunk_bar = tqdm(range(0, self.chunk_num), leave=False)
            for chunk_index in chunk_bar:
                chunk_bar.set_description(f"[generating tile] chunk_idx={chunk_index}")

                chunk_path = osp.join(self.work_folder, f"qp{quality}", f"chunk_{str(chunk_index).zfill(5)}.mp4")
                output_dir_path = osp.join(self.work_folder, f"qp{quality}", f"chunk_{str(chunk_index).zfill(5)}")
                os.makedirs(output_dir_path, exist_ok=True)
                os.chdir(output_dir_path)

                tile_width = self.video_width / self.tile_width_num
                tile_height = self.video_height / self.tile_height_num
                tile_index = 0
                tile_index_bar = tqdm(total=self.tile_width_num*self.tile_height_num, leave=False)
                for index_height in range(self.tile_height_num - 1, -1, -1):
                    for index_width in range(self.tile_width_num):
                        tile_index_bar.set_description(f"[generating tile] tile_idx={tile_index}")

                        cmd = f"{self.ffmpeg} " \
                              f"-i {chunk_path} " \
                              f"-threads {self.ffmpeg_thread} " \
                              f"-vf \"crop={tile_width}:{tile_height}:{index_width * tile_width}:{index_height * tile_height}\" " \
                              f"-y tile_{str(tile_index).zfill(3)}.mp4 " \
                              f"-loglevel {self.ffmpeg_loglevel}"
                        self.logger.debug(cmd)
                        os.system(cmd)
                        tile_index += 1
                        tile_index_bar.update(1)
                tile_index_bar.close()
            chunk_bar.close()
        quality_bar.close()

        self.logger.info("[generating tile] end")

    def _get_tile_size(self):
        """Read the processed video file size and write it to video_size.json"""
        self.logger.info('[get tile size]')
        video_size = []
        background_size = []

        for chunk_index in range(self.chunk_num):
            tmp_result = {'chunk_idx': chunk_index, 'chunk_meta_data': []}

            for tile_index in range(self.tile_width_num*self.tile_height_num):
                tile_data = []

                for quality in self.quality_list:
                    file_path = osp.join(self.work_folder, f"qp{quality}", f"chunk_{str(chunk_index).zfill(5)}", f"tile_{str(tile_index).zfill(3)}.mp4")
                    tile_size = os.path.getsize(file_path)
                    tile_data.append({"qp": quality, "tile_size": tile_size})

                tmp_result['chunk_meta_data'].append({'tile_idx': tile_index, "tile_size_list": tile_data})
            video_size.append(deepcopy(tmp_result))

            if self.opt['method_settings']['background']['background_flag']:
                background_path = osp.join(self.work_folder, 'background_chunks', f"background_{str(chunk_index).zfill(5)}.mp4")
                background_chunk_size = os.path.getsize(background_path)
                background_size.append({'chunk_idx': chunk_index, 'chunk_meta_data': [{'chunk_size': background_chunk_size}]})

        json_path = osp.join(self.work_folder, 'video_size.json')
        write_json(video_size, json_path)
        self.logger.info(f'[write json] path: {json_path}')

        if self.opt['method_settings']['background']['background_flag']:
            json_path = osp.join(self.work_folder, 'background_size.json')
            write_json(background_size, json_path)
            self.logger.info(f'[write json] path: {json_path}')

    def get_size(self, *args):
        """Read the corresponding file size from video_size.json based on the parameter list"""
        assert self.video_size is not None, f"[get size error] {osp.join(self.work_folder, 'video_size.json')} doesn\'t exist."
        chunk_idx, tile_idx, qp_level = args
        assert 0 <= chunk_idx < len(self.video_size), f"[get size error] chunk_idx={chunk_idx} not found!"
        tiles = self.video_size[chunk_idx]['chunk_meta_data']
        for tile in tiles:
            if int(tile['tile_idx']) == tile_idx:
                qualities = tile['tile_size_list']
                for quality in qualities:
                    if quality['qp'] == qp_level:
                        return quality['tile_size']
                self.logger.error(f"[get size error] tile_idx={tile_idx}, qp_level={qp_level} not found!")
                exit(0)
        self.logger.error(f"[get size error] tile_idx={tile_idx}, qp_level={qp_level} not found!")
        exit(0)

    def get_background_size(self, *args):
        """Read the corresponding background file size from background_size.json based on the parameter list"""
        assert self.background_size is not None, f"[get background size error] {osp.join(self.work_folder, 'background_size.json')} doesn\'t exist."
        chunk_idx = args[0]
        assert 0 <= chunk_idx < len(self.background_size), f"[get background size error] chunk_idx={chunk_idx} not found!"
        return self.background_size[chunk_idx]['chunk_meta_data'][0]['chunk_size']
