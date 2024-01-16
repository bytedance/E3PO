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

import copy
import numpy as np


def fov_to_3d_polar_coord(fov_direction, fov_range, fov_resolution):
    """
    Given fov information, convert it to 3D polar coordinates.

    Parameters
    ----------
    fov_direction: dict
        The orientation of fov, with format {pitch: , yaw: , roll:}
    fov_range: list
        The angle range corresponding to fov, expressed in degrees
    fov_resolution: list
        the fov resolution, with format [height, width]

    Returns
    -------
    _3d_polar_coord: array
        3D polar coordinates of fov

    """
    try:
        fov_w, fov_h = fov_range[0] * np.pi / 180, fov_range[1] * np.pi / 180
    except:
        fov_w, fov_h = 90 * np.pi / 180, 90 * np.pi / 180

    # calculate the 3d cartesian coordinates
    vp_yaw, vp_pitch, vp_roll = fov_direction
    _3d_cartesian_coord = calcualte_3d_cartesian_coord(fov_w, fov_h, vp_yaw, vp_pitch, vp_roll, fov_resolution)

    # calculate the 3d polar coordinates
    _3d_polar_coord = calculate_3d_polar_coord(_3d_cartesian_coord)

    return _3d_polar_coord


def calcualte_3d_cartesian_coord(fov_w, fov_h, vp_yaw, vp_pitch, vp_roll, fov_resolution):
    """
    Calculate the 3d spherical coordinates of fov

    Parameters
    ----------
    fov_w: float
        width of fov, in radian
    fov_h: float
        height of fov, in radian
    vp_yaw: float
        yaw of viewport, in radian
    vp_pitch: float
        pitch of viewport, in radian
    vp_roll: float
        roll of viewport, in radian
    fov_resolution: list
        the fov resolution, with format [height, width]

    Returns
    -------
    cartesian_coord: array
        spherical cartesian coordinate of the fov
    """

    m = np.linspace(0, fov_resolution[1] - 1, fov_resolution[1])
    n = np.linspace(0, fov_resolution[0] - 1, fov_resolution[0])

    u = (m + 0.5) * 2 * np.tan(fov_w/2) / fov_resolution[1]
    v = (n + 0.5) * 2 * np.tan(fov_h/2) / fov_resolution[0]

    # calculate the corresponding three-dimensional coordinates (x, y, z) mapped from the positive X-axis.
    x = 1.0
    y = u - np.tan(fov_w/2)
    z = -v + np.tan(fov_h/2)

    # coordinate point dimension expansion
    x_scale = np.ones((fov_resolution[0], fov_resolution[1]))
    y_scale = np.tile(y, (fov_resolution[0], 1))
    z_scale = np.tile(z, (fov_resolution[1], 1)).transpose()

    # unit sphere
    x_hat = x_scale / np.sqrt(x_scale * x_scale + y_scale * y_scale + z_scale * z_scale)
    y_hat = y_scale / np.sqrt(x_scale * x_scale + y_scale * y_scale + z_scale * z_scale)
    z_hat = z_scale / np.sqrt(x_scale * x_scale + y_scale * y_scale + z_scale * z_scale)

    # rotation
    a = vp_yaw              # yaw, phi
    b = vp_pitch            # pitch, theta
    r = vp_roll             # roll, psi

    rot_a = np.array([np.cos(a)*np.cos(b), np.cos(a)*np.sin(b)*np.sin(r) - np.sin(a)*np.cos(r), np.cos(a)*np.sin(b)*np.cos(r) + np.sin(a)*np.sin(r)])
    rot_b = np.array([np.sin(a)*np.cos(b), np.sin(a)*np.sin(b)*np.sin(r) + np.cos(a)*np.cos(r), np.sin(a)*np.sin(b)*np.cos(r) - np.cos(a)*np.sin(r)])
    rot_c = np.array([-np.sin(b), np.cos(b)*np.sin(r), np.cos(b)*np.cos(r)])

    xx = rot_a[0] * x_hat + rot_a[1] * y_hat + rot_a[2] * z_hat
    yy = rot_b[0] * x_hat + rot_b[1] * y_hat + rot_b[2] * z_hat
    zz = rot_c[0] * x_hat + rot_c[1] * y_hat + rot_c[2] * z_hat

    xx = np.clip(xx, -1, 1)
    yy = np.clip(yy, -1, 1)
    zz = np.clip(zz, -1, 1)

    cartesian_coord = np.array([xx, yy, zz])

    return cartesian_coord


