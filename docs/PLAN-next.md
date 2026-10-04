# Next: electrification, then green science

Written 2026-10-04. The player asked for electrification first. It is also what green science needs: a green line uses about 4× the iron per flask that red does.

## Where we stand
- **Red science:** 3 flask assemblers make 0.3 flask/s. The labs research continuously, and `research_keeper.py` queues the next tech.
- **Researched:** Automation, Logistics, Electric mining drill, Steel processing. Logistic science pack is in progress.
- **Plate buffers:** the iron chest holds 578 and the copper chest 523. Each smelter is 2 burner drills, about 0.5 plate/s at most.
- **Power:** one boiler and one steam engine (900 kW cap), drawing about 0.3 MW. The boiler is fed by hand, which is the weak point. Coal used about 40 per 10 min with 3 lines running.

## Phase A: electrification
1. **Coal line to the boiler.** There is no water near the coal field (-116..-95, 28..50), so coal goes to the lake by belt.
   - 2 electric drills on coal output onto a belt that runs east to the power block. About 160 belts, roughly 240 iron.
   - At the block, an inserter takes coal off the belt into the boiler, replacing the chest and burner inserter.
   - Pass: `prove` on the boiler over 3600 ticks with no hand coal, and the chest count is not needed.
2. **Second steam engine.** One boiler feeds 2 engines, for 1.8 MW. It is a stamp change only (`power.txt`, engine chained north).
3. **Electric drills on iron and copper.**
   - 4 drills per ore (0.5 ore/s each) on the existing patches, outputting onto a belt into stone-furnace columns.
   - Furnaces are fed by inserters; output goes onto the existing chest-to-belt feeds.
   - 8 drills is 720 kW, which the second engine covers.
   - Furnaces stay burner-fuelled, with coal from a branch of the coal belt. Iron target: 2 plates/s. Copper target: 1 plate/s.
4. **Fuel the burner drills from the coal belt** until they are replaced. After that the player no longer has to feed coal.

## Phase B: green science (after Logistic science pack is researched)
- **Rate:** match red, 0.3 flask/s.
- **Recipe chain:** 1 inserter + 1 belt → 1 green flask, 6 s.
- **Assembler counts at assembler-1 speed 0.5:**

  | Product | Assemblers |
  |---|---|
  | Green flask | 4 (12 s each) |
  | Inserter | 1 |
  | Belt | 1 |
  | Gear | 1 (0.45/s needed, 1/s per assembler) |
  | Circuit | 1 |
  | Copper cable | 1 |
- **Inputs:** about 1.7 iron/s and 0.45 copper/s for green, on top of red's 0.6 iron/s and 0.3 copper/s. That is why Phase A comes first.
- **Layout:**
  - An iron belt and a copper belt run side by side south of the existing iron belt (y≈28+).
  - The intermediates assemblers sit along the belts. The green flask assemblers feed a flask belt.
  - Labs are fed red and green from the flask belt. Red is moved onto it from the 3 red assemblers.
- **Code changes:**
  - `research_keeper.py` must accept red+green techs once green production is proven. Today it only picks red-only techs.
  - New stamp codes, if needed: splitter, a long inserter for the lab chain.

## Order of work
1. Coal ferry (stopgap; running).
2. Coal belt and boiler inserter.
3. Second engine.
4. Electric drills on iron and copper.
5. Green science.

Each step goes through plan → look/shot/lint → build → prove, and STATE.md is updated after each one.
