"""Linux kernel watchdog support"""

watchdog_device = None

def watchdog(timeout=None, device='/dev/watchdog'):
    """Initialize and/or feed the watchdog"""
    global watchdog_device
    # Close the watchdog, if that is what is wanted
    if timeout == 0:
        if watchdog_device:
            watchdog_device.magic_close()
            watchdog_device = None
            return
    # Open the watchdog, if needed
    if not watchdog_device:
        import watchdogdev
        watchdog_device = watchdogdev.watchdog(device)
    # Set the timeout, if needed
    if timeout:
        watchdog_device.set_timeout(timeout)
    # Feed the dog
    watchdog_device.feed('\n')