def calculate_3d_polar_coord(_3d_cartesian_coord):
    """
    Calculate the corresponding 3d polar coordinates

    Parameters
    ----------
    _3d_cartesian_coord: array
         spherical cartesian coordinate
    Returns
    -------
    _3d_polar_coord: array
        spherical polar coordinate, with foramt [phi, theta]

    """

    x, y, z = _3d_cartesian_coord[0], _3d_cartesian_coord[1], _3d_cartesian_coord[2]
    phi = np.arctan2(y, x)                      # range is [-pi, pi]
    r = np.sqrt(x * x + y * y)
    theta = np.arctan2(z, r)                    # range from bottom to top is [-np.pi/2, np.pi/2]

    _3d_polar_coord = np.concatenate([phi, theta], axis=-1)

    return _3d_polar_coord


def transform_projection(dst_projection, src_projection, dst_resolution, src_resolution):
    """
    Conversion between different projection format

    Parameters
    ----------
    dst_projection: str
        destination projection
    src_projection: str
        source projection
    dst_resolution: list
        video resolution of destination projection format, with format [height, width]
    src_resolution: list
        video resolution of source projection format, with format [height, widht]

    Returns
    -------
    pixel_coord: array
        the pixel coordinates in the source projection format corresponding to the target projection format.
    """

    # input -> 3d_polar_coord
    _3d_polar_coord = source_to_3d_polar_coord(dst_projection, dst_resolution)

    # 3d_polar_coord -> pixel_coord
    pixel_coord = _3d_polar_coord_to_pixel_coord(_3d_polar_coord, src_projection, src_resolution)

    return pixel_coord


def source_to_3d_polar_coord(dst_projection, dst_resolution):
    """
    Calculate corresponding 3D polar coordinates based on the input projection type.

    Parameters
    ----------
    dst_projection: str
        destination projection format
    dst_resolution: list
        video resolution of destination projection format, with format [height, width]

    Returns
    -------
    _3d_polar_coord: bytearray
        the calculated 3d polar coordinates
    """

    if dst_projection == "erp":
        _3d_polar_coord = erp_to_3d_polar_coord(dst_resolution)
    elif dst_projection == "cmp":
        _3d_polar_coord = cmp_to_3d_polar_coord(dst_resolution)
    elif dst_projection == "eac":
        _3d_polar_coord = eac_to_3d_polar_coord(dst_resolution)
    else:
        raise Exception(f"the projection {dst_projection} is not supported currently in e3po")

    return _3d_polar_coord


def _3d_polar_coord_to_pixel_coord(_3d_polar_coord, projection_type, src_resolution):
    """
    Given the 3d polar coordinates, convert it to pixel coordinates in the corresponding projection

    Parameters
    ----------
    _3d_polar_coord: array
         spherical polar coordinate, with foramt [phi, theta]
    projection_type: str
        projection format
    src_resolution: list
        source resolution, with format [height, width]

    Returns
    -------
    pixel_coord: array
        the pixel coordinates in the source projection format
    """

    if projection_type == "erp":
        pixel_coord = _3d_polar_coord_to_erp(_3d_polar_coord, src_resolution)
    elif projection_type == "cmp":
        pixel_coord = _3d_polar_coord_to_cmp(_3d_polar_coord, src_resolution)
    elif projection_type == "eac":
        pixel_coord = _3d_polar_coord_to_eac(_3d_polar_coord, src_resolution)
    else:
        raise Exception(f"the projection {projection_type} is not supported currently in e3po")

    return pixel_coord


def erp_to_3d_polar_coord(dst_resolution):
    """
    Obtain spherical polar coordinates from ERP format

    Parameters
    ----------
    dst_resolution: list
        destination resolution, with format [height, width]

    Returns
    -------
    _3d_polar_coord: array
        spherical polar coordinate, with foramt [phi, theta]
    """

    dst_height, dst_width = dst_resolution[0], dst_resolution[1]

    u_tmp = (np.linspace(0.5, dst_width - 0.5, dst_width)) * 2 / dst_width - 1
    v_tmp = (np.linspace(0.5, dst_height - 0.5, dst_height)) * 2 / dst_height - 1

    u = np.tile(u_tmp, (v_tmp.shape[0], 1))
    v = np.tile(v_tmp, (u_tmp.shape[0], 1)).transpose()

    phi = u * (2 * np.pi) / 2
    theta = -v * np.pi / 2

    _3d_polar_coord = np.concatenate([phi, theta], axis=-1)

    return _3d_polar_coord


def cmp_to_3d_polar_coord(dst_resolution):
    """
    Obtain spherical polar coordinates from CMP format

    Parameters
    ----------
    dst_resolution: list
        destination resolution, with format [height, width]

    Returns
    -------
    _3d_polar_coord: array
        spherical polar coordinate, with foramt [phi, theta]
    """

    cmp_height, cmp_width = dst_resolution[0], dst_resolution[1]
    face_size = cmp_height // 2
    assert (face_size * 3 == cmp_width) and (face_size * 2 == cmp_height)

    u = (np.linspace(0.5, cmp_width - 0.5, cmp_width)) * 2 / face_size - 1
    v = (np.linspace(0.5, cmp_height - 0.5, cmp_height)) * 2 / face_size - 1

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

    phi = (np.arctan2(y_temp, x_temp) + np.pi * 2) % (np.pi * 2) - np.pi
    r = np.sqrt(x_temp ** 2 + y_temp ** 2)
    theta = np.arctan2(z_temp, r)

    return np.concatenate([phi, theta], axis=-1)


