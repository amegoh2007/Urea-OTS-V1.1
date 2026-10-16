"""Station transport — one engine, many consoles.

Pure Python, no Qt: the engine runs headless on a machine with no display, so nothing in
this package may import a GUI toolkit.

    protocol   framing, message kinds, roles, command authorisation
    server     asyncio TCP server that fans state out and funnels commands back

The console's end of the link is `ureasim.hmi.bridge.EngineBridge`, which speaks this same
protocol over a `QTcpSocket`.
"""
