# Using SBS with an agent

Coding agents can run experiments with SBS and change its code for you.
To do this well, an agent needs to know how SBS works and where its limits are.
SBS comes with a guide for this: [`skill.md`](https://github.com/GiorgDiama/SymBChainSim/blob/base/skill.md), in the root of the repository.

## What the guide covers

- **What SBS is for**, and how far to trust its results. Relative results, such as "configuration A beats configuration B", are more reliable than absolute numbers.
- **How to run it**: the commands, `--set`, scenario mode, units and run time.
- **How to design experiments**: seeds, scenarios, and runs with random conditions.
- **How to read the results**, and the signs of a broken run.
- **Where things live** in the code.
- **How to change the code**: the rules that must always hold, and some good practice for research code.

## How to use it

The guide is a plain Markdown file, so it works with any agent.
Give it to your agent in one of these ways:

- Ask the agent to read `skill.md` before it starts.
- Add a line to your agent's instructions file, such as `Read skill.md before working on this repository.`
- Copy the file to the place where your agent loads its skills or instructions from.

## Example prompts

- "Compare PBFT and BigFoot with 3 faulty nodes. Use 10 seeds and report the mean throughput and latency."
- "Run `light_scenario` with each of the three protocols and tell me which one has the lowest latency."
- "Add a metric that counts the round changes on each node, and print it with `-v`."

Check the agent's work as you would check your own.
Look at the design of the experiment, and at the code it changed.
