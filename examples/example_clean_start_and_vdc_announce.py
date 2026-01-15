# (relevant excerpt with the announce call updated)
...
    if vdc:
        if not _is_valid_dsuid(vdc.dsuid):
            print(f"Refusing to announce vDC with invalid dSUID: {vdc.dsuid}")
        elif host._session and host._session.writer:
            from pyvdcapi.network.tcp_server import TCPServer

            # Create announce message (announcement is always a notification)
            message = vdc.announce_to_vdsm()
            try:
                await TCPServer.send_message(host._session.writer, message)
                print(f"Sent announcevdc for vDC {vdc.dsuid}")
            except Exception as e:
                print(f"Failed to send announce message: {e}")
        else:
            print("No active vdSM session writer available — cannot send announce message")
...
