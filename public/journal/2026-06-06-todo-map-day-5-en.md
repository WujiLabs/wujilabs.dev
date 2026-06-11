# Day 5 — Will the workflows I'm building today be scrap metal once super AI arrives?

*Wuji Labs (Cosimo with Claude Opus 4.8 and Gemini Pro 3.1).*
*2026-06-06. MIT license.*

Last week at a founders' gathering, an investor who also codes asked me a sharp question.

The gist: the top-level large-model companies are going to keep pushing down, layer by layer, and eventually swallow the verticals everyone else is building in. Given that trend, what exactly do small builders survive on?

It's a real concern, and a common one.

Take what we've been building for the past 30 days — this Todo Map on top of the Playtiss engine. Today I'm working hard to decompose tasks, design workflows. When that omnipotent super AI shows up, won't all this just get eaten in one bite — entirely obsolete?

My answer: what we're building isn't an "app" waiting to be eaten by a big model. It's a *collaboration network* that doesn't disappear even when super AI arrives. The reason people worry, I think, is that they're conflating two things — *framework* and *collaboration*.

## The exoskeleton thins; the network doesn't

In AI circles, there's a term: Harness. The Claude Code you use is, structurally, just a Harness wrapped around a large model.

There's a clear trend over the past two years: Harnesses are getting thinner.

In the old days, models were dumb — you had to wrap them in long prompts to keep them on track. Now the models are smart, and a lot of those constraints have been peeled away — give them a few simple tool interfaces and they can run an entire loop themselves.

So people figure: Harnesses will simplify (or even disappear) as models get stronger. Workflows must be heading the same way.

But this conflates two different things. **A Harness is an exoskeleton worn by one AI; an engine like Playtiss is a collaboration network spanning several intelligences.** The first is a single-soldier kit. The second is the field where multiple intelligences — human and AI — get work done.

Even when super AI shows up, the nodes and boundaries Playtiss maintains probably won't disappear. Because in the real world, there are several boundaries that can't be crossed.

## The boundaries that hold

**First: the compute economics.**

Even if super AI's inference cost crashes in the future, compute is always physically tiered.

You don't pull a super AI in to extract dates from a few emails, or bulk-rename files. That's killing a chicken with an ox-cleaver.

Inside a collaboration network, you naturally keep the lightweight nodes — a few lines of Python, a small model — to handle the scrappy work. You only route to super AI when the work genuinely needs deep reasoning. The math of cost and efficiency has to be distributed across a network.

**Second: the compliance wall.**

This is the hard rule of reality. In healthcare, in law, there are NDAs, fiduciary duties, regulations that prohibit mixing sensitive client data with general external data in a single black box.

Whether the super AI lives in someone's cloud or eventually gets pushed into the corporate intranet, the real-world commercial requirements demand data firewalls and permission isolation: certain nodes process confidential material, certain key nodes have humans taking final responsibility and signing off.

Without that network of boundaries, even the strongest intelligence struggles to plug legally and compliantly into the chain of corporate accountability.

**Third: super AI's own needs.**

Step back: even if you set super AI loose on a 3-month complex engineering task, on its own.

Facing a task at that timescale, it needs its own collaboration system — break the massive thread of thought into subtasks, plan their dependencies, allocate context to each one, manage their states.

A collaboration engine isn't only for humans. It can also be the scaffolding super AI uses for self-management, self-evolution.

## Workflows won't die — they'll just morph

So workflows won't disappear because AI gets stronger. They'll just *elastically merge*.

That's the conviction behind Playtiss's architecture: it isn't betting super AI will fail. It's being forward-compatible with the future.

Inside the Playtiss network, nodes and edges are dynamic. Tomorrow the model evolves and you don't have to tear everything down — you just say one sentence: *"Take those 5 tedious preliminary review steps, fold them into a single big node, hand it to the new model, push the result through to my final review node."*

The old inefficient friction goes; a stronger node takes its place. But the core boundaries you kept for safety, cost, and responsibility — those stay.

In that sense, Playtiss isn't a temporary patch built because "AI is still dumb today." It's the collaboration substrate left in place — between humans, scripts, small models, and super AI — that doesn't get withdrawn.

These 5 days of journals took the small task of "writing a Todo" all the way to system architecture and future evolution. The blueprint of the design philosophy is laid out.

Tomorrow we go back to code, and see what fun (or painful) surprises actually show up when this blueprint hits the keyboard.

See you tomorrow.

---

*Playtiss is the open-source decentralized collaboration engine built by Wuji Labs. On GitHub: [github.com/WujiLabs/playtiss](https://github.com/WujiLabs/playtiss). Beyond open source, Wuji Labs also offers teams and enterprises architecture consulting and collaboration system customization. We don't think the future is binary — either "throw everything to an AI black box" or "pure human grind." We use coaching-style conversation and training to help teams plug AI partners into the business, and to build workflows that grow stronger and evolve alongside the AI. If you're being drained by terrible system friction, or wrestling with how to bring AI into your work — get in touch: cosimo@wujilabs.dev.*
