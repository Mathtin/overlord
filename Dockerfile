###################################################
#........../\./\...___......|\.|..../...\.........#
#........./..|..\/\.|.|_|._.|.\|....|.c.|.........#
#......../....../--\|.|.|.|i|..|....\.../.........#
#        Mathtin (c)                              #
###################################################
#   Project: Overlord discord bot                 #
#   Author: Daniel [Mathtin] Shiko                #
#   Copyright (c) 2021 <wdaniil@mail.ru>          #
#   This file is released under the MIT license.  #
###################################################

FROM python:3.8.7

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY src src

COPY res res

CMD [ "python", "src/main.py" ]
