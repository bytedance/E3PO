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

import importlib
from .base_data import BaseData
from e3po.utils.registry import data_registry
from e3po.utils import pre_processing_client_log
from e3po.utils import update_motion, extract_frame, generate_dst_frame_uri, save_video_frame
from e3po.utils.data_utilities import update_chunk_info, encode_dst_video, get_video_frame_sizes,\
    remove_temp_files
from e3po.utils.json import write_video_json, update_video_json
from e3po.utils.misc import generate_motion_clock


@data_registry.register()
class TranscodingData(BaseData):
    """
    Video preprocessing module for transcoding approach.

    Parameters
    ----------
    opt : dict
        Configurations.
    """
    def __init__(self, opt):
        """
        Transcoding approaches should configure initial parameters in this function.

        Parameters
        ----------
        opt : dict
            Configurations.
        """
        super(TranscodingData, self).__init__(opt)

        # system related information
        self.video_info = {
            'width': self.system_opt['video']['origin']['width'],
            'height': self.system_opt['video']['origin']['height'],
            'projection': self.system_opt['video']['origin']['projection_mode'],
            'duration': self.system_opt['video']['video_duration'],
            'video_fps': self.system_opt['video']['video_fps'],
            'uri': self.ori_video_uri
        }
        self.rtt = self.system_opt['network_trace']['rtt']

        # user related information
        self.network_stats = [{
            'rtt': self.system_opt['network_trace']['rtt'],
            'bandwidth': self.system_opt['network_trace']['bandwidth'],
            'curr_ts': -1
        }]

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
        motion_record = pre_processing_client_log(self.system_opt)
        motion_clock = generate_motion_clock(self, motion_record)

        motion_history = []
        motion_history = update_motion(0, 0, motion_history, motion_record[0])
        last_frame_idx = -1
        pre_downlode_duration = self.rtt
        update_interval = int(1000 / self.system_opt['motion_trace']['motion_frequency'])

        # pre_download_duration
        for curr_ts in range(0, int(pre_downlode_duration), update_interval):
            curr_frame_idx = int(curr_ts * self.video_info['video_fps'] // 1000.0)
            if curr_frame_idx == last_frame_idx:
                continue
            curr_video_frame = extract_frame(self.video_info['uri'], curr_frame_idx, self.ffmpeg_settings)
            last_frame_idx = curr_frame_idx
            dst_video_frame, user_video_spec, user_data = approach.transcode_video(curr_video_frame, curr_frame_idx, self.network_stats, motion_history, user_data, self.video_info)
            dst_video_frame_uri = generate_dst_frame_uri(self.dst_video_folder, curr_frame_idx)
            save_video_frame(dst_video_frame_uri, dst_video_frame)
            frame_info = update_chunk_info(self, curr_frame_idx)
            write_video_json(self.json_path, 0, frame_info, user_video_spec)

        # after pre_download_duration
        for motion_ts in motion_clock:
            curr_ts = motion_ts + pre_downlode_duration
            motion_history = update_motion(motion_ts, curr_ts, motion_history, motion_record[motion_ts])
            curr_frame_idx = int(curr_ts * self.video_info['video_fps'] // 1000.0)
            if curr_frame_idx >= int(self.video_info['video_fps']) * int(self.video_info['duration']):
                continue
            if curr_frame_idx == last_frame_idx:
                continue
            curr_video_frame = extract_frame(self.video_info['uri'], curr_frame_idx, self.ffmpeg_settings)
            last_frame_idx = curr_frame_idx
            dst_video_frame, user_video_spec, user_data = approach.transcode_video(curr_video_frame, curr_frame_idx, self.network_stats, motion_history, user_data, self.video_info)
            dst_video_frame_uri = generate_dst_frame_uri(self.dst_video_folder, curr_frame_idx)
            save_video_frame(dst_video_frame_uri, dst_video_frame)
            frame_info = update_chunk_info(self, curr_frame_idx)
            write_video_json(self.json_path, 0, frame_info, user_video_spec)

        dst_video_uri = encode_dst_video(self, self.dst_video_folder, self.encoding_params, [])
        dst_video_sizes = get_video_frame_sizes(self.ffmpeg_settings, dst_video_uri)
        update_video_json(self.json_path, dst_video_sizes)
        remove_temp_files(self.dst_video_folder)

        self.logger.info(f"transcoding preprocessing end.")

