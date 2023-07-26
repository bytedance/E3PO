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
from .base_projection import BaseProjection


@projection_registry.register()
class FullTransmissionProjection(BaseProjection):
    """
    Full transmission projection.

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
        super(FullTransmissionProjection, self).__init__(opt)
        self.converted_width = int(opt['video']['converted']['width'])
        self.converted_height = int(opt['video']['converted']['height'])

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

    def get_fov(self, *args):
        """
        Generate FoV images for client viewing.

        Returns
        -------
        numpy.ndarray
            FoV images for client viewing.
        """
        img, src_width, src_height, fov_uv = args

        inter_mode = self.opt['metric']['inter_mode']
        if inter_mode == 'bilinear':
            inter_order = cv2.INTER_LINEAR
        elif inter_mode == 'nearest':
            inter_order = cv2.INTER_NEAREST
        elif inter_mode == 'cubic':
            inter_order = cv2.INTER_CUBIC
        elif inter_mode == 'area':
            inter_order = cv2.INTER_AREA
        elif inter_mode == 'lanczos4':
            inter_order = cv2.INTER_LANCZOS4
        else:
            raise NotImplementedError('unknown mode')

        pixel_coord = self.uv_to_coor(fov_uv, src_width, src_height)
        dstMap_u, dstMap_v = cv2.convertMaps(pixel_coord[0].astype(np.float32), pixel_coord[1].astype(np.float32), cv2.CV_16SC2)
        fov_img = cv2.remap(img, dstMap_u, dstMap_v, inter_order)

        return fov_img
