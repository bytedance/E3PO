# Overview
E3PO is a platform to simulate and evaluate user-implemented 360 video streaming solutions. This project comprises three parts: 

**E3PO framework (e3po/):** The framework provides basic functions to load 360 video, head motion trace, and user-implemented code, run simulations, and evaluate simulation performance. In general, the overall framework comprises three modules: video pre-processing, streaming simulation, and performance evaluation. The video pre-processing module defines the procedure to apply customized methods to convert the original 360 video into various video tiles. The generated video tiles are stored in the file system and the metadata information of each video tile, including tile size, are stored in a json file for further use. The streaming simulation simulates the system downloading behaviors when a user watches the video. It feeds the user's head motion data to user's logic and lets user's simulation decide at what time to request the downloading of which video tile. All the video tile downloading requests are stored in a json file as well. In the performance evaluation module, it uses the pre-generated video tiles and the json files containing video tile information and downloading actions to measure the overall streaming bandwidth consumed. It can also apply user logic to render the result images that will be displayed in user's VR headset. As a result, E3PO can measure the result video quality of a specific user simulation and even compare side by side different simulations. 

![](/docs/Framework.jpg "e3po_framework")

**Example Simulations (e3po/approach):** E3PO has provided several simulation implementations as examples to demonstrate how to use the system to implement various 360 streaming ideas.

**Utility Functions (e3po/utils):** We have also provided some utility functions for user's convenience in implementing their own 360 streaming solutions. Such functions include converting the 360 video into a different projection, segmenting a video clip into small tiles, and more. 



# Terminology
**360 Video:** The 360-degree panoramic video, also called VR video or omni-directional video in certain scenarios,  is usually captured by a 360-degree camera. The goal of E3PO is to optimize the streaming solutions for such videos. In our system, 360 video is used as the source to feed various customized streaming solutions. In our current system, a 360 video has an 8K resolution (7680x3840) and uses equi-rectangular projection. However, E3PO can be updated to support more resolutions and projections. 

**On-demand Mode:** E3PO supports the simulation of two modes, on-demand and transcoding. On-demand mode means the 360 video is pre-processed into small tiles and stored on the server. When streaming starts, the client analyzes the current and historical viewpoint information, and sends requests to download the video tiles needed. 

**Transcoding Mode:** This is another mode that E3PO supports. In this mode, the server does not pre-process 360 video. Instead, the server processes and transcodes the 360 video into a single video stream and sends it to the client during the run-time. The client needs to update server how to transcode the 360 video based on viewpoint information. 

**Chunk:** 360 video is temporarily divided into smaller chunks for on-demand pre-processing (tile generation). The default value of the configurable chunk duration is 2 seconds. All video tiles generated in the on-demand mode shall have the same chunk duration, except the last chunk of the video may have a shorter duration. A chunk is also the basic unit for video tile encoding. Each chunk contains one or more entire GOP, which means each video tile should start with an I-frame. It is important to point out that for the transcoding mode, 360 video is processed and transcoded at frame level and thus the concept of "chunk" in transcoding mode refers to just a single video frame. 

**Tile:** In the on-demand mode, each 360 video chunk is passed to user's simulation logic to generate one or more tiles. The term "tile" is originally used when the 360 video is spatially segmented into multiple non-overlapping pieces. In our system, we expand the term to refer to any user generated video chunks. For example, tile generation techniques may include resizing, changing projection, pixels re-organization, overlapping segmentation, and more. In transcoding mode, we also use "tile" to refer to the transcoding result frame. 

**Motion Trace:** The trace contains the head movement data collected from the real users' VR headset. Each motion trace sample contains {ts, pitch, yaw, roll}. ts is the timestamp for sample collection and ts=0 is aligned with the playback of the first video frame.  Pitch ranges from [$-\pi/2， \pi/2$] and yaw ranges from [$0， 2\pi$] (roll is not currently used in our dataset and you may assume roll=0). Pitch=0 and yaw=0 means the viewer is currently looking at the center of the 360 video. 


# Design a new 360 video streaming solution
E3PO aims to simplify the procedure of implementing a new 360 video streaming design and compare the performance of different solutions. In order to use E3PO to implement a 360 video streaming solution, you only need to complete a python module and **implement FIVE interfaces**. In this section, we will introduce the E3PO work flow in details and highlight the APIs that users need to implement.

