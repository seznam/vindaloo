pex:
	# vytvorime pycache
	python main.py >/dev/null || true
	pex . pystache -e sostool.sostool:run -o latest/sostool.pex --python-shebang='/usr/bin/env python3' --disable-cache
