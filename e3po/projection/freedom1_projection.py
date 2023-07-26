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
class Freedom1Projection(BaseProjection):
    """
    Freedom1 projection.

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
        super(Freedom1Projection, self).__init__(opt)
        self.converted_width = int(opt['video']['converted']['width'])
        self.converted_height = int(opt['video']['converted']['height'])
        self.crop_factor = [eval(v) for v in opt['method_settings']['crop_factor']]
        self.scale_factors = {k: eval(v) for k, v in opt['method_settings']['scale_factors'].items()}
        self.vam_size = opt['method_settings']['vam_size']

    def uv_to_coor(self, *args):
        """
        Convert the UV coordinates of the sampling point to pixel coordinates.

        Returns
        -------
        list
            Pixel coordinates of sampling points:
                [coor_x, coor_y]
        """
        uv, server_motion = args

        server_scale = server_motion['scale']
        a, b, r = [server_motion['yaw'], -server_motion['pitch'], 0]
        rot_a = np.array([np.cos(a) * np.cos(b), np.sin(a) * np.cos(b), -np.sin(b)])
        rot_b = np.array([np.cos(a) * np.sin(b) * np.sin(r) - np.sin(a) * np.cos(r),
                          np.sin(a) * np.sin(b) * np.sin(r) + np.cos(a) * np.cos(r), np.cos(b) * np.sin(r)])
        rot_c = np.array([np.cos(a) * np.sin(b) * np.cos(r) + np.sin(a) * np.sin(r),
                          np.sin(a) * np.sin(b) * np.cos(r) - np.cos(a) * np.sin(r), np.cos(b) * np.cos(r)])

        u, v = np.split(uv, 2, axis=-1)
        v = np.pi / 2 - v
        u = u.reshape(u.shape[:2])
        v = v.reshape(v.shape[:2])

        x = np.sin(v) * np.cos(u)
        y = np.sin(v) * np.sin(u)
        z = np.cos(v)

        xx = rot_a[0] * x + rot_a[1] * y + rot_a[2] * z
        yy = rot_b[0] * x + rot_b[1] * y + rot_b[2] * z
        zz = rot_c[0] * x + rot_c[1] * y + rot_c[2] * z
        zz = np.clip(zz, -1, 1)

        u = np.arctan2(yy, xx)
        v = np.pi / 2 - np.arccos(zz)

        # Calculate Vam coverage
        view_coverage_width = self.crop_factor[0] / self.scale_factors[server_scale] * (2 * np.pi)
        view_coverage_height = self.crop_factor[1] / self.scale_factors[server_scale] * np.pi
        view_coverage_height = view_coverage_height if view_coverage_height <= np.pi else np.pi
        coor_x = (u / view_coverage_width + 0.5) * self.vam_size[0] - 0.5
        coor_y = (-v / view_coverage_height + 0.5) * self.vam_size[1] - 0.5

        return [coor_x, coor_y]

    def get_fov(self, *args):
        """
        Generate FoV images for client viewing.

        Returns
        -------
        numpy.ndarray
            FoV images for client viewing.
        """
        concat_img, fov_uv, server_motion = args
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

        coor_x_arr, coor_y_arr = self._fov_result(fov_uv, server_motion)
        dst_map_u, dst_map_v = cv2.convertMaps(coor_x_arr.astype(np.float32), coor_y_arr.astype(np.float32), cv2.CV_16SC2)
        fov_result = cv2.remap(concat_img, dst_map_u, dst_map_v, inter_order)

        return fov_result

    def _fov_result(self, fov_uv, server_motion):
        """
        Calculate each point in FoV image should be sampled from which coordinate of the transmitted content.

        Parameters
        ----------
        fov_uv : numpy.ndarray
            The spatial polar coordinates of the sampling points based on given FoV direction and resolution.
        server_motion : list
            Motion for generating VAM:
                {'yaw': yaw, 'pitch': pitch, 'scale': scale}

        Returns
        -------
        list
            Pixel coordinates of sampling points:
                [coor_x, coor_y]
        """
        coor_x_arr, coor_y_arr = self.uv_to_coor(fov_uv, server_motion)

        vam_width, vam_height = self.vam_size
        coor_x_arr = np.clip(coor_x_arr, 0, vam_width - 1)
        coor_y_arr = np.clip(coor_y_arr, 0, vam_height - 1)

        return coor_x_arr, coor_y_arr
