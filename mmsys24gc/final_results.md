# Final Evaluation and Ranking
We have received final submissions from 10 teams. We want to thank everyone for your participation. Here we disclose the final results. 

## Environment
For the final evaluation, we packaged all team's codes along with the E3PO code into a [Docker image](https://bytedance.larkoffice.com/drive/folder/HqKhfhzDjlsD9SdaAW3cmFaGnFd) and ran it on multiple virtual machines with identical configuration parameters. These machines feature an Intel(R) Xeon(R) Gold 6148 CPU @ 2.40GHz and run Linux Debian 11. Each virtual machine is equipped with 8 cores, 16GB of RAM, and a 100GB ROM. 

## Dataset
We have selected three panorama videos as the dataset for the final evaluation. It contains three different categories of video (i.e., natural landscapes, computer-generated animations and outdoor sports), all with resolution $7680\times3840$, frame rate 30$fps$, and Equi-Rectangular Projection (ERP). To ensure a comprehensive and diverse evaluation, we randomly selected two segments from each video and collected the corresponding real head motion data for each segment. Therefore, our final test dataset consists of 6 video segments and their corresponding head motion data. These segments can be downloaded at [mmsys24gc data](https://bytedance.larkoffice.com/drive/folder/HqKhfhzDjlsD9SdaAW3cmFaGnFd). 

## Ranking Methodology
We rank all submissions based on the average score of all six tests. As we have stated, we  take 3 decimal places for each score. If the submitted code crashes during the test, its score in the corresponding test will be 0, and this 0 score will also be used to calculate the team's final average score.

## Results

<div align="center">

| $Rank$ |   $Group ~ Name$   |  $Avg~Score$  | $Video1 ~S1$ | $Video1 ~S2$ | $Video2 ~S1$ | $Video2 ~S2$ | $Video3 ~S1$ | $Video3 ~S2$ |
|:------:|:------------------:|:-------------:|:------------:|:------------:|:------------:|:------------:|:------------:|:------------:|
| 1	     | bitedance          | 8.164 |	9.838 |	7.328 |	9.630 |	6.999 |	9.352  |	5.835 |
| 2 	   | Bingo              | 7.794 |	8.845 |	6.832 |	9.193 |	6.441 |	10.185 |	5.267 |
| 3      | 360LCY	            | 7.621 |	8.534 |	6.356 |	8.826 |	6.493 |	9.217  |	6.303 |
| 4      | No.1	              | 6.826 |	8.503 |	6.366 |	8.049 | 3.085 |	9.415  |	5.538 |
| 5      | SJTU_medialab      | 6.163	| 8.569 |	6.667 |	8.531 |	1.621 |	8.513  |	3.077 |
| 6      | Infonet-USTC       | 6.028 |	5.066 |	6.199 |	7.175 |	5.296 |	7.186  |	5.247 |
| 7      | Rhinobird          | 5.827	| 4.859 |	5.810 |	6.782 |	4.906 |	7.351  |	5.252 |
| 8      | Apparate	          | 5.547 |	7.977 |	4.943 |	8.902 |	3.176 |	5.245  |	3.038 |
| 9      | 360 Security Guard | 0.538 |	0.196 |	0.137	| 0.927 |	0.778 |	0.366  |	0.822 |
| -      | Daybreak (internal)|    -	| -     | -     |	-     |	-     |	-      |	-     |

</div>



## Extra Round
We also performed an extra round for the top three teams using two additional segments of a forth video (also included in the dataset). The results indicate a consistent ranking. 

<div align="center">

| &emsp; $Rank$ &emsp; | &emsp;  $Group ~ Name$  &emsp; |  &emsp; $Avg ~Score$ &emsp; | &emsp; $Video4 ~S1$ &emsp; | &emsp; $Video4 ~S2$ &emsp; | 
|:------:|:------------------:|:--------------:|:-------------:|:------------:|
| 1	     |  bitedance         | 4.032 |	4.221 |	3.842 |
| 2	     |  Bingo             | 3.839 |	4.100 |	3.579 |
| 3      |  360LCY	          | 3.769 |	3.997 |	3.541 |

</div>



# Final Ranking
We congratulate the three teams winning this grand challenge! 

<div align="center">

|  &emsp;&emsp; $Rank$ &emsp;&emsp; | &emsp;&emsp; $Group ~ Name$ &emsp;&emsp; | $ Affiliation $ |
|:---------:|:-------------------:| :-------------------: |
| 1st Place	|      Bitedance      | Beijing University of Posts and Telecommunications |
| 2nd Place	|      Bingo          | Communication University of China |
| 3rd Place |      360LCY	      | Kingston University |

</div>

