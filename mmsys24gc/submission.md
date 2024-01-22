# Submission
Contestants need to submit two parts of content, namely the code files and a technical report.

**Code files:** Put all your python source code and auxiliary files in one folder. Compress the folder to a zip file or tar ball and submit to organizer’s email (guiyongqiang@bytedance.com and suoyanyan@bytedance.com). You may also upload your solution to a git repo and email us the repo URL. Please don’t include any E3PO code in your submission. We will run your code using the latest version of official E3PO. We accept binary code submission as well but you should contact the organizer early to make sure the binary file you generate can run on the server for final evaluation. 

**Technical report:** Contestants also need to submit a technical report ([ACM style format](https://www.acm.org/publications/proceedings-template), up to 6 pages plus references) that follows the requirements in [Open-source Software and Datasets](https://2024.acmmmsys.org/participation/cfp/), which should include detailed information about their implemented algorithm. Even though the winners are not determined by the quality of the technical report, you should expect to have your technical report meeting the ACM publishing quality standard before the [camera-ready due](https://2024.acmmmsys.org/gc/360-vod/) date, **which is only one week after we announce winning teams**.

# Scoring
We will follow the defined performance metric score for performance evaluation. Currently, we plan to evaluate all contestants' codes in two stages.
<div align=center>
    <img src=./formula.jpg width=400 height= />
</div>

**Stage 1:** Code development and testing stage. All participating teams can use the provided video and motion trace to test their implemented solutions. You are encouraged to report your scores to the organizers or submit your code and we can test-run your simulation in a similar process to the final evaluation. Meanwhile, we will manage a score board and update daily. Please join the official [discussion group](mmsys24gc_group.jpeg) for more information about the score board.
<div align=center>
    <img src=./rank_table.jpg width=700 height= />
</div>

**Stage 2:** Final evaluation stage. After the challenge deadline, we will give final scores to all the received contestant codes. In order to ensure the fairness of the challenge results, we consider the following rules:
- We will run each submitted simulations using different video sets/motion traces (The video/motion trace for final evaluation will be released after the submission deadline). The final score of all contestants' codes will be the average of all simulations. The top 3 teams with the highest final scores win the challenge.
- To avoid the possibility of two teams having the same score, we will take the scores of each group to 3 decimal places as the final score result. If the scores are still the same, the group with less cost (smaller $Bandwidth~ Cost$ > smaller $Storage~ Cost$ > smaller $Computation~ Cost$) wins.
- If the submitted code crashes in the end, its score in corresponding group that did not pass the test will be 0, and this 0 score will also be used to calculate the contestant's final average score.
