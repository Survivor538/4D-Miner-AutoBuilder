4D game auto building script using Python... Game: 4D Miner

ver0.10 在平坦地形上自动建造任意规格的四维超立方体 按w分大层，在每一层w里按每一层y分层建造；每一个xz平面按照蛇形走位建造，先向+z方向建一条，再向+x移动一格，再向-z方向建一条，再向+x移动一格，以此类推 https://www.bilibili.com/video/BV1sCDyBbEpH

ver0.20 在平坦地形上自动建造任意结构的小型建筑 以“竖直柱”为基本单位，按w(最大层)→x→z逐层扫描。每次先完整建一根柱，同时挖掉上一柱中不需要的方块。每一z层多建一个辅助柱 https://www.bilibili.com/video/BV12GDXBQE6m

read_position2.zip 程序识别4D Miner右下角指南针坐标.方式为截图+颜色识别+模板匹配
