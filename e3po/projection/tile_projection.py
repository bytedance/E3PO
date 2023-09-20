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
class TileProjection(BaseProjection):
    """
    Tile based projection.

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
        super(TileProjection, self).__init__(opt)
        self.converted_width = int(opt['video']['converted']['width'])
        self.converted_height = int(opt['video']['converted']['height'])
        self.tile_width_num = int(opt['method_settings']['tile_width_num'])
        self.tile_height_num = int(opt['method_settings']['tile_height_num'])
        self.quality_list = opt['video']['converted']['quality_list']


    def sphere_to_tile(self, fov_ypr):
        """
        Sample the fov range corresponding to the spherical viewpoint coordinates,
        map the sampling points to the tiles they belong to,
        and return the tile union of all sampling points and the tile number corresponding to each pixel point.

        Parameters
        ----------
        fov_ypr : dict
            Viewpoint of FoV:
                {'yaw': yaw, 'pitch': pitch, 'scale': scale}


        Returns
        -------
        list
            [tile_list, pixel_tile_list].
            tile_list : The tile set corresponding to this set of sampling points.
            pixel_tile_list : Corresponding tile number for each sampling point.
        """
        yaw = float(fov_ypr['yaw'])
        pitch = float(fov_ypr['pitch'])

        uv = self.sphere_to_uv([yaw, pitch, 0], self.opt['metric']['sampling_size'])
        pixel_coord = self.uv_to_coor(uv, self.converted_width, self.converted_height)
        tile_list, pixel_tile_list = self._coord_to_tile(pixel_coord, self.converted_width, self.converted_height)
        return tile_list, pixel_tile_list

    @classmethod
    def uv_to_coor(cls, *args):
        pass

    def uv_to_fov(self, img, fov_uv):
        src_height, src_width = img.shape[:2]
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
        dstMap_u, dstMap_v = cv2.convertMaps(pixel_coord[0].astype(np.float32), pixel_coord[1].astype(np.float32),
                                             cv2.CV_16SC2)
        fov_img = cv2.remap(img, dstMap_u, dstMap_v, inter_order)

        return fov_img

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
        pixel_tile_list = ((coor_y // (h // self.tile_height_num)) * self.tile_width_num) \
                          + (coor_x // (w // self.tile_width_num))

        tile_list = np.unique(pixel_tile_list)
        return tile_list, pixel_tile_list



    def _fov_result(self, fov_uv, w, h, client_tile_list, server_tile_list, server_qp_list):
        """
        Calculate each point in FoV image should be sampled from which coordinate of the transmitted content.

        Parameters
        ----------
        fov_uv : numpy.ndarray
            The spatial polar coordinates of the sampling points based on given FoV direction and resolution.
        w : int
            Image pixel width.
        h : int
            Image pixel height.
        client_tile_list : list
            The tile number corresponding to each pixel in FoV
        server_tile_list : list
            Transmitted tile set from the server.
        server_qp_list: list
            The corresponding qp values of the server_tile_list.

        Returns
        -------
        list
            Pixel coordinates of sampling points:
                [coor_x, coor_y]
        """
        coor_x_arr = np.zeros((fov_uv.shape[:2]), np.float32)
        coor_y_arr = np.zeros((fov_uv.shape[:2]), np.float32)

        set_server_qp_list = set(server_qp_list)                            # transform the server_qp_list to set format, remove duplicates
        for qp_value in set_server_qp_list:
            qp_idx = self.quality_list.index(qp_value)
            server_qp_mask = np.isin(server_qp_list, qp_value)
            server_tile_list_qp = np.array(server_tile_list)[server_qp_mask]
            in_server_mask = np.isin(client_tile_list, server_tile_list_qp)
            in_server_coor_x, in_server_coor_y = self.uv_to_coor(fov_uv[in_server_mask], w, h)
            coor_x_arr[in_server_mask], coor_y_arr[in_server_mask] = w * qp_idx + in_server_coor_x.reshape((-1,)), \
                                                                     in_server_coor_y.reshape((-1,))

        if self.opt['method_settings']['background']['background_flag']:
            background_w = self.opt['method_settings']['background']['width']
            background_h = self.opt['method_settings']['background']['height']
            out_server_mask = (in_server_mask == False)

            out_server_coor_x, out_server_coor_y = projection_registry[self.opt['method_settings']['background']
                                                    ['projection_type']].uv_to_coor(fov_uv[out_server_mask], background_w, background_h)
            coor_x_arr[out_server_mask], coor_y_arr[out_server_mask] = w*len(self.quality_list) + out_server_coor_x.reshape((-1,)), \
                                                                       out_server_coor_y.reshape((-1,))

        return coor_x_arr, coor_y_arr


    def generate_fov_coor(self, *args):
        """This function should be implemented by each contestant in their own projection file."""
        pass
