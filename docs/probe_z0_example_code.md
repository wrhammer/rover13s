# G38.2 Z0 Probing — Example Code

**G38.2 is g-code.** It runs in the LinuxCNC interpreter. You can use it in either:

1. **An NGC subroutine** (e.g. `ngc/probe_z0.ngc`) — pure g-code, called from the first line of your posted file or from MDI.
2. **A Python M-code remap** (e.g. M200) — Python calls `self.execute("G38.2 ...")` (and other g-code) to run the probe cycle.

Below are examples of both. **Probe XY, depth, and feed** are placeholders; set them for your machine and fixture.

---

## 1. NGC subroutine (O-word)

Lives in your `ngc/` folder so it’s in `USER_M_PATH` / `SUBROUTINE_PATH`. The posted file’s first line can be `O9010 call`, or you can call it from MDI.

**File: `ngc/probe_z0.ngc`**

```ngc
%
O9010 sub (Probe Z0 — set top of material to Z0 in active work offset)
(Assumes: machine homed, probe wired to motion.probe-input, PROBE=1 in INI)
(Set #1 #2 #3 #4 for your machine or pass as params from caller)

G21 G90 G40
#1 = 0    (Probe X position in current work coord, or use G53 X value)
#2 = 0    (Probe Y position)
#3 = -50  (Probe depth: Z travel below start, mm — enough to hit top of material)
#4 = 100  (Probe feed, mm/min — slow and repeatable)

G0 Z10       (Safe clearance Z)
G0 X#1 Y#2   (Move to probe XY)
G38.2 Z#3 F#4 (Probe toward Z#, stop on contact; error if no contact)
G10 L20 P1 Z0 (Set G54 Z so current position = 0. P1=G54, P2=G55, etc.)
G0 Z10       (Retract to clear)
O9010 return
%
```

**From MDI:** `O9010 call`  
**From posted g-code:** Make the first line `O9010 call` so every job starts with this probe.

To use a different work offset (e.g. G55), use `G10 L20 P2 Z0` (P2 = G55). Use the same P number as your normal fixture.

---

## 2. Python M-code remap (e.g. M200)

The **G38.2 and G10** logic stays as g-code; the Python remap only **sends** that g-code via `self.execute(...)`. So the “code” is still G38.2 etc.; it’s just driven from Python.

**In `python/remap.py`** (and register `REMAP=M200 ...` in the INI):

```python
def remap_m200(self, **params):
    """M200: Probe Z0 and set active work offset Z to 0 (top of material = Z0)."""
    if self.task == 0:
        yield INTERP_EXECUTE_FINISH
        return INTERP_OK

    # --- Set these for your machine ---
    PROBE_X = 0.0      # Probe position X (in current work coord or use G53)
    PROBE_Y = 0.0      # Probe position Y
    PROBE_DEPTH = -50.0  # Z travel below start (mm)
    PROBE_FEED = 100.0  # mm/min
    SAFE_Z = 10.0      # Clearance height, mm
    # G54 = P1, G55 = P2, etc.
    WORK_OFFSET_P = 1

    try:
        self.execute("G90")
        self.execute(f"G0 Z{SAFE_Z}")
        yield INTERP_EXECUTE_FINISH
        self.execute(f"G0 X{PROBE_X} Y{PROBE_Y}")
        yield INTERP_EXECUTE_FINISH
        self.execute(f"G38.2 Z{PROBE_DEPTH} F{PROBE_FEED}")
        yield INTERP_EXECUTE_FINISH
        self.execute(f"G10 L20 P{WORK_OFFSET_P} Z0")
        yield INTERP_EXECUTE_FINISH
        self.execute(f"G0 Z{SAFE_Z}")
        yield INTERP_EXECUTE_FINISH
    except Exception as e:
        print(f"M200 probe error: {e}")
        yield INTERP_ERROR
        return
    yield INTERP_EXECUTE_FINISH
    return INTERP_OK
```

**INI** (e.g. in `[RS274NGC]` with your other REMAPs):

```ini
REMAP=M200 modalgroup=3 python=remap_m200
```

Then the first line of every posted file can be **M200** and the interpreter will run this remap, which runs the G38.2 (and rest) via `self.execute(...)`.

---

## 3. Summary

| Where the “code” lives | What runs G38.2 | Good for |
|------------------------|-----------------|----------|
| **NGC subroutine**     | Interpreter runs `probe_z0.ngc` (O9010). | First line `O9010 call`, or MDI. No new M-code. |
| **Python remap (M200)** | Interpreter runs g-code sent by `self.execute("G38.2 ...")`. | First line `M200`, or MDI. One remap, easy to change X/Y/depth in Python. |

In both cases **G38.2 is g-code**; the Python remap is just a wrapper that feeds that g-code to the interpreter. Use either the NGC sub or the M200 remap from the first line of the post so every job starts with probe Z0.
