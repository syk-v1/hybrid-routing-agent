# Hybrid Routing Agent — video script (~2:10)

Read at a relaxed pace; each section matches one slide.

## Slide 1 — Title (~15s)
Hi! This is the Hybrid Routing Agent, our entry for Track 1 of the AMD Developer
Hackathon. The idea is simple: every query takes the cheapest path that still gets
the answer right.

## Slide 2 — The scoring game (~20s)
The competition scores in two steps. First, an LLM judge checks accuracy — fail the
bar and you're off the leaderboard. Then survivors are ranked by total Fireworks
tokens, and fewest wins. Our insight: most prompts don't need a frontier model.
Paying big-model tokens to answer "twelve plus forty-seven" is throwing away rank.

## Slide 3 — How it works (~25s)
At the core is a twelve-signal complexity router. Regex and keyword signals — code,
math, reasoning, entity extraction, sentiment, format constraints — score every
prompt from zero to one, with no extra LLM call. Easy prompts run on a local phi-3
mini model, for free. Hard ones go straight to Fireworks. In between, a cascade
tries the local model first and only escalates when a confidence check says the
answer looks shaky.

## Slide 4 — Built for the harness (~20s)
Everything ships as one Docker container built for the judging harness. It reads
tasks from input, answers them concurrently with per-task isolation and an internal
deadline, and writes valid results before exiting. The local model's weights are
baked into the image, and every credential and model name comes from the environment
at runtime — nothing is hardcoded.

## Slide 5 — Proven, not promised (~20s)
And this is all proven, not promised. On the published image, our CI verified twelve
out of twelve sample answers with zero remote tokens, all eight capability categories
answered end to end, a fifty-second batch against a ten-minute limit, and a three
point six gigabyte image against a ten gigabyte cap.

## Slide 6 — Nothing wasted (~18s)
We also never waste an answer. If a remote call fails, the agent returns the local
answer it already computed — because a shaky answer can still pass the judge, but an
empty one never can. One crashing task can't sink the batch, and every failure path
is exercised in CI.

## Slide 7 — Close (~10s)
Hybrid Routing Agent: big-model accuracy, small-model bill. The image is public on
GitHub Container Registry. Thanks for watching!
