def remap_m201(prolog, params=None):

    print("Loading m201...")

    import linuxcnc
    cmd = linuxcnc.command()

    try:
        cmd.mdi("M64 P0")
        print("m201 executed successfully.")

    except Exception as e:
        print(f"Error in remap_m201: {e}")

    return
