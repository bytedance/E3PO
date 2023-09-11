# E3PO Basic Tutorial

## Prerequisites (p: Python package, b: Binary)
- (b) ffmpeg
- (b) cuda
- Python 3.8
- (p) numpy
- (p) Pytorch
- (p) cv2
- (p) tqdm

## Dataset Preparation
### Download data
1. Video data<br>
Download video, and place like:
```
|---e3po
    |---source
        |---video
            |---[video file]
```
2. Motion trace data<br>
Download motion trace log, and place like:
```
|---e3po
    |---source
        |---motion_trace
            |---[motion trace file]
```

### Modify the configuration yaml file
The specific meaning of parameters can be found in [Config.md](./Config.md). For all methods, you should specify the path to the local ffmpeg. If your ffmpeg has a global path, you do not need to specify the ffmpeg path, otherwise you need to specify the absolute path of the ffmpeg. If you have different versions of ffmpeg, it is best to specify the absolute path of the ffmpeg you are using:
```
# The specific meaning of parameters can be found in docs/Config.md.
ffmpeg:
  ffmpeg_path: ~
```

Taking the ERP solution as an example, if you use your own video, you need to modify the following parameters in [erp.yml](../e3po/approaches/erp/erp.yml):
```
# The specific meaning of parameters can be found in docs/Config.md.
video:
  video_duration: 10
  video_fps: 30
  origin:
    video_dir: ~
    video_name: video_1.mp4
    projection_mode: erp
    projection_type: ErpProjection
    ffmpeg_vf_parameter: e # For details, see: https://ffmpeg.org/ffmpeg-all.html#v360.
    height: 3840
    width: 7680
```
There are still some parameters that should be specified before running [make_preprocessing.py](../e3po/make_preprocessing.py). However, as the first example, you can choose to keep them as default:
```
# The specific meaning of parameters can be found in docs/Config.md.
test_group: group_1
method_name: erp
data_type: OnDemandData
projection_type: ErpProjection
evaluation_type: OnDemandEvaluation
method_settings:
  chunk_duration: 1 # The following condition needs to be met: (60 mod chunk_duration) == 0. 
  tile_width_num: 6
  tile_height_num: 6
  background:
    background_flag: True
    projection_mode: erp
    projection_type: ErpProjection
    ffmpeg_vf_parameter: e # For details, see: https://ffmpeg.org/ffmpeg-all.html#v360.
    width: 1920
    height: 1080
video:
  converted:
    quality_list: [29] # QP value
    projection_mode: erp
    ffmpeg_vf_parameter: e # For details, see: https://ffmpeg.org/ffmpeg-all.html#v360.
    height: 3840
    width: 7680
log:
  save_log_file: True
  console_log_level: ~
  file_log_level: ~
ffmpeg:
  loglevel: error
  thread: 6
```


## Make Preprocessing
### Run the script [make_preprocessing.py](../e3po/make_preprocessing.py)
Taking the ERP solution as an example:
```
python ./e3po/make_preprocessing.py -opt approaches/erp/erp.yml
```
Then you'll see result in:
```
|---e3po
    |---source
        |---video
            |---[group_1]
                |---[video_1]
                    |---[erp]
                        |---video_size.json
                        |---converted_[quality].mp4
    |---log
        |---[group_1]
            |---[video_1]
                |---[erp]
                    |---erp_prepare_data.log  
```

## Make Decision
The decision-making of the transcoding scheme will be completed during the data preparation phase.The following process is for the on demand solution.
### Modify the configuration yaml file
Taking the ERP solution as an example, and keep the previous parameters unchanged. The parameters you can modify in this step are as follows. 
Except for the user log file that must indicate the file you are using, you can choose to keep the other parameters as default：
```
# The specific meaning of parameters can be found in docs/Config.md.
decision_type: OnDemandDecision
method_settings:
  hw_size: 2 # in seconds.
  pw_size: 1 # in chunks.
  decision_location: client
  decision_delay: 66
  pre_download_duration: 3 # in chunks.
motion_trace:
  motion_file: source/motion_trace/motion_trace.log # Your motion trace file path.
  sample_frequency: 10
  motion_frequency: 100
  column_idx: 20
network_trace:
  rtt: 30
```

### Run the script [make_decision.py](../e3po/make_decision.py)
```
python ./e3po/make_decision.py -opt options/example/E1.yml
```
Then you'll see results in:
```
|---e3po
    |---result
        |---[test group name]
            |---[method name]
                |---decision.json
    |---log
        |---[test group name]
            |---[method name]_make_decision.log
```

## Evaluation
### Modify the configuration yaml file
Taking the ERP solution as an example,  keep the previous parameters unchanged. The parameters you can modify in this step are as follows. 

* You need to pay attention to whether you have installed the GPU version of Pytorch. If GPU acceleration is not available, you need to set `use_gpu` to `False`. 
* In addition, you also need to decide whether to save the resulting image. If each image is saved, there will be a certain storage cost, and the corresponding parameter is `save_result_img_flag`. `save_ground_truth_flag` suggests setting it to `True` because for the same set of tests, ground truth images are often the same, and saving them can reduce the evaluation time.
* You can choose to keep the default for other parameters:
```
# The specific meaning of parameters can be found in docs/Config.md.
evaluation_type: TileBasedEvaluation
video:
  rendering_delay: 10
network_trace:
  bandwidth: 100 # MBps
metric:
  range_fov: [89, 89]
  fov_resolution: [1920, 1832] # h*w
  sampling_size: [50, 50]
  psnr_flag: True
  ssim_flag: True
  psnr_ssim_frequency: 1 # The following condition needs to be met: (video_fps mod psnr_ssim_frequency) == 0
  use_gpu: False # Please set False when GPU acceleration is not possible, otherwise it will slow down the running speed.
  save_ground_truth_flag: True
  save_result_img_flag: True
  inter_mode: bilinear
```

### Run the script [make_evaluation.py](../e3po/make_evaluation.py)
```
python ./e3po/make_evaluation.py -opt approaches/erp/erp.yml
```
Then you'll see result in:
```
|---e3po
    |---result
        |---[group_1]
            |--[video_1]
              |---[erp]
                  |---evaluation.json
                  |---frames
                      |---xxx.png
                      |---output.mp4
    |---log
        |---[group_1]
            |--[video_1]
                |---erp_evaluation.log
```
## Customize methods
See tutorial in [CustomScheme.md](./CustomScheme.md).