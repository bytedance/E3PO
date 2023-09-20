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
class CustomEacProjection(TileProjection):
    """
    Custom EAC projection.

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

            u_cub = np.arctan(u_cub) * 4 / np.pi
            v_cub = np.arctan(v_cub) * 4 / np.pi
            m_cub = (u_cub + 1) * face_size_w / 2 - 0.5
            n_cub = (v_cub + 1) * face_size_h / 2 - 0.5
            coor_u[temp_index] = face_index
            coor_x[temp_index] = (face_index % 3) * face_size_w + m_cub
            coor_y[temp_index] = (face_index // 3) * face_size_h + n_cub

            coor_x[temp_index] = np.clip(coor_x[temp_index], (face_index % 3) * face_size_w, (face_index % 3 + 1) * face_size_w - 1)
            coor_y[temp_index] = np.clip(coor_y[temp_index], (face_index // 3) * face_size_h, (face_index // 3 + 1) * face_size_h - 1)

        return [coor_x, coor_y]



    def _coord_to_tile(self, pixel_coord, w, h):
        """
        Convert a set of 2D pixel plane coordinates into a tile ordinal list.

        Parameters
        ----------
        pixel_coord : list
            [coor_x, coor_y], stores the x and y pixel coordinates of a series of sampling points.
        w : int
            Frame pixel width.
        h : int
            Frame pixel height.

        Returns
        -------
        list
            [tile_list, pixel_tile_list].
            tile_list : The tile set corresponding to this set of sampling points,
            pixel_tile_list : Corresponding tile number for each sampling point.
        """
        coor_x, coor_y = pixel_coord
        pixel_tile_list = ((coor_y // (h // self.tile_height_num)) * self.tile_width_num) + (
                coor_x // (w // self.tile_width_num))

        big_tile_set1 = []
        bit_tile_set2 = []
        for i in range(self.tile_height_num // 2, self.tile_height_num):
            for j in range(self.tile_width_num):
                tile_idx = j + i * self.tile_width_num
                if j < self.tile_width_num // 3:
                    big_tile_set1.append(tile_idx)
                elif j >= (self.tile_width_num // 3 * 2):
                    bit_tile_set2.append(tile_idx)
                else:
                    continue
        pixel_tile_list[np.isin(pixel_tile_list, big_tile_set1)] = big_tile_set1[0]
        pixel_tile_list[np.isin(pixel_tile_list, bit_tile_set2)] = bit_tile_set2[0]

        tile_list = np.unique(pixel_tile_list)
        return tile_list, pixel_tile_list


    def erp_to_eac(self, img, inter_mode):
        """
        Convert an ERP image into an EAC image.

        Parameters
        ----------
        img : numpy.ndarray
            Input ERP image.
        inter_mode : str
            Interpolation mode。

        Returns
        -------
        numpy.ndarray
            Output EAC image.
        """
        if len(img.shape) == 2:
            img = img[..., None]
        assert len(img.shape) == 3
        h, w = img.shape[:2]
        face_size = h // 2
        cub_height = face_size * 2
        cub_width = face_size * 3

        u = (np.linspace(0.5, cub_width - 0.5, cub_width)) * 2 / face_size - 1
        v = (np.linspace(0.5, cub_height - 0.5, cub_height)) * 2 / face_size - 1

        u = np.tan(u * np.pi / 4)
        v = np.tan(v * np.pi / 4)

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

        u_temp = np.tile(u, (v.shape[0], 1))
        v_temp = np.tile(v, (u.shape[0], 1)).transpose()

        x_temp = np.zeros((u_temp.shape[0], u_temp.shape[1]), np.float32)
        y_temp = np.zeros((u_temp.shape[0], u_temp.shape[1]), np.float32)
        z_temp = np.zeros((u_temp.shape[0], u_temp.shape[1]), np.float32)

        # 0
        x_temp[:face_size, :face_size] = -u_temp[:face_size, :face_size]
        y_temp[:face_size, :face_size] = 1
        z_temp[:face_size, :face_size] = -v_temp[:face_size, :face_size]

        # 1
        x_temp[:face_size, face_size:face_size * 2] = -1
        y_temp[:face_size, face_size:face_size * 2] = -u_temp[:face_size, :face_size]
        z_temp[:face_size, face_size:face_size * 2] = -v_temp[:face_size, :face_size]

        # 2
        x_temp[:face_size, face_size * 2:] = u_temp[:face_size, :face_size]
        y_temp[:face_size, face_size * 2:] = -1
        z_temp[:face_size, face_size * 2:] = -v_temp[:face_size, :face_size]

        # 3
        x_temp[face_size:, :face_size] = u_temp[:face_size, :face_size]
        y_temp[face_size:, :face_size] = v_temp[:face_size, :face_size]
        z_temp[face_size:, :face_size] = -1

        # 4
        x_temp[face_size:, face_size:face_size * 2] = 1
        y_temp[face_size:, face_size:face_size * 2] = v_temp[:face_size, :face_size]
        z_temp[face_size:, face_size:face_size * 2] = u_temp[:face_size, :face_size]

        # 5
        x_temp[face_size:, face_size * 2:] = -u_temp[:face_size, :face_size]
        y_temp[face_size:, face_size * 2:] = v_temp[:face_size, :face_size]
        z_temp[face_size:, face_size * 2:] = 1

        phi = (np.arctan2(y_temp, x_temp) + 2 * np.pi) % (2 * np.pi)
        theta = np.arccos(z_temp / np.sqrt(x_temp ** 2 + y_temp ** 2 + z_temp ** 2))

        coor_x = (phi / (2 * np.pi)) * w - 0.5
        coor_y = (theta / np.pi) * h - 0.5

        coor_x = np.clip(coor_x, 0, w - 1)
        coor_y = np.clip(coor_y, 0, h - 1)
        dstMap_u, dstMap_v = cv2.convertMaps(coor_x.astype(np.float32), coor_y.astype(np.float32), cv2.CV_16SC2)

        dst_img = cv2.remap(img, dstMap_u, dstMap_v, inter_order)
        return dst_img



    def generate_fov_coor(self, *args):
        """
        Get the coordinates of FoV area on the concat image.

        Parameters
        ----------
        *args :
        concat_img : ndarray
            An array including the concatenated high-resolution tiles and low-resolution background image
            (if there is a background stream).
        src_width: int
            The width of original full frame.
        src_height: int
            The height of original full frame.
        fov_uv:
            The direction user actually views during playback.
        server_tile_list:
            After decision, selected tiles at the server
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