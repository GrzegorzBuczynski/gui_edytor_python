all:
	python3 -m venv myenv
	. myenv/bin/activate && python3 app.py

push:
	git add .
	git commit -m "Update"
	git push