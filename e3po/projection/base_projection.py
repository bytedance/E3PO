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

from e3po.utils import get_logger


class BaseProjection:
    """
    Base projection.

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
        self.opt = opt
        self.logger = get_logger()

        self.fov_range = opt['metric']['range_fov']

    def sphere_to_uv(self, fov_ypr, sampling_size):
        """
        Sample the given FOV at the given sampling frequency and output the spatial polar coordinates of the sampling points.

        Parameters
        ----------
        fov_ypr : list
            Viewpoint of FoV, [yaw, pitch, roll]
        sampling_size : list
            Wide and high sampling frequencies

        Returns
        -------
        numpy.ndarray
            The spatial polar coordinates of the sampling points.
        """
        def _xyzpers(fov_x, fov_y, vp_yaw, vp_pitch, vp_roll, sampling_size):
            """
            Sample the given FOV at the given sampling frequency and output the xyz coordinates of the sampling points.

            Parameters
            ----------
            fov_x : int
                Fov width (in radians).
            fov_y : int
                Fov height (in radians).
            vp_yaw : int
                Viewpoint yaw (in radians).
            vp_pitch : int
                Viewpoint pitch (in radians).
            vp_roll : int
                Viewpoint roll (in radians).

            Returns
            -------
            numpy.ndarray
                The xyz coordinates of the sampling points.
            """
            def _rotation_matrix(rad, ax):
                """
                Generate rotation matrix.

                Parameters
                ----------
                rad : int
                    Angle (in radians).
                ax : list
                    Vector.

                Returns
                -------
                numpy.ndarray
                    The rotation matrix.
                """
                ax = np.array(ax)
                assert len(ax.shape) == 1 and ax.shape[0] == 3
                ax = ax / np.sqrt((ax ** 2).sum())
                R = np.diag([np.cos(rad)] * 3)
                R = R + np.outer(ax, ax) * (1.0 - np.cos(rad))

                ax = ax * np.sin(rad)
                R = R + np.array([[0, -ax[2], ax[1]],
                                  [ax[2], 0, -ax[0]],
                                  [-ax[1], ax[0], 0]])
                return R

            out = np.ones((*sampling_size, 3), np.float32)
            x_max = np.tan(fov_x / 2)  # The default ball radius is 1.
            y_max = np.tan(fov_y / 2)
            x_rng = np.linspace(-x_max, x_max, num=sampling_size[1], dtype=np.float32)
            y_rng = np.linspace(-y_max, y_max, num=sampling_size[0], dtype=np.float32)

            a = np.meshgrid(x_rng, -y_rng)
            out[..., :2] = np.stack(a, -1)  # Obtained sampling point coordinates.
            Rx = _rotation_matrix(vp_pitch, [1, 0, 0])
            Ry = _rotation_matrix(vp_yaw, [0, 1, 0])
            Ri = _rotation_matrix(vp_roll, np.array([0, 0, 1.0]).dot(Rx).dot(Ry))

            return out.dot(Rx).dot(Ry).dot(Ri)  # The xyz coordinates of each row of pixel points (3D).

        def _xyz2uv(xyz):
            """
            Convert spatial rectangular coordinates to spatial polar coordinates.

            Parameters
            ----------
            xyz : numpy.ndarray
                Spatial rectangular coordinate.

            Returns
            -------
            numpy.ndarray
                Spatial polar coordinates.
            """
            x, y, z = np.split(xyz, 3, axis=-1)
            u = np.arctan2(x, z)
            c = np.sqrt(x ** 2 + z ** 2)
            v = np.arctan2(y, c)
            return np.concatenate([u, v], axis=-1)

        # Calculate given fov_ Under range, the radians of width x and height y of fov.
        try:
            fov_x, fov_y = self.fov_range[0] * np.pi / 180, self.fov_range[1] * np.pi / 180
        except:
            fov_x, fov_y = 90 * np.pi / 180, 90 * np.pi / 180

        # Calculate the yaw, pitch, and roll radians of vam rotation.
        yaw_tmp, pitch_tmp, roll_tmp = fov_ypr
        vp_yaw = -yaw_tmp
        vp_pitch = pitch_tmp
        vp_roll = roll_tmp

        vp_xyz = _xyzpers(fov_x, fov_y, vp_yaw, vp_pitch, vp_roll, sampling_size)
        uv = _xyz2uv(vp_xyz)
        return uv

    @classmethod
    def uv_to_coor(cls, *args):
        pass

    def uv_to_fov(self, *args):
        pass

    def generate_fov_coor(self, *args):
        pass