## Video Preprocessing – On Demand
The preprocessing module has different logics for on-demand and transcoding mode. In the on-demand mode, the original 360 video is divided into chunks and then passed to the user logic to generate one or multiple video tiles. Each video tile is subsequently encoded and stored in the file system. The size of the encoded tile video as long as any user generated meta data is stored in the video.json file for future use in the streaming simulation. The following pseudo-code describes the flow:
```python
user_data = None
user_data = video_analysis(user_data, video_info)

for chunk_idx in range[...]:
    source_video_uri = generate_source_video(source_video, chunk_idx)
    chunk_info = update_chunk_info(chunk_idx)
    dst_video_folder = ‘/path/to/temp/folder/of/output/frames’
    tile_idx = 0
    while True:
        user_video_spec, user_data = preprocess_video(source_video_uri, dst_video_folder, chunk_info, user_data)
        if user_video_spec is null:
            break
        dst_video_uri = generate_dst_video_uri(chunk_info, tile_idx)
        encode_dst_video(dst_video_uri, dst_video_folder, encoding_params)
        dst_video_size = get_video_size(dst_video_uri)
        remove_temp_files (dst_video_folder)
        write_video_json(tile_idx, dst_video_uri, dst_video_size, chunk_info, user_video_spec)
        tile_idx = tile_idx + 1
```

### video_analysis(user_data, video_info)
This API allows users to analyze the full 360 video (if necessary) before the pre-processing starts. This is also the only chance that the user gets access to the entire 360 video. Users can store the analysis results in ```user_data``` for future use in pre-processing. 

**user_data:** is initially **set to an empy object**  and users can change it to any structure they need. The framework guarantees passing the same user_data to all subsequent preprocess functions. 

**video_info:** is a dictionary containing the following information:

|Parameter | Description |
|--------- | ----------- |
|"width" | width of video resolution|
|"height" | height of video resolution|
|"projection" | the projection used for the 360 video. In most cases, it is "equirectangular"|
|"duration" | the length of video in seconds |
|"fps" | the video frame rate |
|"uri" | the uri of the video where the user can read from the file system. |

**RETURN VALUE:** user should return the modified (or unmodified) ```user_data``` as the return value. Failing to do so will result in the loss of the information stored in the ```user_data``` object. 

### preprocess_video(source_video_uri, dst_video_folder, chunk_info, user_data)
This API allows the user to implement customized functions to process video chunks and generate their own video tiles. The original 360 video is first divided into N chunks. Each chunk is passed to this API one or multiple times depending on user's actions. The user should process all necessary functions, including but not limited to re-projection, segmentation, resize to generate different video tiles. It is important to remember, even though the source video is provided in the form of a video, the user should generate and store each tile video frame as PNG format in the dst_video_folder. The video frame files should be named 000.png, 001.png so that they can be encoded with ffmpeg. The reason we process this way is that we can apply the same encoding parameters for all streaming solutions. 

**source_video_uri:** a string variable that indicates where the source video is on the file system. 

**dst_video_folder:** a string variable suggests where the user should store all the generated tile video frames. 

**chunk_info:** is a dictionary containing the following information:

|Parameter | Description |
|--------- | ----------- |
|"chunk_idx" | the index of this video chunk |
|"chunk_duration" | the duration of a chunk in seconds |
|"start_second" | the start second of the chunk |
|"end_second" | the end second of the chunk |

**user_data:** the variable is reserved to pass information between API calls. Users can insert or modify any customized information in the object. E3PO guarantees the same variable is passed to ```video_analysis()``` and all ```preprocess_video()``` calls. 


**RETURN VALUE:** There are **TWO** objects to return. The first object is  a JSON object that contains the metadata information for the generated video tile. This JSON will be saved with the generated video tiles together and passed to the future decision and evaluation stage. You can simply return an empty JSON object ```{""}``` if you don't want to pass anything, but we strongly recommend you at least give the tile you generate an index number. It is important to know that this JSON object is the only method you can pass information to other modules (i.e., streaming simulation, and performance evalution). If you have completed generating tiles for this video chunk, you need to return the ```NULL``` object so that the framework will move to the next chunk video. The second object is the ```user_data``` that you may have modified in the function. Failing to do so will result in the loss of the information stored in the ```user_data``` object. 

