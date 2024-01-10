# Introduction
E3PO is an **O**pen **P**latform for **3**60° video streaming simulation and **E**valuation. E3PO is designed to support the simulation of a variety of 360° video streaming approaches that have been proposed so far, including projection based, tile based, or transcoding based. Particularly, E3PO allows users to convert 360° video into standard or customized projections, segment video into equal or adaptive sizes, implement customized motion prediction algorithms, apply different streaming strategies, and evaluate using any user-specific metrics. Most importantly, E3PO generates the actual visual sequences that will display on the user screen for each simulation. 

Therefore, E3PO provides a perfect solution to objectively compare the performance of different 360° video streaming approaches, using the same video content and same motion trace.



# Framework
The framework of E3PO is illustrated as the following figure, which consists of three principal modules, i.e., the ***video pre-processor***, the ***streaming simulator*** and the ***system evaluator***.

To simulate a streaming approach, the ***video pre-processor*** first segments the 360° panoramic video into small video tile chunks according to users’ specific projection and tiling parameters. Then the ***streaming simulator*** reads the provided head motion trace, and simulates the detailed streaming actions which include when and which video chunk is transmitted. Last, the ***system evaluator*** synthesizes the video sequence that is displayed on the user screen and calculates various metrics.

![](/docs/Framework.jpg "e3po_framework")



# Quick Start

## Code & Dataset
1. Download E3PO code
```
git clone https://github.com/bytedance/E3PO.git
```

2. Video Source<br>
Prepare a 360° video (which is not included in E3PO repo), rename and place it at /e3po/source/video/[sample].mp4. Note that the file name and video attributions should match the configurations listed in e3po/e3po.yml.  We have provided a sample video for particpants of 2024 MMSys Grand Challenge.


3. Motion Trace<br>
Prepare a motion trace file and place it at /e3po/source/motion_trace/[motion_trace].log. Note that E3PO has provided a sample file. If you want to use a different one, you can generate one similarly to that from [360VidStr](https://github.com/360VidStr/A-large-dataset-of-360-video-user-behaviour/blob/main/AggregatedDataset/7.txt).


## Execute commands
To simulate the streaming process, three terminal commands need to be executed sequentially. For example, with the sample simulation E1 we have provided in the project, the following commands should be executed. Note that the approach name as well as the approach type (on_demand or transcoding) should be specified.

1. Run the [make_preprocessing.py](e3po/make_preprocessing.py) script (***video pre-processor*** module)
```
python ./e3po/make_preprocessing.py -approach_name erp -approach_type on_demand
```
Corresponding results can be found at
```
|---e3po
    |---source
        |---video
            |---[group_*]
                |---[video_*]
                    |---[erp]
                        |---video_size.json
                        |---dst_video_folder
                            |---chunk_***_tile_***.mp4
    |---log
        |---[group_*]
            |---[video_*]
                |---erp_make_preprocessing.log
```

2. Run the [make_decision.py](./e3po/make_decision.py) script (***streaming simulator*** module)
```
python ./e3po/make_decision.py -approach_name erp -approach_type on_demand
```
Corresponding results can be found at
```
|---e3po
    |---result
        |---[group_*]
            |---[video_*]
                |---[erp]
                    |---decision.json
    |---log
        |---[group_*]
            |---[video_*]
                |---erp_make_decision.log
```

3. Run the [make_evaluation.py](./e3po/make_evaluation.py) script (***system evaluator*** module)
```
python ./e3po/make_evaluation.py -approach_name erp -approach_type on_demand
```

Corresponding results can be found at 
```
|---e3po
    |---result
        |---[group_*]
            |---[video_*]
                |---[erp]
                    |---evaluation.json
                    |---output_frames
                        |---xxx.png
                        |---output.mp4
    |---log
        |---[group_*]
            |---[video_*]
                |---erp_make_evaluation.log
```

## Examples
We have implemented eight simple but typical approaches, with their detailed descriptions shown in the following table.

|  Name             | Projection | Background Stream |  Tiling | Resolution |
|  ----             | ----       | ----              | ----    | ----       |
|  E1               | ERP        | w/o               | 6x6     | -          |
|  C1               | CMP        | w/o               | 6x6     | -          |
|  C2               | CMP        | w/                | 6x6     | -          |
|  C3               | CMP        | w/                | 6x12    | -          |
|  A1               | EAC        | w/                | 6x12    | -          |
|  F1 (Freedom)     | ERP        | w/o               | 1x1     | 1680x1120  |
|  F2 (Freedom)     | ERP        | w/o               | 1x1     | 2400x2176  |
|  Full             | ERP        | w/o               | 1x1     | -          |


The visual comparison results of these eight approaches are illustrated as the following figure.

![](/docs/comparison.jpg "comparison_results")


For more details, please refer to [Tutorial.md](./docs/Tutorial.md).


# Contributes
We welcome researchers to simulate their own streaming systems using E3PO and submit their implementation back to this project, so that the community can better compare the performance of different solutions. Users making contributions to E3PO shall meet the following two requirements:

- The submitted code should be reviewed by the E3PO group.
- The submitted code should follow the [GPL 2.0 License](./COPYING) adopted by E3PO.


# License
[GPL 2.0 License](./COPYING)
