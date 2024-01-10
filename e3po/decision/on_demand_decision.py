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
from e3po.utils.registry import decision_registry
from .base_decision import BaseDecision
from e3po.utils.json import read_video_json
import os.path as osp
from e3po.utils import pre_processing_client_log
from e3po.utils.json import write_decision_json
from e3po.utils.misc import generate_motion_clock
from e3po.utils.misc import update_motion


@decision_registry.register()
class OnDemandDecision(BaseDecision):
    """
    On-demand decision, which is suitable for on_demand approaches.

    Parameters
    ----------
    opt : dict
        Configurations.
    """

    def __init__(self, opt):
        super(OnDemandDecision, self).__init__(opt)
        self.video_duration = self.system_opt['video']['video_duration']
        self.pre_download_duration = int(
            self.system_opt['network_trace']['pre_download_duration'] * 1000
        )
        self.base_ts = -1                  # starting timestamp of historical window

        # read json files
        video_size_json_uri = osp.join(self.source_folder, 'video_size.json')
        self.video_size = read_video_json(video_size_json_uri)

        # user related parameters
        self.network_stats = [{
            'rtt': self.system_opt['network_trace']['rtt'],
            'bandwidth': self.system_opt['network_trace']['bandwidth'],
            'curr_ts': -1
        }]
        self.video_info = {
            'width': self.system_opt['video']['origin']['width'],
            'height': self.system_opt['video']['origin']['height'],
            'projection': self.system_opt['video']['origin']['projection_mode'],
            'duration': self.system_opt['video']['video_duration'],
            'chunk_duration': self.system_opt['video']['chunk_duration'],
            'pre_download_duration': self.pre_download_duration,
            'range_fov': self.system_opt['metric']['range_fov']
        }

    def make_decision(self):
        """
        Performing download decision for on_demand approaches, and recording the decision results into JSON file.

        Returns
        -------
            None
        """

        curr_ts = 0
        motion_history = []
        motion_record = pre_processing_client_log(self.system_opt)
        motion_clock = generate_motion_clock(self, motion_record)

        approach = importlib.import_module(self.approach_module_name)
        user_data = None
        # pre_download_duration
        motion_history = update_motion(0, curr_ts, motion_history, motion_record[0])
        dl_list, user_data = approach.download_decision(self.network_stats, motion_history, self.video_size, curr_ts, user_data, self.video_info)
        write_decision_json(self.decision_json_uri, curr_ts, dl_list)

        # after pre_download_duration
        for motion_ts in motion_clock:
            curr_ts = motion_ts + self.pre_download_duration
            motion_history = update_motion(motion_ts, curr_ts, motion_history, motion_record[motion_ts])
            dl_list, user_data = approach.download_decision(self.network_stats, motion_history, self.video_size, curr_ts, user_data, self.video_info)
            write_decision_json(self.decision_json_uri, curr_ts, dl_list)

        self.logger.info(f"on_demand decision end.")
