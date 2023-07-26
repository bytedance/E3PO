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
import shutil

from e3po.utils import get_logger


class BaseData:
    """
    Base data.

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
        self.opt = opt
        self.test_group = opt['test_group']
        self.method_name = opt['method_name']
        self.logger = get_logger()
        self.ffmpeg_loglevel = self.opt['ffmpeg']['loglevel']
        self.ffmpeg_thread = self.opt['ffmpeg']['thread']
        self.ffmpeg = self.opt['ffmpeg']['ffmpeg_path']
        if not self.ffmpeg:
            assert shutil.which('ffmpeg'), '[error] ffmpeg doesn\'t exist'
            self.ffmpeg = shutil.which('ffmpeg')
        else:
            assert os.path.exists(self.ffmpeg), f'[error] {self.ffmpeg} doesn\'t exist'
        self.logger.info(f'[ffmpeg path] {self.ffmpeg}')
        self.psnr_ssim_frequency = opt['metric']['psnr_ssim_frequency']

        video = opt['video']
        self.video_duration = video['video_duration']
        s = str(self.video_duration % 60).zfill(2)
        m = str(self.video_duration // 60).zfill(2)
        h = str(self.video_duration // 3600).zfill(2)
        self.video_duration_str = f"{h}:{m}:{s}"
        self.video_fps = video['video_fps']
        assert self.video_fps % self.psnr_ssim_frequency == 0, "[error] video_fps mod psnr_ssim_frequency != 0."

        origin = video['origin']
        self.ori_video_dir = origin['video_dir']
        self.ori_video_name = origin['video_name']
        self.ori_projection_mode = origin['projection_mode']
        self.ori_video_path = osp.join(self.ori_video_dir, self.ori_video_name)
        assert os.path.exists(self.ori_video_path), f'[error] {self.ori_video_dir} doesn\'t exist'
        self.ori_ffmpeg_vf_option = origin['ffmpeg_vf_parameter']
        self.work_folder = osp.join(self.ori_video_dir, self.test_group, self.ori_video_name.split('.')[0], self.method_name)

        converted = video['converted']
        self.quality_list = converted['quality_list']
        self.projection_mode = converted['projection_mode']
        self.video_width = converted['width']
        self.video_height = converted['height']
        self.target_ffmpeg_vf_option = converted['ffmpeg_vf_parameter']

        if self.opt['method_settings']['background']['background_flag']:
            self.background_width = opt['method_settings']['background']['width']
            self.background_height = opt['method_settings']['background']['height']

    def process_video(self):
        pass

    def _convert_ori_video(self):
        """Convert original video's projection format and qp value."""
        os.makedirs(self.work_folder, exist_ok=True)
        os.chdir(self.work_folder)

        self.logger.info(f'[converting origin video] start; {self.ori_projection_mode} to {self.projection_mode}; qp_list={self.quality_list}')
        quality_bar = tqdm(self.quality_list, leave=False)
        for quality in quality_bar:
            quality_bar.set_description(f"[converting origin video] qp={quality}")

            cmd = f"{self.ffmpeg} " \
                  f"-r {self.video_fps} " \
                  f"-i {self.ori_video_path} " \
                  f"-threads {self.ffmpeg_thread} " \
                  f"-c:v libx264 " \
                  f"-ss 0:0:0 " \
                  f"-to {self.video_duration_str} " \
                  f"-preset faster " \
                  f"-qp {quality} " \
                  f"-vf v360={self.ori_ffmpeg_vf_option}:{self.target_ffmpeg_vf_option}" \
                  f",scale={self.video_width}x{self.video_height} " \
                  f"-y converted_{quality}.mp4 " \
                  f"-loglevel {self.ffmpeg_loglevel}"
            self.logger.debug(cmd)
            os.system(cmd)
        quality_bar.close()
        self.logger.info('[converting origin video] end')

        if self.opt['method_settings']['background']['background_flag']:
            self.logger.info('[generating background video] start')
            cmd = f"{self.ffmpeg} " \
                  f"-r {self.video_fps} " \
                  f"-i {self.ori_video_path} " \
                  f"-threads {self.ffmpeg_thread} " \
                  f"-c:v libx264 " \
                  f"-ss 0:0:0 " \
                  f"-to {self.video_duration_str} " \
                  f"-preset faster " \
                  f"-vf v360={self.ori_ffmpeg_vf_option}:{self.opt['method_settings']['background']['ffmpeg_vf_parameter']}" \
                  f",scale={self.background_width}x{self.background_height}" \
                  f",setdar={self.background_width}/{self.background_height} " \
                  f"-y background.mp4 " \
                  f"-loglevel {self.ffmpeg_loglevel}"
            self.logger.debug(cmd)
            os.system(cmd)
            self.logger.info('[generating background video] end')

    def _del_intermediate_file(self, target_folder, start_list, end_list):
        """
        Delete files and folders in target_folder without prefixes/suffixed in the start_list/end_list.

        Parameters
        ----------
        target_folder : str
            The absolute path of the pending folder.
        start_list : list
            Prefix list.
        end_list : list
            Suffix list.
        """
        self.logger.info('[delete intermediate file] start')
        os.chdir(self.work_folder)

        def _if_startswith(file, start_list):
            flag = False
            for start in start_list:
                if file.startswith(start):
                    flag = True
            return flag

        def _if_endswith(file, end_list):
            flag = False
            for end in end_list:
                if file.endswith(end):
                    flag = True
            return flag

        tmp_bar = tqdm(os.walk(target_folder, topdown=False), leave=False)
        for root, dirs, files in tmp_bar:
            for file in files:
                if _if_startswith(file, start_list) or _if_endswith(file, end_list):
                    continue
                else:
                    os.remove(os.path.join(root, file))
                    get_logger().debug(f"[delete intermediate file] deleted: {os.path.join(root, file)}")

            for dir in dirs:
                if any((_if_startswith(fname, start_list) or _if_endswith(fname, end_list)) for fname in
                       os.listdir(os.path.join(root, dir))):
                    continue
                else:
                    shutil.rmtree(os.path.join(root, dir))
                    get_logger().debug(f"[delete intermediate file] deleted: {os.path.join(root, dir)}")
        tmp_bar.close()

        self.logger.info('[delete intermediate file] end')

    def get_size(self, *args):
        """Read the corresponding file size from video_size.json based on the parameter list"""
        pass

    def get_background_size(self, *args):
        """Read the corresponding background file size from background_size.json based on the parameter list"""
        pass
