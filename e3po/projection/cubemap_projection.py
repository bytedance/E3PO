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

from e3po.utils.registry import projection_registry
from .tile_projection import TileProjection


@projection_registry.register()
class CubemapProjection(TileProjection):
    """
    Cubemap projection.

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

        face_size_w = w // 3
        face_size_h = h // 2

        x_sphere = np.round(np.cos(v) * np.cos(u), 9)
        y_sphere = np.round(np.cos(v) * np.sin(u), 9)
        z_sphere = np.round(np.sin(v), 9)

        dst_h, dst_w = np.shape(u)[:2]
        coor_x = np.zeros((dst_h, dst_w))
        coor_y = np.zeros((dst_h, dst_w))
        coor_u = np.zeros((dst_h, dst_w))

        for i in range(6):
            if i == 0:
                temp_index1 = np.where(y_sphere < 0, 1, -1)
                temp_index2 = np.where(abs(y_sphere) >= abs(x_sphere), 1, -2)
                temp_index3 = np.where(abs(y_sphere) >= abs(z_sphere), 1, -3)
                temp_index = (temp_index1 == np.where(temp_index2 == temp_index3, 1, -2))
                u_cub = x_sphere[temp_index] / abs(y_sphere[temp_index])
                v_cub = -z_sphere[temp_index] / abs(y_sphere[temp_index])
            elif i == 1:
                temp_index1 = np.where(x_sphere > 0, 1, -1)
                temp_index2 = np.where(abs(x_sphere) >= abs(y_sphere), 1, -2)
                temp_index3 = np.where(abs(x_sphere) >= abs(z_sphere), 1, -3)
                temp_index = (temp_index1 == np.where(temp_index2 == temp_index3, 1, -2))
                u_cub = y_sphere[temp_index] / abs(x_sphere[temp_index])
                v_cub = -z_sphere[temp_index] / abs(x_sphere[temp_index])
            elif i == 2:
                temp_index1 = np.where(y_sphere > 0, 1, -1)
                temp_index2 = np.where(abs(y_sphere) >= abs(x_sphere), 1, -2)
                temp_index3 = np.where(abs(y_sphere) >= abs(z_sphere), 1, -3)
                temp_index = (temp_index1 == np.where(temp_index2 == temp_index3, 1, -2))
                u_cub = -x_sphere[temp_index] / abs(y_sphere[temp_index])
                v_cub = -z_sphere[temp_index] / abs(y_sphere[temp_index])
            elif i == 3:
                temp_index1 = np.where(z_sphere < 0, 1, -1)
                temp_index2 = np.where(abs(z_sphere) >= abs(x_sphere), 1, -2)
                temp_index3 = np.where(abs(z_sphere) >= abs(y_sphere), 1, -3)
                temp_index = (temp_index1 == np.where(temp_index2 == temp_index3, 1, -2))
                u_cub = -x_sphere[temp_index] / abs(z_sphere[temp_index])
                v_cub = -y_sphere[temp_index] / abs(z_sphere[temp_index])
            elif i == 4:
                temp_index1 = np.where(x_sphere < 0, 1, -1)
                temp_index2 = np.where(abs(x_sphere) >= abs(y_sphere), 1, -2)
                temp_index3 = np.where(abs(x_sphere) >= abs(z_sphere), 1, -3)
                temp_index = (temp_index1 == np.where(temp_index2 == temp_index3, 1, -2))
                u_cub = z_sphere[temp_index] / abs(x_sphere[temp_index])
                v_cub = -y_sphere[temp_index] / abs(x_sphere[temp_index])
            elif i == 5:
                temp_index1 = np.where(z_sphere > 0, 1, -1)
                temp_index2 = np.where(abs(z_sphere) >= abs(x_sphere), 1, -2)
                temp_index3 = np.where(abs(z_sphere) >= abs(y_sphere), 1, -3)
                temp_index = (temp_index1 == np.where(temp_index2 == temp_index3, 1, -2))
                u_cub = x_sphere[temp_index] / abs(z_sphere[temp_index])
                v_cub = -y_sphere[temp_index] / abs(z_sphere[temp_index])
            face_index = i
            m_cub = (u_cub + 1) * face_size_w / 2 - 0.5
            n_cub = (v_cub + 1) * face_size_h / 2 - 0.5
            coor_u[temp_index] = face_index
            coor_x[temp_index] = (face_index % 3) * face_size_w + m_cub
            coor_y[temp_index] = (face_index // 3) * face_size_h + n_cub

            coor_x[temp_index] = np.clip(coor_x[temp_index], (face_index % 3) * face_size_w, (face_index % 3 + 1) * face_size_w - 1)
            coor_y[temp_index] = np.clip(coor_y[temp_index], (face_index // 3) * face_size_h, (face_index // 3 + 1) * face_size_h - 1)

        return [coor_x, coor_y]
