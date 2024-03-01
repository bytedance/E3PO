In the final assessment phase, we have selected three different categories of video, including natural landscapes, computer-generated animations, and outdoor sports (these videos will be released at [mmsys24gc data](https://bytedance.larkoffice.com/drive/folder/QQgJfhxs7lor3xdb0WGcTYMsnPb?from=space_personal_filelist)). To ensure a comprehensive and diverse evaluation, we randomly selected two segments from each video and collected the corresponding real head motion data for each segment. Therefore, our final test dataset consists of 6 video segments and their corresponding head motion data. 

During our preliminary testing, we found that the evaluation results were heavily dependent on the software and hardware environment. Therefore, in the final testing phase, we packaged all team codes along with the E3PO code into a Docker image and ran it on multiple virtual machines with identical configuration parameters (running Linux Debian 11, 8 cores, 16GB RAM, 100GB ROM). By doing so, we can ensure fairness and consistency for all teams.

Each team's solution undergoes 6 sets of tests, with each set corresponding to a combination of video segment and head motion data. By calculating the average score from these 6 sets of tests, we will determine the final rankings of all teams. It's worth noting that in order to avoid the possibility of two teams having the same score, we will take the scores of each group to 3 decimal places as the final score result. If the scores are still the same, the group with less cost (smaller $Bandwidth~ Cost$ > smaller $Storage~ Cost$ > smaller $Computation~ Cost$) wins. If the submitted code crashes in the end, its score in corresponding round that did not pass the test will be 0, and this 0 score will also be used to calculate the team's final average score.


# Final results
<div align="center">

| $Rank$ |   $Group ~ Name$   |  $S$  | $MSE$  | $Bandwidth~Cost$ | $Storage~Cost$ | $Computation~Cost$ | $Approach~Type$ |
|:------:|:------------------:|:-----:|:------:|:----------------:|:--------------:|:------------------:|:---------------:|
|   1    |                    |  |  |         |   | | |
|   2    |                    |  |  |         |   | | |
|   3    |                    |  |  |   	  |   | | |
|   4    |                    |  |  |         |   | | |
|   5    |                    |  |  |         |   | | |
|   6    |                    |  |  |         |   | | |
|   7    |                    |  |  |         |   | | |
|   8    |                    |  |  |         |   | | |
|   9    |                    |  |  |         |   | | |
|   10   |                    |  |  |         |   | | |


</div>



