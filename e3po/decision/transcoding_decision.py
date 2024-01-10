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

from e3po.utils.registry import decision_registry
from .base_decision import BaseDecision
from e3po.utils.json import write_decision_json


@decision_registry.register()
class TranscodingDecision(BaseDecision):
    """
    Transcoding decision, which is suitable for transcoding approaches.

    Parameters
    ----------
    opt : dict
        Configurations.
    """

    def __init__(self, opt):
        super(TranscodingDecision, self).__init__(opt)
        self.video_info = {
            'width': self.system_opt['video']['origin']['width'],
            'height': self.system_opt['video']['origin']['height'],
            'projection': self.system_opt['video']['origin']['projection_mode'],
            'duration': self.system_opt['video']['video_duration'],
            'video_fps': self.system_opt['video']['video_fps'],
            'range_fov': self.system_opt['metric']['range_fov']
        }
        self.rtt = self.system_opt['network_trace']['rtt']

    def make_decision(self):
        """
        Performing download decision for transcoding approaches, and recording the decision results into JSON file.

        Returns
        -------
            None
        """

        last_frame_idx = -1
        update_interval = int(1000 / self.system_opt['motion_trace']['motion_frequency'])
        video_duration = self.video_info['duration'] * 1000

        for curr_ts in range(0, video_duration, update_interval):
            curr_frame_idx = int(curr_ts * self.video_info['video_fps'] // 1000.0)
            if curr_frame_idx == last_frame_idx:
                continue
            tile_id = [f"chunk_{str(curr_frame_idx).zfill(4)}_tile_{str(1).zfill(3)}"]
            dl_list = {
                "chunk_idx": curr_frame_idx,
                "decision_data": {"tile_info": tile_id}
            }
            write_decision_json(self.decision_json_uri, curr_ts, [dl_list])
            last_frame_idx = curr_frame_idx

        self.logger.info(f"transcoding decision end.")