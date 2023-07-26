# Configuration

#### Contents

1. [On-demand Solution Configuration](#On-demand Solution Configuration)
1. [Transcoding Solution Configuration](#Transcoding Solution Configuration)

We use yaml files for configuration.

## On-demand Solution Configuration
Taking [E1.yml](../e3po/options/example/E1.yml) as an example:
```yml
#------------------------------------
# The following are general settings
#------------------------------------
# Experiment group name. The processing results of different groups will be stored in their respective folders.
test_group: example
# Name of the method to be tested.
method_name: E1
# The absolute path of this project, automatically obtained at runtime.
project_path: ~
# Use the class name defined in the `data` folder.
data_type: TileBasedData
# Use the class name defined in the `decision` folder.
decision_type: TileBasedDecision
# The projection format of the target video.
# Use the class name defined in the `projection` folder.
projection_type: ErpProjection
# Use the class name defined in the `evaluation` folder.
evaluation_type: TileBasedEvaluation

#-------------------------------
# The following are log settings
#-------------------------------
log:
  # Whether to save log file.
  save_log_file: True
  # Log level of command line output. Defalut: Info
  console_log_level: ~
  # Log level of log file records. Defalut: Debug
  file_log_level: ~

#----------------------------------
# The following are ffmepg settings
#----------------------------------
ffmpeg:
  # Absolute path for ffmpeg executable file.
  # If your ffmpeg has a global path, you do not need to specify the ffmpeg path.
  # If you have different versions of ffmpeg, it is best to specify the absolute path of the ffmpeg you are using.
  ffmpeg_path: /home/bytedance-star/Documents/zt/ffmpeg-6.0/ffmpeg
  # Log level of ffmpeg.
  loglevel: error
  # Number of threads running ffmpeg
  thread: 6

#----------------------------------
# The following are method settings
#----------------------------------
method_settings:
  # Chunk duration. 
  # The following condition needs to be met: (60 mod chunk_duration) == 0. 
  chunk_duration: 1
  # Number of horizontally segmented video tiles.
  tile_width_num: 6
  # Number of vertically segmented video tiles.
  tile_height_num: 6
  # Historical window for predicting motion, in seconds.
  hw_size: 2
  # Prediction window for predicting motion, in chunks.
  pw_size: 1
  # The location of deciding transmission content, affects the value of RTT.
  decision_location: client
  # When making a decision to transmit content, 
  # it is necessary to have an advance time compared to the corresponding content playback time to ensure 
  # that the content to be played can arrive before playback.
  # In milliseconds.
  decision_delay: 66
  # Number of pre-downloaded chunks.
  pre_download_duration: 3
  background:
    # Whether to use background video.
    background_flag: True
    # Alias for projection format of background streaming video.
    projection_mode: erp
    # The projection format of background stream video.
    # Use the class name defined in the `projection` folder.
    projection_type: ErpProjection
    # The 'vf' filter parameter corresponding to generating background stream video using ffmpeg.
    # For details, see: https://ffmpeg.org/ffmpeg-all.html#v360.
    ffmpeg_vf_parameter: e
    # Background stream video pixel width.
    width: 1920
    # Background stream video pixel height.
    height: 1080

#---------------------------------
# The following are video settings
#---------------------------------
video:
  # Video duration, in seconds.
  video_duration: 10
  # Video frame rate per second.
  video_fps: 30
  # Rendering delay of each frame, in seconds.
  rendering_delay: 10
  origin:
    # The relative path of the original video compared to './source/video'.
    video_dir: ~
    # Original video full name.
    video_name: sample.mp4
    # Alias for projection format of original video.
    projection_mode: erp
    # The projection format of original video.
    # Use the class name defined in the `projection` folder.
    projection_type: ErpProjection
    # The 'vf' filter parameter corresponding to generating other video using ffmpeg.
    # For details, see: https://ffmpeg.org/ffmpeg-all.html#v360.
    ffmpeg_vf_parameter: e
    # Original video pixel width.
    height: 3840
    # Original video pixel height.
    width: 7680
  converted:
    # Quality list of target videos, in QP.
    quality_list: [29]
    # Alias for projection format of target video. 
    projection_mode: erp
    # The 'vf' filter parameter corresponding to generating target video using ffmpeg.
    # For details, see: https://ffmpeg.org/ffmpeg-all.html#v360.
    ffmpeg_vf_parameter: e
    # Target video pixel width.
    height: 3840
    # Target video pixel height.
    width: 7680

#----------------------------------------
# The following are motion trace settings
#----------------------------------------
motion_trace:
  # Full name of motion trace log file.
  motion_file: motion_trace.log
  # Raw  motion trace log file sampling frequency, in Hz.
  sample_frequency: 10
  # The motion frequency after frame filling, in Hz
  motion_frequency: 100 #
  # Which line of data in the file is used, except for the header
  column_idx: 20

#-----------------------------------------
# The following are network trace settings
#-----------------------------------------
network_trace:
  # Round-Trip Time, in milliseconds.
  rtt: 30
  # Bandwidth, MBps.
  bandwidth: 100

#----------------------------------
# The following are metric settings
#----------------------------------
metric:
  # FoV range, angular system.
  range_fov: [89, 89]
  # Resolution of FoV, h*w.
  fov_resolution: [1920, 1832]
  # Sampling frequency when calculating the boundary ratio.
  sampling_size: [50, 50]
  # Whether to calculate psnr. When (psnr_flag || ssim_flag) == True, the FoV video will be created and saved.
  psnr_flag: True
  # Whether to calculate ssim. When (psnr_flag || ssim_flag) == True, the FoV video will be created and saved.
  ssim_flag: True
  # The frequency for evaluating psnr and ssim.
  # The following condition needs to be met: (video_fps mod psnr_ssim_frequency) == 0
  # In Hz.
  psnr_ssim_frequency: 1
  # Whether to GPU to accelerate the calculation of psnr and ssim.
  # Please set False when GPU acceleration is not possible, otherwise it will slow down the running speed.
  use_gpu: True
  # Whether to save ground truth images.
  save_ground_truth_flag: True
  # Whether to save result FoV images.
  save_result_img_flag: True
  # Interpolation mode.
  inter_mode: bilinear
```


## Transcoding Solution Configuration
Taking [F1.yml](../e3po/options/example/F1.yml) as an example:
```yml
#-----------------------------------
# The following are general settings
#-----------------------------------
# Experiment group name. The processing results of different groups will be stored in their respective folders.
test_group: example
# Name of the method to be tested.
method_name: F1
# The absolute path of this project, automatically obtained at runtime.
project_path: ~
# Use the class name defined in the `data` folder.
data_type: Freedom1Data
# Use the class name defined in the `decision` folder.
decision_type: ~
# The projection format of the target video.
# Use the class name defined in the `projection` folder.
projection_type: Freedom1Projection # converted的投影格式
# Use the class name defined in the `evaluation` folder.
evaluation_type: Freedom1Evaluation

#-------------------------------
# The following are log settings
#-------------------------------
log:
  # Whether to save log file.
  save_log_file: True
  # Log level of command line output. Defalut: Info
  console_log_level: ~
  # Log level of log file records. Defalut: Debug
  file_log_level: ~

#----------------------------------
# The following are ffmepg settings
#----------------------------------
ffmpeg:
  # Absolute path for ffmpeg executable file.
  # If your ffmpeg has a global path, you do not need to specify the ffmpeg path.
  # If you have different versions of ffmpeg, it is best to specify the absolute path of the ffmpeg you are using.
  ffmpeg_path: /home/bytedance-star/Documents/zt/ffmpeg-6.0/ffmpeg
  # Log level of ffmpeg.
  loglevel: error
  # Number of threads running ffmpeg
  thread: 6

#----------------------------------
# The following are method settings
#----------------------------------
method_settings:
  # The location of deciding transmission content, affects the value of RTT.
  decision_location: server
  # When making a decision to transmit content, 
  # it is necessary to have an advance time compared to the corresponding content playback time to ensure 
  # that the content to be played can arrive before playback.
  # In milliseconds.
  decision_delay: 266
  # Number of pre-downloaded chunks.
  pre_download_duration: 3
  # Set to 1 when there is no need to split tiles
  tile_width_num: 1
  # Set to 1 when there is no need to split tiles
  tile_height_num: 1  
  # Unique parameters of Freedom.
  vam_size: [1680, 1120]
  # Unique parameters of Freedom.
  crop_factor: ['7 / 32', '7 / 24']
  # Unique parameters of Freedom.
  scale_factors: {1: '1', 1.5: '21 / 40', 2: '1 / 2', 3: '7 / 16', 4: '7 / 18', 5: '7 / 20', 6: '7 / 24', 7: '7 / 32'}
  background:
    # Whether to use background video.
    background_flag: False

#---------------------------------
# The following are video settings
#---------------------------------
video:
  # Video duration, in seconds.
  video_duration: 10
  # Video frame rate per second.
  video_fps: 30
  # Rendering delay of each frame, in seconds.
  rendering_delay: 10
  origin:
    # The relative path of the original video compared to './source/video'.
    video_dir: ~
    # Original video full name.
    video_name: sample.mp4
    # Alias for projection format of original video.
    projection_mode: erp
    # The projection format of original video.
    # Use the class name defined in the `projection` folder.
    projection_type: ErpProjection
    # The 'vf' filter parameter corresponding to generating other video using ffmpeg.
    # For details, see: https://ffmpeg.org/ffmpeg-all.html#v360.
    ffmpeg_vf_parameter: e
    # Original video pixel width.
    height: 3840
    # Original video pixel height.
    width: 7680
  converted:
    # Quality list of target videos, in QP.
    quality_list: [29]
    # Alias for projection format of target video. 
    projection_mode: erp
    # The 'vf' filter parameter corresponding to generating target video using ffmpeg.
    # For details, see: https://ffmpeg.org/ffmpeg-all.html#v360.
    ffmpeg_vf_parameter: e
    # Target video pixel width.
    height: 3840
    # Target video pixel height.
    width: 7680

#----------------------------------------
# The following are motion trace settings
#----------------------------------------
motion_trace:
  # Full name of motion trace log file.
  motion_file: motion_trace.log
  # Raw  motion trace log file sampling frequency, in Hz.
  sample_frequency: 10
  # The motion frequency after frame filling, in Hz
  motion_frequency: 100 #
  # Which line of data in the file is used, except for the header
  column_idx: 20

#-----------------------------------------
# The following are network trace settings
#-----------------------------------------
network_trace:
  # Round-Trip Time, in milliseconds.
  rtt: 30
  # Bandwidth, MBps.
  bandwidth: 100

metric:
  # FoV range, angular system.
  range_fov: [89, 89]
  # Resolution of FoV, h*w.
  fov_resolution: [1920, 1832]
  # Sampling frequency when calculating the boundary ratio.
  sampling_size: [50, 50]
  # Whether to calculate psnr. When (psnr_flag || ssim_flag) == True, the FoV video will be created and saved.
  psnr_flag: True
  # Whether to calculate ssim. When (psnr_flag || ssim_flag) == True, the FoV video will be created and saved.
  ssim_flag: True
  # The frequency for evaluating psnr and ssim.
  # The following condition needs to be met: (video_fps mod psnr_ssim_frequency) == 0
  # In Hz.
  psnr_ssim_frequency: 1
  # Whether to GPU to accelerate the calculation of psnr and ssim.
  # Please set False when GPU acceleration is not possible, otherwise it will slow down the running speed.
  use_gpu: True
  # Whether to save ground truth images.
  save_ground_truth_flag: True
  # Whether to save result FoV images.
  save_result_img_flag: True
  # Interpolation mode.
  inter_mode: bilinear
```