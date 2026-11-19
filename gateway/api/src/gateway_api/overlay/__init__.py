"""OBS overlay and spectator socket support for the gateway.

The modules here relay. `camera_relay` asks the board owner to move the camera. `frame_dispatch`
validates one inbound frame and routes it to its handler. `room` holds the live sockets of each
session. None of them keeps domain state. The routes stay in `routers/overlay.py`.
"""