def eac_to_3d_polar_coord(dst_resolution):
    """
    Obtain spherical polar coordinates from EAC format

    Parameters
    ----------
    dst_resolution: list
        destination resolution, with format [height, width]

    Returns
    -------
    _3d_polar_coord: array
        spherical polar coordinate, with foramt [phi, theta]
    """

    eac_height, eac_width = dst_resolution[0], dst_resolution[1]
    face_size = eac_height // 2
    assert (face_size * 3 == eac_width) and (face_size * 2 == eac_height)

    u = (np.linspace(0.5, eac_width - 0.5, eac_width)) * 2 / face_size - 1
    v = (np.linspace(0.5, eac_height - 0.5, eac_height)) * 2 / face_size - 1

    u = np.tan(u * np.pi / 4)
    v = np.tan(v * np.pi / 4)

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

    phi = (np.arctan2(y_temp, x_temp) + np.pi * 2) % (np.pi * 2) - np.pi
    r = np.sqrt(x_temp ** 2 + y_temp ** 2)
    theta = np.arctan2(z_temp, r)

    return np.concatenate([phi, theta], axis=-1)


def _3d_polar_coord_to_erp(polar_coord, src_resolution):
    """
    Convert polar coordinates to pixel coordinates in ERP format

    Parameters
    ----------
    polar_coord: array
        polar coord, with format [phi, theta]
    src_resolution: list
        source resolution, with format [height, width]

    Returns
    -------
    pixel_coord: array
        the corresponding pixel coordinates in ERP format
    """

    erp_height, erp_width = src_resolution[0], src_resolution[1]

    phi, theta = np.split(polar_coord, 2, axis=-1)
    phi = phi.reshape(phi.shape[:2])
    theta = theta.reshape(theta.shape[:2])

    u = phi / (2 * np.pi) + 0.5
    v = 0.5 - theta / np.pi

    coor_x = u * erp_width - 0.5
    coor_y = v * erp_height - 0.5

    coor_x = np.clip(coor_x, 0, erp_width - 1)
    coor_y = np.clip(coor_y, 0, erp_height - 1)

    pixel_coord = [coor_x, coor_y]

    return pixel_coord


