# easonFansForumDaily
自动完成神经研究所每日任务
### 1.使用方法
fork本repositroy后，在Settings->Secrets中新建仓库密码（New repository secret）。
USERNAME,PASSWORD,PUSHPLUS_TOKEN,API_KEY,APP_ID


## 2.本地运行
1. Clone this repo and install prerequisites:

    ```bash
    # Clone this repo
    git clone git@github.com:TannerTam/easonFansForumDaily.git
    
    # Create a Conda environment
    conda create -n easonFansForumDaily python=3.10.0
    conda activate easonFansForumDaily
    
    # Install prequisites
    pip install -r requirements.txt
    # Install packages
    sudo apt update
    sudo apt install tesseract-ocr
    ```

2. 在本地新建`config.json`文件，内容为

    ```json
    {
        "USERNAME": "",
        "PASSWORD": "",
        "PUSHPLUS_TOKEN": "",
        "API_KEY":"",
        "APP_ID":""
    }
    ```
3. 在[网站](https://googlechromelabs.github.io/chrome-for-testing/#stable)下载与自己chrome版本相符合的chrome driver，并将文件夹解压后放到当前目录
4. 运行

    ```bash
    #无头
    python dailyMission.py --local --headless
    
    #显示窗口
    python dailyMission.py --local
    ```
