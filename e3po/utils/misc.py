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

import os
import json
import numpy as np


def scan_file_name(dir_path, suffix=None):
    """
    Recursively scan all files with the specified suffix in the target folder and return the file names.

    Parameters
    ----------
    dir_path : str
        Path of the directory.
    suffix : str
        Expected file name suffix.

    Returns
    -------
    list
        All file names that meet the requirements.
    """
    result = []
    for root, dirs, files in os.walk(dir_path, topdown=False):
        if suffix is None:
            result += [os.path.splitext(os.path.basename(file)) for file in files if not file.startswith('.')]
        else:
            result += [os.path.splitext(os.path.basename(file))[0] for file in files if not file.startswith('.') and file.endswith(suffix)]
    return result


def write_json(result, json_path):
    """
    Write result to json file in json_path

    Parameters
    ----------
    result : list
        In json format
    json_path : str
        Absolute path of json file.
    """
    fpath, _ = os.path.split(json_path)
    os.makedirs(fpath, exist_ok=True)
    if os.path.exists(json_path):
        os.remove(json_path)
    with open(json_path, "w", encoding='utf-8') as f:
        json.dump(result, f, indent=2, sort_keys=True)

def calc_theta_hat(vam_size, vam_degW, vam_degH):
    rot_camera_inv = np.array([[0, 1, 0], [-1, 0, 0], [0, 0, 1]])
    vam_w, vam_h = vam_size

    u = (0 + 0.5) * 2 * np.tan(vam_degW / 2) / vam_w
    v = (0 + 0.5) * 2 * np.tan(vam_degH / 2) / vam_h

    # calculate the corresponding 3D coordinate (x, y, z), mapped from the positive X-axis
    x_scale = 1.0
    y_scale = -u + np.tan(vam_degW / 2)
    z_scale = -v + np.tan(vam_degH / 2)

    # mapping the point to the unit spherical surface
    x_hat = x_scale / np.sqrt(x_scale * x_scale + y_scale * y_scale + z_scale * z_scale)
    y_hat = y_scale / np.sqrt(x_scale * x_scale + y_scale * y_scale + z_scale * z_scale)
    z_hat = z_scale / np.sqrt(x_scale * x_scale + y_scale * y_scale + z_scale * z_scale)

    Sphere_xyz = np.array([x_hat, y_hat, z_hat])
    xyz_rotation_px = np.dot(rot_camera_inv, Sphere_xyz)    # matrix dot product
    phi = np.arctan2(xyz_rotation_px[1], xyz_rotation_px[0])
    theta = np.pi / 2 - np.arcsin(xyz_rotation_px[2])       # theta represents the angle between the point and the z axis

    phi_hat_px = np.arccos(np.cos(np.pi / 2 - phi) * np.cos(np.pi / 2 - theta))
    theta_hat_px = np.arcsin(np.sin(np.pi / 2 - theta) / np.sin(phi_hat_px))

    return theta_hat_px * 180 / np.pi

def calc_mapUV(phi_3d, theta_3d, vam_ypr, src_size):
    def phi_theta_2xyz(phi_theta):
        x1 = np.sin(phi_theta[1]) * np.cos(phi_theta[0])
        y1 = np.sin(phi_theta[1]) * np.sin(phi_theta[0])
        z1 = np.cos(phi_theta[1])
        zxy = [x1, y1, z1]
        return zxy

    erp_height, erp_width = src_size

    # calculate the spherical coordinate
    xyz_temp = phi_theta_2xyz([phi_3d, theta_3d])
    x, y, z = xyz_temp[0], xyz_temp[1], xyz_temp[2]

    # rotation angles
    a, b, r = vam_ypr

    # rotation matrix
    rot_a = np.array([np.cos(a) * np.cos(b), np.cos(a) * np.sin(b) * np.sin(r) - np.sin(a) * np.cos(r),
                      np.cos(a) * np.sin(b) * np.cos(r) + np.sin(a) * np.sin(r)])
    rot_b = np.array([np.sin(a) * np.cos(b), np.sin(a) * np.sin(b) * np.sin(r) + np.cos(a) * np.cos(r),
                      np.sin(a) * np.sin(b) * np.cos(r) - np.cos(a) * np.sin(r)])
    rot_c = np.array([-np.sin(b), np.cos(b) * np.sin(r), np.cos(b) * np.cos(r)])

    # rotate the image to the correct place
    xx = rot_a[0] * x + rot_a[1] * y + rot_a[2] * z
    yy = rot_b[0] * x + rot_b[1] * y + rot_b[2] * z
    zz = rot_c[0] * x + rot_c[1] * y + rot_c[2] * z
    xx = np.clip(xx, -1, 1)
    yy = np.clip(yy, -1, 1)
    zz = np.clip(zz, -1, 1)

    map_u = ((np.arctan2(yy, xx) + 2 * np.pi) % (2 * np.pi)) / (2 * np.pi) * erp_width - 0.5
    map_v = np.arccos(zz) * erp_height / np.pi - 0.5

    map_u = np.clip(map_u, 0, erp_width - 1)
    map_v = np.clip(map_v, 0, erp_height - 1)
    return map_u, map_v