def _3d_polar_coord_to_cmp(polar_coord, src_resolution):
    """
    Convert polar coordinates to pixel coordinates in CMP format

    Parameters
    ----------
    polar_coord: array
        polar coord, with format [phi, theta]
    src_resolution: list
        source resolution, with format [height, width]

    Returns
    -------
    pixel_coord: array
        the corresponding pixel coordinates in CMP format
    """

    cmp_height, cmp_width = src_resolution[0], src_resolution[1]
    u, v = np.split(polar_coord, 2, axis=-1)
    u = u.reshape(u.shape[:2])
    v = v.reshape(v.shape[:2])

    face_size_w = cmp_width // 3
    face_size_h = cmp_height // 2
    assert (face_size_w == face_size_h)  # ensure the ratio of w:h is 3:2

    x_sphere = np.round(np.cos(v) * np.cos(u), 9)
    y_sphere = np.round(np.cos(v) * np.sin(u), 9)
    z_sphere = np.round(np.sin(v), 9)

    dst_h, dst_w = np.shape(u)[:2]
    coor_x = np.zeros((dst_h, dst_w))
    coor_y = np.zeros((dst_h, dst_w))

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
        coor_x[temp_index] = (face_index % 3) * face_size_w + m_cub
        coor_y[temp_index] = (face_index // 3) * face_size_h + n_cub

        coor_x[temp_index] = np.clip(coor_x[temp_index], (face_index % 3) * face_size_w,
                                     (face_index % 3 + 1) * face_size_w - 1)
        coor_y[temp_index] = np.clip(coor_y[temp_index], (face_index // 3) * face_size_h,
                                     (face_index // 3 + 1) * face_size_h - 1)

    pixel_coord = [coor_x, coor_y]

    return pixel_coord


def _3d_polar_coord_to_eac(polar_coord, src_resolution):
    """
    Convert polar coordinates to pixel coordinates in EAC format

    Parameters
    ----------
    polar_coord: array
        polar coord, with format [phi, theta]
    src_resolution: list
        source resolution, with format [height, width]

    Returns
    -------
    pixel_coord: array
        the corresponding pixel coordinates in EAC format
    """

    eac_height, eac_width = src_resolution[0], src_resolution[1]
    u, v = np.split(polar_coord, 2, axis=-1)
    u = u.reshape(u.shape[:2])
    v = v.reshape(v.shape[:2])

    face_size_w = eac_width // 3
    face_size_h = eac_height // 2
    assert (face_size_w == face_size_h)     # ensure the ratio of w:h is 3:2

    x_sphere = np.round(np.cos(v) * np.cos(u), 9)
    y_sphere = np.round(np.cos(v) * np.sin(u), 9)
    z_sphere = np.round(np.sin(v), 9)

    dst_h, dst_w = np.shape(u)[:2]
    coor_x = np.zeros((dst_h, dst_w))
    coor_y = np.zeros((dst_h, dst_w))

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
        coor_x[temp_index] = (face_index % 3) * face_size_w + m_cub
        coor_y[temp_index] = (face_index // 3) * face_size_h + n_cub

        coor_x[temp_index] = np.clip(coor_x[temp_index], (face_index % 3) * face_size_w,
                                     (face_index % 3 + 1) * face_size_w - 1)
        coor_y[temp_index] = np.clip(coor_y[temp_index], (face_index // 3) * face_size_h,
                                     (face_index // 3 + 1) * face_size_h - 1)
    pixel_coord = [coor_x, coor_y]

    return pixel_coord


def pixel_coord_to_tile(pixel_coord, total_tile_num, video_size, chunk_idx):
    """
    Calculate the corresponding tile, for given pixel coordinates

    Parameters
    ----------
    pixel_coord: array
        pixel coordinates
    total_tile_num: int
        total num of tiles for different approach
    video_size: dict
        video size of preprocessed video
    chunk_idx: int
        chunk index

    Returns
    -------
    coord_tile_list: list
        the calculated tile list, for the given pixel coordinates
    """

    coord_tile_list = np.full(pixel_coord[0].shape, 0)
    for i in range(total_tile_num):
        tile_id = f"chunk_{str(chunk_idx).zfill(4)}_tile_{str(i).zfill(3)}"
        if tile_id not in video_size:
            continue
        tile_idx = video_size[tile_id]['user_video_spec']['tile_info']['tile_idx']
        tile_start_width = video_size[tile_id]['user_video_spec']['segment_info']['start_position']['width']
        tile_start_height = video_size[tile_id]['user_video_spec']['segment_info']['start_position']['height']
        tile_width = video_size[tile_id]['user_video_spec']['segment_info']['segment_out_info']['width']
        tile_height = video_size[tile_id]['user_video_spec']['segment_info']['segment_out_info']['height']

        # Create a Boolean mask to check if the coordinates are within the tile range
        mask_width = (tile_start_width <= pixel_coord[0]) & (pixel_coord[0] < tile_start_width + tile_width)
        mask_height = (tile_start_height <= pixel_coord[1]) & (pixel_coord[1] < tile_start_height + tile_height)

        # find coordinates that satisfy both width and height conditions
        hit_coord_mask = mask_width & mask_height

        # update coord_tile_list
        coord_tile_list[hit_coord_mask] = tile_idx

    return coord_tile_list


def pixel_coord_to_relative_tile_coord(pixel_coord, coord_tile_list, video_info, chunk_idx):
    """
    Calculate the relative position of the pixel_coord coordinates on each tile.

    Parameters
    ----------
    pixel_coord: array
        pixel coordinates
    coord_tile_list: list
        calculated tile list
    video_info: dict
    chunk_idx: int
        chunk index

    Returns
    -------
    relative_tile_coord: array
        the relative tile coord for the given pixel coordinates
    """

    relative_tile_coord = copy.deepcopy(pixel_coord)
    unique_tile_list = np.unique(coord_tile_list)
    for i in unique_tile_list:
        tile_id = f"chunk_{str(chunk_idx).zfill(4)}_tile_{str(i).zfill(3)}"
        tile_start_width = video_info[tile_id]['user_video_spec']['segment_info']['start_position']['width']
        tile_start_height = video_info[tile_id]['user_video_spec']['segment_info']['start_position']['height']
        tile_width = video_info[tile_id]['user_video_spec']['segment_info']['segment_out_info']['width']
        tile_height = video_info[tile_id]['user_video_spec']['segment_info']['segment_out_info']['height']

        hit_coord_mask = (coord_tile_list == i)

        # update the relative position
        relative_tile_coord[0][hit_coord_mask] = np.clip(relative_tile_coord[0][hit_coord_mask] - tile_start_width, 0, tile_width - 1)
        relative_tile_coord[1][hit_coord_mask] = np.clip(relative_tile_coord[1][hit_coord_mask] - tile_start_height, 0, tile_height - 1)

    return relative_tile_coord


