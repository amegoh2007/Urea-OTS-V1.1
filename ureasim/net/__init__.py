"""Console transport — the engine's link to its single local console.

Pure Python, no Qt: the engine runs headless, so nothing in this package may import a GUI
toolkit.

    protocol      framing and message kinds
    server        asyncio TCP server on the loopback interface: state out, commands back
    engine_host   the plant stepped on its own physics thread, served through the server

The console's end of the link is `ureasim.hmi.bridge.EngineBridge`, which speaks this same
protocol over a `QTcpSocket`.
"""
