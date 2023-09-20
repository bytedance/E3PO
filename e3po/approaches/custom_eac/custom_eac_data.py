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
import cv2

from e3po.utils.registry import data_registry
from e3po.utils import write_json
from e3po.data.on_demand_data import OnDemandData
from e3po.projection import build_projection


@data_registry.register()
class CustomEacData(OnDemandData):
    """
    Custom EAC data.

    Parameters
    ----------
    opt : dict
        Configurations.

    Notes
    -----
    Almost all class public attributes are directly read or indirectly processed from the yaml configuration file.
    Their specific meanings can be found in 'docs/Config.md'.
    """
    def _convert_ori_video(self):
        """Convert original video's projection format and qp value."""
        os.makedirs(self.work_folder, exist_ok=True)
        os.chdir(self.work_folder)

        self.logger.info(f'[converting origin video] start; {self.ori_projection_mode} to {self.projection_mode}')

        self.logger.info(f"[converting origin video] {self.ori_projection_mode} to erp")
        origin = self.opt['video']['origin']
        cmd = f"{self.ffmpeg} " \
              f"-i {self.ori_video_path} " \
              f"-threads {self.ffmpeg_thread} " \
              f"-c:v libx264 " \
              f"-ss 0:0:0 " \
              f"-to {self.video_duration_str} " \
              f"-preset faster " \
              f"-vf v360={self.ori_ffmpeg_vf_option}:e" \
              f",scale={origin['width']}x{origin['height']} " \
              f"-y erp.mp4 " \
              f"-loglevel {self.ffmpeg_loglevel}"
        self.logger.debug(cmd)
        os.system(cmd)

        self.logger.info(f"[converting origin video] erp to {self.projection_mode}")
        tmp_projection = build_projection(self.opt)
        frame_path = osp.join(self.work_folder, 'frames')
        os.makedirs(frame_path, exist_ok=True)
        background_frame_path = osp.join(self.work_folder, 'background_frames')
        os.makedirs(background_frame_path, exist_ok=True)
        video = cv2.VideoCapture()
        assert video.open("erp.mp4"), "can't read video[erp.mp4]"
        frame_num = int(video.get(cv2.CAP_PROP_FRAME_COUNT))

        frame_bar = tqdm(range(frame_num), leave=False)
        for frame_idx in frame_bar:
            frame_bar.set_description(f"[erp to eac] frame_idx={frame_idx}")
            ret, frame = video.read()
            if not ret:
                break
            frame = tmp_projection.erp_to_eac(frame, self.opt['metric']['inter_mode'])

            cv2.imwrite(osp.join(frame_path, f"{frame_idx}.png"), frame, [cv2.IMWRITE_JPEG_QUALITY, 100])

            if self.opt['method_settings']['background']['background_flag']:
                frame = cv2.resize(frame, (self.background_width, self.background_height))
                cv2.imwrite(osp.join(background_frame_path, f"{frame_idx}.png"), frame, [cv2.IMWRITE_JPEG_QUALITY, 100])
        frame_bar.close()

        quality_bar = tqdm(self.quality_list, leave=False)
        for quality in quality_bar:
            quality_bar.set_description(f"[converting origin video] qp={quality}")

            cmd = f"{self.ffmpeg} " \
                  f"-r {self.video_fps} " \
                  f"-start_number 0 " \
                  f"-i {osp.join('.', 'frames', '%d.png')} " \
                  f"-threads {self.ffmpeg_thread} " \
                  f"-preset faster " \
                  f"-c:v libx264 " \
                  f"-qp {quality} " \
                  f"-y {osp.join('.', f'converted_{quality}.mp4')} " \
                  f"-loglevel {self.ffmpeg_loglevel}"
            self.logger.debug(cmd)
            os.system(cmd)
        quality_bar.close()

        if self.opt['method_settings']['background']['background_flag']:
            self.logger.info('[generating background video] start')
            cmd = f"{self.ffmpeg} " \
                  f"-r {self.video_fps} " \
                  f"-start_number 0 " \
                  f"-i {osp.join('.', 'background_frames', '%d.png')} " \
                  f"-threads {self.ffmpeg_thread} " \
                  f"-preset faster " \
                  f"-c:v libx264 " \
                  f"-qp {quality} " \
                  f"-y {osp.join('.', f'background.mp4')} " \
                  f"-loglevel {self.ffmpeg_loglevel}"
            self.logger.debug(cmd)
            os.system(cmd)
            self.logger.info('[generating background video] end')

        self.logger.info('[converting origin video] end')

    def _generate_tile(self):
        """Segment the video chunks into tiles."""
        self.logger.info("[generating tile] start")

        quality_bar = tqdm(self.quality_list, leave=False)
        for quality in quality_bar:
            quality_bar.set_description(f"[generating tile] qp={quality}")

            chunk_bar = tqdm(range(0, self.chunk_num), leave=False)
            for chunk_index in chunk_bar:
                chunk_bar.set_description(f"[generating tile] chunk_idx={chunk_index}")

                chunk_path = osp.join(self.work_folder, f'qp{quality}', f'chunk_{str(chunk_index).zfill(5)}.mp4')
                output_dir_path = osp.join(self.work_folder, f"qp{quality}", f"chunk_{str(chunk_index).zfill(5)}")
                os.makedirs(output_dir_path, exist_ok=True)
                os.chdir(output_dir_path)

                small_tile_width = self.video_width / self.tile_width_num
                small_tile_height = self.video_height / self.tile_height_num
                big_tile_width = self.video_width / 3
                big_tile_height = self.video_height / 2

                tile_index_bar = tqdm(total=int(self.tile_width_num * self.tile_height_num * 2 / 3 + 2), leave=False)
                for i in range(self.tile_width_num):
                    for j in range(self.tile_height_num):
                        if j >= self.tile_height_num / 2 and (i < self.tile_width_num / 3 or i >= self.tile_width_num / 3 * 2):
                            if j == self.tile_height_num / 2 and (i == 0 or i == self.tile_width_num / 3 * 2):
                                tile_width = big_tile_width
                                tile_height = big_tile_height
                            else:
                                continue
                        else:
                            tile_width = small_tile_width
                            tile_height = small_tile_height
                        x = small_tile_width * i
                        y = small_tile_height * j
                        tile_idx = i + j * self.tile_width_num
                        tile_index_bar.set_description(f"[generating tile] tile_idx={tile_idx}")
                        cmd = f"{self.ffmpeg} " \
                              f"-i {chunk_path} " \
                              f"-threads {self.ffmpeg_thread} " \
                              f"-vf \"crop={tile_width}:{tile_height}:{x}:{y}\" " \
                              f"-y tile_{str(tile_idx).zfill(3)}.mp4 " \
                              f"-loglevel {self.ffmpeg_loglevel}"
                        self.logger.debug(cmd)
                        os.system(cmd)
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

            for i in range(self.tile_width_num):
                for j in range(self.tile_height_num):
                    if j >= self.tile_height_num / 2 and (i < self.tile_width_num / 3 or i >= self.tile_width_num / 3 * 2):
                        if j == self.tile_height_num / 2 and (i == 0 or i == self.tile_width_num / 3 * 2):
                            pass
                        else:
                            continue
                    else:
                        pass
                    tile_index = i + j * self.tile_width_num
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
