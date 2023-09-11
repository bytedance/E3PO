# Development
Contestants can download [E3PO](https://github.com/bytedance/E3PO) from Github and follow the README file for the basic testing process, and refer to the six samples provided by E3PO for developing their own algorithms. For instance, if the name of contestant's approach is "star", they need to modify the following four files (or some of them), place them in the corresponding "star" folder, and then debug the algorithms.

```
|---E3PO
    |---e3po
        |---approaches
            |---star
                |---star.yml              # E3PO/e3po/options/example/
                |---star_data.py          # E3PO/e3po/data/
                |---star_decision.py      # E3PO/e3po/decision/
                |---star_projection.py    # E3PO/e3po/projection/
```

For the four modules in the "star" folder mentioned above, the specific modifications needed for each module are described as follows:
<div align=center>
    <img src=/uml.jpg width=600 height= />
</div>
## star.yml
This file is the configuration file for the contestant's approach. Besides the basic parameters, the contestant should specify the aforementioned several modules they have implemented in the star.yml file, for example:
```
data_type: StarData
decision_type: StarDecision
projection_type: StarProjection
```

## star_data.py
It should be distinguished whether it is the on-demand or transcoding mode, then inherit the methods from data/on_demand_data.py and data/transcoding_data.py respectively, and rewrite the process_video() method for each.
- on_demand
```
- process_video()
  - self._convert_ori_video()   # There may be different projection methods
  - self._generate_chunk()      # The generated image frames here will be processed using uniform encoding parameters.
  - self._generate_tile()       # There may be custom tiling involved here
```
Taking the $4\times6$ tiling of ERP format as an example, the final partition result is shown as the following figure. The index of the first tile from the left is 0, and the index of the tiles to the right and below gradually increases.

<div align=center>
    <img src=/tiling.jpg width=258 height= />
</div>

- transcosding
```
- process_video()
  - self._convert_ori_video()   # There may be different projection methods
  - self._generate_viewport()   # The generated image frames here will be processed using uniform encoding parameters.
  - self._generate_h264()       # Encode the generated frames into a video, generate an h264 file for each frame.
```
It should be noted that for the transcoding mode, its video preprocessing operation depends on the user's head movement information. After video preprocessing, we will record the decision result actually sent to the user and write it into JSON file.

## star_decision.py
For the on-demand mode, contestants should inherit the methods from decision/on_demand_decision.py and override the decision() function. However, in the transcoding mode, no further processing is required as the decision has already been handled in the data module.

- on_demand
```
- decision()
  - self._predict_motion_tile()   # Based on historical motion information, perform prediction.
  - self._tile_decision()         # Based on the prediction results, determine which tiles should be slected.
  - self._bitrate_decision()      # Based on the tile decision results, determine the quality of each tile.
```

## star_projection.py
As shown in the figure below, we need to specify that the coordinate system used in E3PO is a [right-handed coordinate system](https://www.scratchapixel.com/lessons/mathematics-physics-for-computer-graphics/geometry/coordinate-systems.html). Accordingly, the [three-dimensional matrix rotation](https://en.wikipedia.org/wiki/Rotation_matrix) used in E3PO for processing perspective transformation is also based on a right-handed coordinate system. If contestants want to implement a custom projection method, the functions they need to modify should include:

<div align=center>
    <img src=/coordinates.png width=258 height= />
</div>

```
- generate_fov_coor()       # Generate the pixel coordinates of the user's fov with given parameters
    - uv_to_coor()          # Given viewing direction, return the pixel coordinates on the image
- coor_to_tile()            # Given pixel corredinates, return the corresponding tile indexes
```

The contestants only needs to return the pixel coordinates of the FoV on the concatenated image in the generate_fov_coor() function based on their custom projection and tiling methods. The format of the concatenated image is shown below, with panoramic frames of different quality levels placed from left to right. If there is a background stream, the low-resolution frame of the background stream will be placed in the last column, and the area where the background stream frame that is not as large as the panoramic frame will be set as [0, 0, 0].

<div align=center>
    <img src=/concat_img.jpg width=600 height= />
</div>

In E3PO, contestants only need to modify one or several above-mentioned files to implement their solution. It is worth mentioning that to ensure fairness for all contestants, we specify that everyone uses the same encoding parameters, such as the same GoP size, using only I/P frames and not using B frames, as well as the same preset parameters. Except for the files mentioned above, contestants generally should not make modifications to other files. If there is a need for modifying the general system code of E3PO, please submit requests to the github repository [E3PO](https://github.com/bytedance/E3PO).


# Submission
Contestants need to submit two parts of content, namely the code files and a technical report.

**Code files:** After testing the algorithm locally and making sure there are no errors, contestants can pack the relevant modified code and submit it to organizers' email. Taking the "star" solution as an example, contestants should put the *star.yml*, *star_data.py*, *star_decision.py*, and *star_projection.py* files in the star folder, and then compress them into the star.zip or star.tar format. We recommend that contestants submit their algorithms in source code form (for ease of subsequent evaluation), but we also support contestants submitting their algorithms in binary format. The submitted code will be tested with the following path.
```
|---E3PO
    |---docs
    |---e3po        
        |---approaches
            |---star   # user1
                |---star.yml         
                |---star_data.py          
                |---star_decision.py      
                |---star_projection.py            
            |---moon   # user2
                |---moon.yml
                |---moon_data.py          
                |---moon_decision.py      
                |---moon_projection.py          
            ...
```
**Technical report:** Contestants also need to submit a technical report that follows the requirements in [Open-source Software and Datasets](https://2024.acmmmsys.org/participation/cfp/), which should include detailed information about their implemented algorithm. The technical report of the challenge-winning contestants will receive a notification to prepare a camera-ready version, which will be published on ACM DL after being reviewed and recognized as meeting the publishing standards.

# Scoring
We mainly consider two parts for algorithm scoring, i.e., user viewing quality and system cost. The submitted code of all contestants will be evaluated on the same machine, and the file path after evaluation is shown as follows. 
```
|---E3PO
    |---docs
    |---e3po        
        |---result
            |---group_*
                |---video_*
                    |---star   # user1
                        |---decision.json
                        |---evaluation.json
                    |---moon   # user2
                        |---decision.json
                        |---evaluation.json
                    ...
        |---log
            |---group_*
                |---video_*
                    |---star   # user1
                        |---star_***.log
                    |---moon   # user2
                        |---moon_***.log
                    ...
```
Currently, we plan to evaluate all contestants' codes in two stages.

**Stage 1:** Code development and testing stage. The challenge organizers will evaluate the submitted code every 3 days, sort all contestants' scores (including total scores and item scores) in descending order, and publish them in the official [topic group](./mmsys24gc_group.jpeg) for contestants to check their rankings and perform targeted optimization.

 $Rank$ | $Group\ name$ | $S$ | $VPSNR$ | $C_{b}$ | $C_{s}$ | $C_{c}$
 :-: | :-: | :-: | :-: | :-: | :-: | :-:
1 |  |  |  |  |  |   
... |  |  |  |  |  |   

**Stage 2:** Final evaluation stage. After the challenge deadline, we will give final scores to all the received contestant codes. In order to ensure the fairness of the challenge results, we consider the following rules:
- There are different test groups, such as 3 groups with different RTTs (100ms, 150ms, 300ms) and 3 groups with different video sets (different complexities). The final score of all contestants' codes will be the average of these 6 scores. The top 3 contestants with the highest final scores will respectively win the first, the second, and the third place in the challenge.
- To avoid the possibility of two teams having the same score, we will take the scores of each group to 3 decimal places as the final score result. If the scores are still the same, the group with a higher single test score (smaller $Trans_{cost}$ > smaller $Calc_{cost}$ > smaller $Storage_{cost}$) will win.
- If the submitted code crashes in the end, its score in corresponding group that did not pass the test will be 0, and this 0 score will also be used to calculate the contestant's final average score.