## Video Preprocessing – Transcoding
In the transcoding mode, the video tile is generated at run-time when user starts the streaming. But for convenience, in E3PO, we reuse the video preprocessing module to simulate the generation of video tiles that are transcoded in real-time. The pseudo-code of the module is as follows
```python
user_data = None
user_data = video_analysis(user_data, video_info)

motion_history = []
motion_history = update_motion(0, 0, motion_history)
last_frame_idx = -1
pre_downloading_duration = RTT

for curr_ts in range [0, pre_downloading_duration]
    curr_frame_idx = get_curr_video_frame_index(video_info, curr_ts)
    if curr_frame_idx == last_frame_idx:
        continue       
    curr_video_frame = get_curr_video_frame(video_info, curr_frame_idx)
    last_frame_idx = curr_frame_idx
    dst_video_frame, user_video_spec = transcode_video(curr_video_frame, curr_frame_idx, network_stats, motion_history, user_data)
    dst_video_frame_uri = generate_dst_frame_uri(curr_frame_idx)
    save_video_frame(dst_video_frame_uri, dst_video_frame)
    frame_info = update_chunk_info(curr_frame_idx)
    write_video_json(curr_frame_idx, dst_video_frame_uri, 0, frame_info, user_video_spec)

for motion_ts in range[...]:
    motion_history = update_motion(motion_ts, motion_ts, motion_history)
    curr_frame_idx = get_curr_video_frame_index(video_info, motion_ts + pre_downloading_duration)
    if curr_frame_idx == last_frame_idx:
        continue       
    curr_video_frame = get_curr_video_frame(video_info, curr_frame_idx)
    last_frame_idx = curr_frame_idx
    dst_video_frame, user_video_spec = transcode_video(curr_video_frame, curr_frame_idx, network_stats, motion_history, user_data)
    dst_video_frame_uri = generate_dst_frame_uri(curr_frame_idx)
    save_video_frame(dst_video_frame_uri, dst_video_frame)
    frame_info = update_chunk_info(curr_frame_idx)
    write_video_json(curr_frame_idx, dst_video_frame_uri, 0, frame_info, user_video_spec)
    
dst_video_uri = generate_dst_video_uri(chunk_info, tile_idx)
encode_dst_video(dst_video_uri, dst_video_folder, encoding_params)
dst_video_sizes = get_video_frame_sizes(dst_video_uri)
update_video_sizes(dst_video_sizes)
```
The process gets more complicated compared to the on demand mode because the user motion data and time sequence get involved as well. We will explain more about the time sequence of E3PO in the following sections and the important takeaway here is that: each video frame of the original 360 video is passed to the user logic to generate only one tile. 


### video_analysis(user_data, video_info)
This is the same API as the one used in the on-demand mode. It allows the user to analyze the 360 video before streaming and transcoding starts. Please refer to the previous explanation of parameters and return values.

### transcode_video(curr_video_frame, curr_frame_idx, network_stats, motion_history, user_data)
This API allows the user to implement customized functions to process the 360 video frame and generate the transcoded tile. The user is provided with the original 360 video frame object that stores all pixels, and output the tile frame in the same format. 

**curr_video_frame:** the object (cv2 image type) that saves the video frame of the 360 video that is being transcoded at this moment.

**curr_frame_idx:** the integer marks the index of the video frame that is currently being transcoded. 

**network_stats:** a list of network information structures, each of which is a dictionary with the following information:

|Parameter | Description |
|--------- | ----------- |
|"ts" | the timestamp at which the network condition is measured. |
|"rtt" | rtt between client and server |
|"bw" | estimated bandwidth between client and server |

In the current version, the ```network_stats``` always contains one element, where ```rtt``` and ```bw``` remain unchanged. 

**motion_history:** a list of head motion records, each of which is a dictionary with the following information: 

|Parameter | Description |
|--------- | ----------- |
|"ts" | the timestamp at which the motion is measured. Note it should correspond to the curr_ts in the framework, rather than the motion_ts in the dataset. 
|"pitch" | ranges from [$-\pi/2， \pi/2$] |
|"yaw" | ranges from [$0， 2\pi$]
|"roll" |  ranges from [$-\pi/2， \pi/2$] but you can treat it as 0 in the current version |

Note that users can find the curr_ts by reading the latest record motion_history[-1]["ts"]. 

**user_data:** the variable is reserved to pass information between API calls. Users can insert or modify any customized information in the object. E3PO guarantees the same variable is passed to ```video_analyze()``` and all ```transcode_video()``` calls. 

