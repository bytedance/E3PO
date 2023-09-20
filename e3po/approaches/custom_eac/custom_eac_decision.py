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

from copy import deepcopy
from e3po.utils.registry import decision_registry
from e3po.decision.on_demand_decision import OnDemandDecision


@decision_registry.register()
class CustomEacDecision(OnDemandDecision):
    """
    Custom EAC approach, only relevant functions should be rewritten.

    Notes
    -----
    Almost all class public attributes are directly read or indirectly processed from the yaml configuration file.
    Their specific meanings can be found in 'docs/Config.md'.
    """

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
