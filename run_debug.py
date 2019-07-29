#!/usr/bin/python3

# wrapper script for flask < 1.0

from yami import create_app

app = create_app()
app.run(debug=True, host="0.0.0.0")