**RETURN VALUE:** the function should return **THREE** objects. The first is the video tile that is generated, and it should be a cv2 image type as well. The second object is the user json for the generated tile. This user json is the place to store any metadata for this tile frame if needed. It is also the only method to pass any information to subsequent modules. The last object is the ```user_data``` that you may have modified in the function. Failing to do so will result in the loss of the information stored in the ```user_data``` object. 

## Streaming Decision - On Demand
Similarly, the streaming decision module has different logics for on-demand and transcoding mode. For the on_demand mode, based on the ```video.json``` generated by the preprocessing module, user makes decision on which video tiles should be downloaded according to the head movements and network status available at the moment. Each time there is a new decision result, it will be saved along with the current timestamp in the ```decision.json``` file.

The following pseudo-code describes the flow:
```python
curr_ts = 0
motion_history = []
user_data = None
dl_list, user_data = download_decision(network_stats, motion_history, video_json, user_data)
write_decision_json(curr_ts, dl_list)

for motion_ts in range[...]:
    curr_ts = motion_ts + pre_downloading_duration
    motion_history = update_motion(motion_ts, curr_ts, motion_history)
    dl_list, user_data = download_decision(network_stats, motion_history, video_json, user_data)
    write_decision_json(curr_ts, dl_list)
```

### download_decision(network_stats, motion_history, video_json, user_data)
The user needs to implement this API to simulate the action of the streaming system: at what time should the client request which video tile from the server. The user should assume this function to be executed on the VR device, which means it can immediately detect the head motion but it takes at least an RTT to receive the requested video tile. Thus, the user should add customized motion prediction logic to the function. 

**network_stats:** a list of network information structures, each of which is a dictionary with the following information:

|Parameter | Description |
|--------- | ----------- |
|"ts" | the timestamp at which the network condition is measured. |
|"rtt" | rtt between client and server |
|"bw" | estimated bandwidth between client and server |

In the current version, the ```network_stats``` always contains one element, where ```rtt``` and ```bw``` remain unchanged. 


**motion_history:** a list of head motion records, each of which is a dictionary with the following information: 

|Parameter | Description |
|--------- | ----------- |
|"ts" | the timestamp at which the motion is measured. Note it should correspond to the curr_ts in the framework, rather than the motion_ts in the dataset. 
|"pitch" | ranges from [$-\pi/2， \pi/2$] |
|"yaw" | ranges from [$0， 2\pi$]
|"roll" |  ranges from [$-\pi/2， \pi/2$] but you can treat it as 0 in the current version |

Note that users can find the curr_ts by reading the latest record motion_history[-1]["ts"]. 

**video_json:** is the whole ```video_json``` file. 

**user_data:** reserve for users to add customized variables or data. The same variable is guaranteed to pass to every decision function. 

**RETURN VALUE:** There are **TWO** return values. The first if a list of tile indexes that the user request to download at this moment. For example, at this time, the user decides to request tile #1 and #2. Then the return value should be ```[1, 2]```. If no tile is needed, an empty list should be returned. It is important to remember that the user should keep a list of what tiles have been requested, for example using ```user_data``` structure. Otherwise, the simulator does not have any other method for the user to query the history download list. The second
object is the ```user_data``` that you may have modified in the function. Failing to do so will result in the loss of the information stored in the ```user_data``` object.

## Streaming Decision - Transcode
The transcode mode of streaming decision requires no user action. The transcoded tile has already been generated in the video preprocessing module and thus will be simply streamed to the user accordingly. 

The following pseudo-code describes the flow :
```python
last_frame_idx = -1
for curr_ts in range[video_info.duration]:
    curr_frame_idx = get_curr_video_frame_index(video_info, curr_ts)
    if curr_frame_idx == last_frame_idx:
        continue
    write_decision_json(curr_ts, [curr_frame_idx])
    last_frame_idx = curr_frame_idx
```

