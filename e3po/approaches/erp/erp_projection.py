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

import numpy as np
import cv2

from e3po.utils.registry import projection_registry
from e3po.projection.tile_projection import TileProjection

@projection_registry.register()
class ErpProjection(TileProjection):
    """
    ERP projection.

    Parameters
    ----------
    opt : dict
        Configurations.

    Notes
    -----
    Almost all class public attributes are directly read or indirectly processed from the yaml configuration file.
    Their specific meanings can be found in 'docs/Config.md'.
    """
    @classmethod
    def uv_to_coor(cls, *args):
        """
        Convert the UV coordinates of the sampling point to pixel coordinates.

        Returns
        -------
        list
            Pixel coordinates of sampling points:
                [coor_x, coor_y]
        """
        uv, w, h = args

        u, v = np.split(uv, 2, axis=-1)
        u = u.reshape(u.shape[:2])
        v = v.reshape(v.shape[:2])

        coor_x = (u / (2 * np.pi) + 0.5) * w - 0.5
        coor_y = (-v / np.pi + 0.5) * h - 0.5

        coor_x = np.clip(coor_x, 0, w - 1)
        coor_y = np.clip(coor_y, 0, h - 1)

        return [coor_x, coor_y]


    def generate_fov_coor(self, *args):
        """
        Get the coordinates of FoV area on the concat image.

        Parameters
        ----------
        *args :
        concat_img : ndarray
            A array including the concatenated high-resolution tiles and low-resolution background image
            (if there is a background stream).
        src_width: int
            The width of original full frame.
        src_height: int
            The height of original full frame.
        fov_uv:
            The direction user actually views during playback.
        server_tile_list:
            After decision, selected tiles at the server.
        server_qp_list:
            After decision, the corresponding qp values of selected tiles.

        Returns
        -------
        numpy.ndarray
            Coordinates of FoV area on the concat image.
        """

        concat_img, src_width, src_height, fov_uv, server_tile_list, server_qp_list = args

        # calculate the pixel coordinates with given viewing direction (from the motion trace)
        pixel_coord = self.uv_to_coor(fov_uv, src_width, src_height)

        # determine the tile list with given pixel coordinates
        tile_list, client_tile_list = self._coord_to_tile(pixel_coord, src_width, src_height)

        # calculate the corresponding pixel coordinates with given viewing direction
        coor_x_arr, coor_y_arr = self._fov_result(fov_uv, src_width, src_height, client_tile_list, server_tile_list, server_qp_list)

        return coor_x_arr, coor_y_arr