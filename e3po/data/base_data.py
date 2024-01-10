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

import os
import os.path as osp
from e3po.utils import get_logger
import shutil


class BaseData:
    """
    Base data module for preprocessing video.

    Parameters
    ----------
    opt : dict
        Configurations.

    Notes
    -----
    Almost all class public attributes are directly read or indirectly processed from the yaml configuration file.
    """
    def __init__(self, opt):
        self.opt = opt
        self.system_opt = opt['e3po_settings']
        self.logger = get_logger()

        # ffmpeg related information
        self.ffmpeg_settings = self.system_opt['ffmpeg']
        if not self.ffmpeg_settings['ffmpeg_path']:
            assert shutil.which('ffmpeg'), '[error] ffmpeg doesn\'t exist'
            self.ffmpeg_settings['ffmpeg_path'] = shutil.which('ffmpeg')
        else:
            assert os.path.exists(self.ffmpeg_settings['ffmpeg_path']), \
                f'[error] {self.ffmpeg_settings["ffmpeg_path"]} doesn\'t exist'

        # evaluation related information
        origin = self.system_opt['video']['origin']
        self.ori_video_dir = origin['video_dir']
        self.test_group = opt['test_group']
        self.ori_video_name = origin['video_name']
        self.ori_projection_mode = origin['projection_mode']
        self.approach_folder_name = self.opt['approach_name']
        self.approach_name = self.opt['approach_name']
        self.approach_mode = self.opt['approach_type']
        self.approach_module_name = f"e3po.approaches.{self.approach_folder_name}.{self.approach_name}_approach"

        self.work_folder = osp.join(
            self.ori_video_dir,
            self.test_group,
            self.ori_video_name.split('.')[0],
            self.approach_folder_name
        )
        os.makedirs(self.work_folder, exist_ok=True)

        self.json_path = osp.join(self.work_folder, 'video_size.json')
        try:
            if os.path.exists(self.json_path):
                os.remove(self.json_path)
        except Exception as e:
            print(f"An error occurred while deleting the json file {self.json_path}: {e}")
        self.dst_video_folder = osp.join(self.work_folder, 'dst_video_folder')
        try:
            if os.path.exists(self.dst_video_folder) and os.path.isdir(self.dst_video_folder):
                shutil.rmtree(self.dst_video_folder)
            os.makedirs(self.dst_video_folder, exist_ok=True)
        except Exception as e:
            print(f"An error occurred while deleting the folder {self.dst_video_folder}: {e}")

        self.encoding_params = self.system_opt['encoding_params']
        self.video_duration = self.system_opt['video']['video_duration']
        self.ori_video_uri = osp.join(self.ori_video_dir, self.ori_video_name)