## Performance Evaluation
Both on-demand and transcoding modes share the same performance evaluation module. According to the video tile size information stored in ```video.json``` and the streaming requests recorded in ```decision.json```, E3PO can calculate the arrival time of each video tile. According to the ```motion_history```, it is simple to calculate the actual FOV at any given time. Thus, the user needs to provide the logic to render the display image for the specific FOV providing the available video tiles. E3PO is also responsible measuring all related visual and QoS metrics. The following pseudo code describes the flow:
```python
user_data = None
dl_list = read_decision_json()
video_json = read_video_json()
arrival_list = calc_arrival_ts(dl_list, network_stats)
last_display_frame_pts = -1

if is_transcode_mode() == false:
    pre_downloading_duration = options.pre_download_duration
else:
    pre_downloading_duration = arrival_list[0].ts

for motion_ts in range[...]:
    curr_ts = motion_ts + pre_downloading_duration
    current_display_chunks = get_curr_display_chunks(arrival_list, curr_ts, video_json)
    curr_display_frame_pts = get_curr_display_frame_pts(current_display_chunks, motion_ts)
    if curr_display_frame_pts == last_display_frame_pts:
        continue
        
    curr_display_frames = get_curr_display_frames(current_display_chunks, curr_display_frame_pts)
    last_display_frame_pts = curr_display_frame_pts
    
    curr_motion = update_current_motion(motion_ts)
    curr_fov = get_curr_fov(curr_motion)
    
    dst_video_frame_uri = generate_dst_frame_uri(motion_ts)

    user_data = generate_display_result(curr_display_frames, current_display_chunks, curr_fov, dst_video_frame_uri, user_data)
    
    generate_benchmark_result(source_video_uri, curr_fov, dst_benchmark_frame)
    calc_psnr_ssim(dst_benchmark_frame, dst_video_frame_uri)
    
encode_display_video()
```
### generate_display_result(curr_display_frames, current_display_chunks, curr_fov, dst_video_frame_uri, user_data) 
In this API, user is required to implement the logic of generating the display image for a specific FOV (```curr_fov```). That is, based on the currently available tile video frames, user should generate a image that will finally be presented on the display screen. The user is provided with a list of currently available video tile frame objects, each storing all the pixels, and output the display results. It is important to point out here that the user should store the display image as a file using the provided file name and location. The user should store the image in PNG format (the provided file name will also have a PNG extension) to avoid quality loss. 


**curr_display_frames:** a list of video tile frame objects (cv2 image type)are provided. The user can only use these video tile frames to generate the display image. The frames in the list has the same order of the ```curr_display_chunks```. 

**curr_display_chunks:** a list of video tile metadata JSON objects. Each JSON object contains all the inforamtion stored in the ```video.json```, which also includes the ```user_video_spec``` at tile generation. The list has the same order of ```curr_display_frame```. For example, the first element of ```curr_display_frame``` stores all the pixels and the first element of ```curr_display_chunks``` contains all the metadata of this specific frame.  

**curr_fov:** a dictionary including the current viewpoint for display rendering. 

| Parameter | Description |
| ------------- | ------------- |
| "curr_motion" | current motion which equals to the center of rendering viewpoint, with format of ```{yaw, pitch, roll}``` |
| "range_fov" | degree range of fov, with format of ```[vertical, horizontal]``` |
| "fov_resolution" | resolution of fov in pixel number, with format of ```[height, width]``` |

**dst_video_frame_uri:** uri for the generated display image to store on the file system. You can assume the file name has PNG as extension. 

**user_data:** reserve for users to add customized variables or data. The framework guarantees passing the same ```user_data``` to all subsequent ```generate_display_result()``` functions.

**RETURN VALUE:** user should return the object ```user_data``` that you may have modified in the function. Failing to do so will result in the loss of the information stored in the ```user_data``` object.

## Time Sequence and Clock Simulation
You may have noticed an important issue in E3PO design, which is how time is simulated in E3PO. There are many time related concepts: the PTS for each video frame, the timestamp for each motion data sample, the transmission time that each video tile needs to be streamed over networks, the network round trip time between server and client, and the moment at which the client sends video tile streaming requests. In order to make the simulation as valid as possible, E3PO needs to appropriately address all these components. 

There are several basic rules of E3PO clock simulation: 
1. A system clock is provided as a reference. 
2. All streaming actions, including sending requests for video tiles and receiving video tiles, are all timed using the timestamp (ts) of the system clock. 
3. The start of video playback is also timed using the timestamp (ts) of the system clock. Assuming the video playback starts at $\Delta$ (illustrated in the figure below), a video frame with $pts$ is actually displayed at time $\Delta + pts$ according to the system clock. 

<div align=center>
    <img src=./clock.jpg width=450 height= />
</div>

