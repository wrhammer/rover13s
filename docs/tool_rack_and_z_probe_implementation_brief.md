# Tool Rack + Z Probe Implementation Brief

Preparatory overview for adding (1) a tool rack with CNC moves to each tool position on M6, and (2) a Z probe to touch off and set top-of-material as Z zero.

---

## 1. Tool Rack — Move to Tool Position on M6

### Goal
On each tool change, LinuxCNC moves to a fixed XY (and optionally Z) position for that tool, then your existing M6 logic does release/lock. No manual “drive to the rack” step.

### What You Already Have
- **M6 remap** (`python/remap.py` → `remap_m6`) — handles tool type, pins (M64/M65), router/blade/saw, tool release/lock.
- **Tool table** (`tool.tbl`) — already has X,Y,Z per tool (e.g. T20 Router: `X-180.1 Y-45 Z+4.65`). Right now those are used as offsets; they can later double as “rack position” or you can keep rack positions separate.

### Implementation Options

**Option A — Use tool table X/Y (and Z) as rack position**
- Treat `tool.tbl` X,Y,Z as “position to move to when loading this tool” (in machine coords or a dedicated work coordinate, e.g. G55 “tool rack”).
- In `remap_m6`, before the physical tool exchange:
  1. Read tool geometry for the **requested** tool (or from a small “rack position” table).
  2. Move to safe Z, then to (rack_x, rack_y), then to rack_z if you use it (e.g. approach height).
  3. Run your existing release/lock and pin sequence.
  4. After load, optionally move to a common “ready” position, then continue.

**Option B — Separate rack position table**
- Keep `tool.tbl` for diameter/length/offsets only.
- Add a second source of truth for “where tool N lives”: e.g. Python dict, CSV, or extra columns in a custom table.
- In `remap_m6`, look up “rack position for tool_number” and execute moves from that table.

**Option C — Rack positions in INI or Python**
- Define something like `[TOOL_RACK]` in the INI or a dict in `remap.py`:
  - `TOOL_1_X = ...`, `TOOL_1_Y = ...`, `TOOL_1_Z = ...`
  - or `rack_positions = { 1: (x,y,z), 2: (x,y,z), ... }`
- Same idea as B: M6 reads this and runs G0/G1 to that position before/after the exchange.

### Technical Details (independent of option)
- **Coordinates:** Usually machine (G53) or a dedicated work zero (e.g. G55) that you set once at the rack.
- **Motion:** Use `self.execute("G53 G0 Z...")` and `self.execute("G53 G0 X... Y...")` (or G55 etc.) so moves are repeatable and independent of the program’s current G54.
- **Safe height:** Always clear Z (and possibly retract router/blade) before X/Y move to the rack; lower to rack Z only when it’s safe.
- **Integration point:** All of this lives inside `remap_m6`, in the same try/except as today: “move to rack for new tool → release old → [manual or auto exchange] → lock new → optional move to ready” then `tool-changed` and continue.

### What to Decide Before Coding
- Coordinate system for rack (G53 vs G55/G56 and origin).
- Exact sequence: retract → move to rack → exchange → move to “ready” vs back to last XY.
- Which tools use the rack (e.g. only router, or all tools that live in the rack).

---

## 2. Z Probe — Touch Off for Top-of-Material Z Zero

### Goal
Use a physical probe so the control can set Z0 at the top of the material, either for the first tool only or for every tool.

### Hardware (assigned)
- **Probe input:** `hm2_7i94.0.7i84.0.0.input-09` (Mesa 7i84-00 in machine head — TB1 input 9).
- **Probe:** Contact (touch) probe or conductive probe that closes a switch when it hits the surface.
- **Wiring:** Probe signal → Mesa 7i84-00 input-09. Often NC (normally closed) so a break in the wire is safe.
- **HAL:** Connect that input to `motion.probe-input` (see rover-custom.hal placeholder when ready).

### LinuxCNC Side
- **Probe aware motion:** Motion must know “probe tripped” so it can stop and record position. That’s done by connecting the probe input to `motion.probe-input` (or the probe component your config uses).  
  Standard approach: load `probe_parport` or wire the Mesa input to the same HAL net as `motion.probe-input`.
- **Parameters:** Set `PROBE = 1` in the INI so G38.x is enabled; set search velocity, etc., as needed.

### G-Code / Logic
- **Built-in cycle:** `G38.2 Z-50 F100` (or similar) does a straight probe toward the top of the part; when the probe trips, LinuxCNC stops and records the position. You can then use that in O-word or Python to set Z in the work offset.
- **Setting Z0:**  
  - `G10 L20 P1 Z0` sets current Z (in the active work offset, e.g. G54) to 0 at the **current** machine Z after the probe.  
  - To put “top of material = 0” you typically: run G38.2 so the probe touches the top, then “set current position to 0” via G10 L20 or equivalent. The exact line depends on whether you use G38.2’s reported position or the current position at trip.
- **O-word or Python:** A small routine can:
  1. Move to safe XY over the probe area.
  2. Run G38.2 (or multiple probes for average).
  3. Use the probed Z to compute the offset and issue G10 L20 P1 Z… (or set parameters and have an O-word call G10).

