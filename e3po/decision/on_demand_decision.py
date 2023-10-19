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

from collections import deque
from copy import deepcopy

from e3po.utils.registry import decision_registry
from .base_decision import BaseDecision
from e3po.projection import build_projection


@decision_registry.register()
class OnDemandDecision(BaseDecision):
    """
    On-demand decision, which is suitable for tile-based approaches.

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
        super(OnDemandDecision, self).__init__(opt)
        settings = opt['method_settings']
        self.decision_location = settings['decision_location'].lower()
        assert self.decision_location in ['client', 'server'], "[error] decision_location wrong. It should be set to the value in ['client', 'server']"
        self.decision_delay = settings['decision_delay']
        self.chunk_duration = settings['chunk_duration']
        self.next_download_idx = settings['pre_download_duration'] / self.chunk_duration
        assert self.next_download_idx % 1 == 0, f"pre_download_duration error!"
        self.next_download_idx = int(self.next_download_idx)
        self.hw_size = settings['hw_size'] * 1000
        self.pw_size = settings['pw_size']
        self.video_duration = opt['video']['video_duration']
        self.quality_list = opt['video']['converted']['quality_list']
        self.rtt = opt['network_trace']['rtt'] * 0.5 if self.decision_location == 'server' else 0

        self.base_ts = -1               # Starting timestamp of historical window data
        self.hw = deque()               # Queue for storing historical window data
        self.projection = build_projection(opt)
        self.tmp_result = {}            # To support more granular decisions

    def push_hw(self, motion_ts, motion):
        """
        Push input data into the queue self.hw.

        Parameters
        ----------
        motion_ts : int
            Motion timestamp.
        motion : dict
            Motion description information:
                {'yaw': yaw, 'pitch': pitch, 'scale': scale}
        """
        motion_ts += self.rtt
        if self.base_ts == -1:
            self.base_ts = motion_ts
        self.hw.append((motion_ts, motion))
        if list(self.hw)[-1][0] - list(self.hw)[0][0] > self.hw_size:
            self.hw.popleft()

    def decision(self):
        """
        Determine whether to make a decision based on historical information and return decision results

        Returns
        -------
        list
            Decision result list, which may be empty list.
        """
        result = []
        if self.next_download_idx >= self.video_duration / self.chunk_duration:
            return result

        predicted_record = self._predict_motion_tile()
        tile_record = self._tile_decision(predicted_record)
        bitrate_record = self._bitrate_decision(tile_record)

        for i in range(self.pw_size):
            tmp_tiles = tile_record[i]
            for j in range(len(tmp_tiles)):
                if tmp_tiles[j] not in self.tmp_result.keys():
                    self.tmp_result[tmp_tiles[j]] = bitrate_record[i][j]

        if list(self.hw)[-1][0] >= self.base_ts + self.next_download_idx * self.chunk_duration * 1000 - self.decision_delay:
            for i in range(self.pw_size):
                tmp_pw = {'chunk_idx': self.next_download_idx, 'decision_data': [{'pw_ts': list(self.hw)[-1][0]}]}
                for tile_idx in self.tmp_result.keys():
                    tmp_pw['decision_data'].append({'tile_idx': tile_idx, 'tile_bitrate': self.tmp_result[tile_idx]})
                result.append(tmp_pw)
                self.tmp_result = {}
                self.next_download_idx += 1

        return result


    def _predict_motion_tile(self):
        """
        Predict pw record based on the given hw and pw values and hw record.

        Returns
        -------
        list
            The predicted record list, which sequentially store the predicted motion of the future pw chunks.
             Each motion dictionary is stored in the following format:
                {'yaw ': yaw,' pitch ': pitch,' scale ': scale}
        """
        # Use exponential smoothing to predict the angle of each motion within pw for yaw and pitch.
        a = 0.3  # Parameters for exponential smoothing prediction
        predicted_motion = list(self.hw)[0][1]
        for motion_record in list(self.hw)[1:]:
            predicted_motion['yaw'] = a * predicted_motion['yaw'] + (1-a) * motion_record[1]['yaw']
            predicted_motion['pitch'] = a * predicted_motion['pitch'] + (1-a) * motion_record[1]['pitch']
            predicted_motion['scale'] = a * predicted_motion['scale'] + (1-a) * motion_record[1]['scale']

        # The current prediction method implemented is to use the same predicted motion for all chunks in pw.
        predicted_record = []
        for i in range(self.pw_size):
            predicted_record.append(deepcopy(predicted_motion))

        return predicted_record


    def _tile_decision(self, predicted_record):
        """
        Determine the tile range to be transmitted for each chunk within pw based on the predicted record.

        Parameters
        ----------
        predicted_record : list
            The predicted record list.

        Returns
        -------
        list
            Tile record list, storing the tile sequence number to be transmitted for each chunk of the future pw chunks of the decision.
        """
        # The current tile decision method is to sample the fov range corresponding to the predicted motion of each chunk,
        # and the union of the tile sets mapped by these sampling points is the tile set to be transmitted.
        tile_record = []
        for predicted_motion in predicted_record:
            tmp_tile_list, tmp_pixel_tile_list = self.projection.sphere_to_tile(predicted_motion)
            tile_record.append(tmp_tile_list)

        return tile_record


    def _bitrate_decision(self, tile_record):
        """
        Determine the bitrate for each tile of each chunk to be transmitted.

        Parameters
        ----------
        tile_record : list
            The tile record list.

        Returns
        -------
        list
            Bitrate list, storing the bitrate for each tile of each chunk to be transmitted.
        """
        bitrate_record = []
        for tiles in tile_record:
            tmp_bitrate = []
            for _ in tiles:
                tmp_bitrate.append(min(self.quality_list))
            bitrate_record.append(tmp_bitrate)

        return bitrate_record
