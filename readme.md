### TIPS

This repo is based on [PyQt5-YOLOv5](https://github.com/Javacr/PyQt5-YOLOv5)

Download the models of  YOLOv5 v6.1 from [here](https://github.com/ultralytics/yolov5/releases/tag/v6.1)，and put the them to the pt folder. When the GUI runs, the existing models will be automatically detected.

### Quick Start

```bash
conda create -n yolov5_pyqt5 python=3.8
conda activate yolov5_pyqt5
pip install -r requirements.txt
python main.py
```
### About Packaging

- install pyinstaller

```
pip install pyinstaller==5.7.0
```

- package the GUI

```
pyinstaller -D -w --add-data="./utils/*;./utils" --add-data="./config/*;./config" --add-data="./icon/*;./icon" --add-data="./weights/*;./weights" --add-data="./imgs/*;./imgs" main.py
```

- if no errors occur, the packaged application is in dist/main

### Function

1. support image/video/webcam/sonar_data as input
2. change model
3. change IoU
4. change confidence
5. set latency
6. play/pause/stop
7. result statistics
8. save detected image/video automatically