### “First tool only” vs “every tool”
- **First tool only:**  
  - In your job setup: run one probe routine (manual, or from a “start job” O-word/M-code).  
  - That sets G54 Z (or whatever work zero you use) so “top = Z0”.  
  - All subsequent tools use that same Z0 via their tool length offsets in the tool table.
- **Every tool:**  
  - After each M6 (or before first cut with that tool), move to a fixed probe position, run the probe cycle for that tool, update that tool’s length or the work offset so “this tool at top = Z0”.  
  - Requires a repeatable probe location and a clear workflow in `remap_m6` or in the g-code (e.g. O-word called after each tool change).

### Automating Z0 when tool is already in spindle (e.g. T20, no M6)

When you load a new project and the correct tool (e.g. T20) is already in the spindle, no M6 runs, so there is no built-in hook to probe. You need a separate “run Z0 probe” trigger. Three practical options:

**Option 1 — M-code at start of every program (recommended)**  
- Remap an M-code (e.g. **M200**) to “probe Z0 and set work offset.”  
- Your **post-processor** outputs `M200` (or `G65 P9010`) as the **first line** of every file.  
- When you load a project and press Run, the first thing that runs is the probe cycle: move to probe XY → G38.2 → set G54 Z0 (or current work offset) → continue.  
- Works the same whether the tool was just changed (M6) or already in the spindle; no extra step for you.  
- If you ever want to skip probing for a job, you can add a post-processor switch or delete/comment that first line.

**Option 2 — M-code from MDI before Run**  
- Same remapped M-code (e.g. M200) that runs “probe Z0 and set work offset.”  
- Workflow: load g-code → (machine homed, T20 in spindle) → type **M200** in MDI and Run → then Run the main program.  
- No post-processor change; you always trigger probe manually when starting a new job.

**Option 3 — First line calls an O-word subroutine**  
- Create an O-word (e.g. **O9010**) that does: move to probe XY → G38.2 → set work offset Z0 → return.  
- Put O9010 in a file in `USER_M_PATH` or `SUBROUTINE_PATH` (e.g. `ngc/probe_z0.ngc`).  
- Post-processor outputs **`O9010 call`** as the first line of every file.  
- Effect is the same as Option 1, but the probe sequence lives in an NGC subroutine instead of an M-code remap.

**Suggested flow for “T20 already in spindle, new job”**  
- Use **Option 1 (or 3)**: first line of every posted program is “probe Z0” (M200 or O9010 call).  
- So the sequence is: Load → Run → machine does “probe Z0” first → then runs the rest of the program.  
- No need to remember to run M200 from MDI; it’s automatic as long as the post always adds that first line.

**If you also probe after M6**  
- You can do both: M6 remap optionally runs a probe after loading a new tool, *and* the first line of the program runs “probe Z0” when that tool is the first (or only) one used.  
- For “T20 only” jobs, the first-line probe is enough. For “T20 then T5 then T20” jobs, you can either probe only at program start (first line) or add “probe after M6 when first tool of job” logic in the remap if you want to touch off again after each change.

### What to Prepare
- ~~One free Mesa input for the probe.~~ **Done:** using `hm2_7i94.0.7i84.0.0.input-09`.
- HAL connection from that input to motion’s probe input (placeholder in rover-custom.hal).
- INI: `PROBE = 1` and any probe-related [PROBE] or similar.
- A small “probe and set Z0” routine (O-word or Python) you can trigger from MDI or from an M-code at the start of a job.

---

## 3. How They Fit Together

- **Tool rack:** Makes M6 repeatable: “move to tool N’s rack position, then do your existing tool change.”
- **Z probe:** Gives you reliable “top of material = Z0” for one or all tools.

You can do them in either order: e.g. add probe first (manual rack for a while), then add automated moves to rack positions in M6; or build the rack moves first and add probe later. Both can share the same `remap_m6` and tool table as you already have.

---

## 4. Suggested Prep Checklist

- [ ] Decide coordinate system and origin for the tool rack (G53 vs G55/56).
- [ ] Decide which tools have rack positions and document (X,Y,Z) for each.
- [ ] Choose “rack position” storage: re-use tool table X/Y/Z, or separate table/INI/Python.
- [x] Reserve one Mesa input for the probe: **hm2_7i94.0.7i84.0.0.input-09** (7i84-00 machine head).
- [ ] Sketch HAL: probe input → `motion.probe-input` (or probe component).
- [ ] Enable probe in INI (`PROBE = 1`) when you’re ready to test.
- [ ] Write a minimal “probe Z and set G54 Z0” routine (O-word or Python) and test from MDI.
- [ ] Choose Z0 trigger for “tool already in spindle”: **M200 at first line** (remap + post), **O9010 call at first line** (sub in ngc/ + post), or **M200 from MDI** only.  
  **→ Decided:** first line in post-processor (M200 or O9010 call) so every job starts with probe Z0.
- [ ] Add that line in the post-processor (`post-processors/emc-hzntl-bits.cps` or active post) so every posted file starts with M200 or O9010 call.
- [ ] Plan M6 sequence on paper: retract → move to rack → exchange → [optional probe] → continue.

When you’re ready to implement, the next steps are: (1) add the probe input and HAL, and (2) add “move to rack position” logic into `remap_m6` using the chosen position source.