E3PO always starts the video playback at time $\Delta$, or ```pre_download_duration``` as the pseudo-code suggests. For the on-demand mode, $\Delta$ is set to a few hundred milliseconds, allowing users to download some video tiles within this duration before the start of playback. But keep in mind, the video playback does not wait for all requested tiles to arrive. Thus it is important to manage a reasonable streaming workloads. For the transcoding mode, since all video frames are generated and streamed at run-time, $\Delta$ is set to the arrival ts of the first transcoded video frame. 


E3PO requires the timestamp used in the motion log to be strictly aligned with the 360 video playback, which means $ts=0$ for motion log means the 360 video is just about to start playing. The current version of E3PO does not consider the scenario of video freeze. It means when the motion log is collected, the entire video plays smoothly without any stall. It also means during the simulation of video playback, the video does not freeze at all. Even in the situation that there is no appropriate video frame to display, E3PO simply displays a black screen but does not playback clock to wait for missing frames. This design choice enables a consistent synchronization between the motion timestamp and the video playback timestamp. 

For both modes, E3PO provides the user with the initial view position and allows the user to send the first tile request at the start of the system clock ($ts=0$). Then it will fast-forward to the time when video playback and motion both start. It is important to remember, when E3PO updates user a motion sample, the user can immediately send a request for a new video tile but the tile won't arrive after at least a round trip time plus the tile transmission time ($tile_{size}/BW$). 

## Sample video.json
The information of the whole preprocessed video tiles is recorded in the ```video.json``` file using a dictionary format. A typical example is shown below:

```
{
  "chunk_0000_tile_001": {
    "chunk_info": {
        "chunk_duration": 1, "chunk_idx": 0, "end_second": 1, "start_second": 0
    },
    "user_video_spec": {
      "segment_info": {
        "segment_out_info": {"height": 640, "width": 960},
        "start_position": {"height": 0, "width": 960}
      },
      "tile_info": {"chunk_idx": 0, "tile_idx": 1}
    },
    "video_size": 50252
  },
  "chunk_0000_tile_002": {
    "chunk_info": {
        "chunk_duration": 1, "chunk_idx": 0, "end_second": 1, "start_second": 0
    },
    "user_video_spec": {
      "segment_info": {
        "segment_out_info": {"height": 640, "width": 960},
        "start_position": {"height": 0, "width": 1920}
      },
      "tile_info": {"chunk_idx": 0, "tile_idx": 2}
    },
    "video_size": 48690
  },
  ...
}
```
```chunk_0000_tile_000``` is the unique index identifier for the generated tile video. Its name indicates which chunk the video belongs to and its position wihtin that chunk.

```chunk_info``` is a dictionary, identical to the content presented in the video preprocessing module.

```user_video_spec``` records specific parameters utilized by the user during the generation of this tile. You can store any parameters in this field as you need. We provide an example as follows:


<table>
    <tr>
        <th colspan="2">Parameter</th>
        <th>Description</th>
    </tr>
    <tr>
        <td rowspan="2">"segment_info"</td>
        <td>"segment_out_info"</td>
        <td>includes the tile size with width and height</td>
    </tr>
    <tr>
        <td>"start_position"</td>
        <td>includes the start position of the tile on origianl video</td>
    </tr>
    <tr>
        <td colspan="2">"tile_info"</td>
        <td>records the chunk index and tile index</td>
    </tr>
</table>


```video_size``` records the amount of data storage space occupied by the video on the file system, measured in Byte.


## Sample decision.json
The streaming decision results are recorded in the ```decision.json``` file using a list format. Similarly, a typical example is provided below:

```
[
  {
    "chunk_idx": 0,
    "decision_data": {
      "system_ts": 0,
      "tile_info": [
        "chunk_0000_tile_000", ..., "chunk_0000_background"
      ]
    }
  }
  {
    "chunk_idx": 1,
    "decision_data": {
      "system_ts": 300,
      "tile_info": [
        "chunk_0000_tile_000", ..., "chunk_0000_background"
      ]
    }
  }
  ...
]
```
```chunk_idx``` represents the index of which chunk is under download decision.

```decision_data``` is a dictionary, which records two types of data, that is ```system_ts``` and ```tile_info```. ```system_ts``` is the system timestamp when decising the current chunk. ```tile_info``` is also a list, with each of its item is a ```tile_id``` indicating which video tiles should be downloaded. Note that if background stream is supported in your approach, then the background stream chunk ```chunk_xxx_background``` is also recorded.

It should be noted that E3PO updates every 10ms, allowing users to make decisions corresponding to the system update interval. That is, users can make decisions for a chunk multiple times.