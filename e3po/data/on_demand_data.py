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
import importlib

from e3po.utils.registry import data_registry
from .base_data import BaseData
from e3po.utils.json import write_video_json
from e3po.utils.data_utilities import generate_source_video, update_chunk_info, \
    encode_dst_video, get_video_size, remove_temp_files, remove_temp_video


@data_registry.register()
class OnDemandData(BaseData):
    """
    Video preprocessing module for on_demand approach.

    Parameters
    ----------
    opt : dict
        Configurations.
    """
    def __init__(self, opt):
        """
        Each approach should configure initial parameters in this function.

        Parameters
        ----------
        opt : dict
            Configurations.
        """
        super(OnDemandData, self).__init__(opt)

        # system related information
        self.encoding_params = self.system_opt['encoding_params']
        self.video_duration = self.system_opt['video']['video_duration']
        self.ori_video_uri = osp.join(self.ori_video_dir, self.ori_video_name)
        self.video_info = {
            'width': self.system_opt['video']['origin']['width'],
            'height': self.system_opt['video']['origin']['height'],
            'projection': self.system_opt['video']['origin']['projection_mode'],
            'duration': self.system_opt['video']['video_duration'],
            'uri': self.ori_video_uri
        }

        # on_demand approaches related information
        self.chunk_duration = self.system_opt['video']['chunk_duration']
        self.chunk_num = int(self.video_duration / self.chunk_duration)

    def make_preprocessing(self):
        """
        Preprocessing the original video for transcoding approaches, and recording the preprocessing results into JSON file.

        Returns
        -------
            None
        """

        approach = importlib.import_module(self.approach_module_name)
        user_data = None
        user_data = approach.video_analysis(user_data, self.video_info)
        for chunk_idx in range(self.chunk_num):
            source_video_uri = generate_source_video(self, self.ori_video_uri, chunk_idx)
            chunk_info = update_chunk_info(self, chunk_idx)
            while True:
                user_video_spec, user_data = approach.preprocess_video(source_video_uri, self.dst_video_folder, chunk_info, user_data, self.video_info)
                if user_video_spec is None:
                    break
                dst_video_uri = encode_dst_video(self, self.dst_video_folder, self.encoding_params, user_video_spec)
                dst_video_size = get_video_size(dst_video_uri)
                remove_temp_files(self.dst_video_folder)
                write_video_json(self.json_path, dst_video_size, chunk_info, user_video_spec)
            remove_temp_video(source_video_uri)
            if os.path.exists(user_data['transcode_video_uri']):
                remove_temp_video(user_data['transcode_video_uri'])

        self.logger.info(f"on_demand preprocessing end.")