pex:
	# vytvorime pycache
	python main.py >/dev/null || true
	pex . pystache -e vindaloo.vindaloo:run -o latest/vindaloo.pex --python-shebang='/usr/bin/env python3' --disable-cache
