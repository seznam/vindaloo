pex:
	# vytvorime pycache
	python main.py >/dev/null || true
	pex . pystache sostool -e sostool.sostool:run -o latest/sostool.pex -f dist --python-shebang='/usr/bin/env python3'
