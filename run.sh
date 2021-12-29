importchecker yacd.py
yapf -i yacd.py

export FLASK_APP=yacd
export FLASK_ENV=development
flask run
