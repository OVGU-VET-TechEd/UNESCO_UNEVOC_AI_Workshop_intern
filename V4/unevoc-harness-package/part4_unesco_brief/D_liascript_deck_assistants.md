<!--
author:   UNESCO UNEVOC Centre Magdeburg / OVGU
email:    unevoc@ovgu.de
version:  1.0.0
language: en
narrator: US English Female
comment:  AI assistants, agents and knowledge bases — what they are, how they work,
          and where they fit in UNEVOC practice. Fully offline demonstration.

@style
.lia-slide__content h2 { border-bottom: 2px solid #1a4f8a; padding-bottom: .2em; }
blockquote { border-left: 4px solid #c0762b; }
@end
-->

# AI Assistants, Agents and Knowledge Bases

**What they are, how they work, and where they fit in UNEVOC practice**
UNESCO UNEVOC Centre Magdeburg · Otto von Guericke University Magdeburg

Everything demonstrated today runs on a **local model**. No cloud service, no API key,
no data leaving the room.

--{{0}}--
Welcome. One framing point before we start. Most of the confusion in this field is
vocabulary rather than technology. The words assistant, agent and knowledge base get
used interchangeably in vendor material, and they describe things with different costs,
different failure modes, and different governance requirements. By the end of today you
will be able to tell them apart, and you will have watched a working one refuse to answer
a question — which is the behaviour that matters most.

    {{1}}
> **Four sections**
>
> 1. The pieces, precisely — what a model is and is not
> 2. Knowledge bases — where "it knows our documents" actually comes from
> 3. Assistants and agents — who decides the next step
> 4. Four UNEVOC use cases, and a live demonstration

--{{1}}--
Sections one to three are the conceptual core. Section four is the practical part and
includes the live demo. Every slide has a facilitator note underneath it.

## Section 1 — The Pieces, Precisely

### What a language model actually is

    {{0}}
> A function, **fixed at training time**, that takes text and predicts what comes next.
> Run it repeatedly and you get more text.

    {{1}}
Four consequences that follow directly from that definition:

- It has **no memory**. Every call is independent.
- It has **no access** to your files, your email, or the internet.
- It does not **look things up**. It produces what fits the patterns it learned.
- It cannot **do** anything. It emits text.

    {{2}}
> So where do "it remembers", "it knows our documents", and "it sent the email" come from?
> **From the software around the model.** Every one of them.

--{{0}}--
Start with the narrow, boring, technically correct definition, because everything else
follows from it. It predicts the next piece of text. That is the whole mechanism.

--{{1}}--
Go through the four consequences slowly. The one that surprises people most is the second:
the model genuinely cannot see anything you have not pasted into it. When a product appears
to read your documents, something fetched those documents and pasted them in first.

--{{2}}--
This is the pivot for the whole session. Every capability the room cares about lives outside
the model. That is good news, because outside the model is where you have control.

### The context window is a budget

    {{0}}
Every call has a maximum amount of text it can accept.

    {{1}}
Competing for that space: the instructions, the documents you supply, the conversation so
far, **and the answer**.

    {{2}}
> "Just give it all our documents" fails for an unglamorous reason: **they do not fit.**
> And where they do fit, quality falls as the relevant sentence gets buried.

    {{3}}
So something has to **choose** what goes in. That choosing is the actual engineering.

--{{0}}--
Introduce the budget idea without token arithmetic; the room does not need it.

--{{1}}--
The answer competes with the input for the same space, which is why an assistant given
too much material also gives shorter answers.

--{{2}}--
Somebody in the room will have been told that a large context window removes this problem.
It reduces it. Retrieval quality still dominates, and this is measurable — we measure it
in section four.

--{{3}}--
Set up section two here: selecting what goes into the prompt is the job.

### Section 1 quiz

A colleague says: "we uploaded our policy documents, so the AI has learned them."
What is technically wrong with that sentence?

    [( )] Nothing — that is how it works.
    [(X)] Nothing was learned. The documents sit in a file, and passages are copied into the prompt at question time.
    [( )] The documents must be converted to PDF first.
    [( )] The model would need to be larger.
***********************************************

Uploading documents does not change the model's weights. It creates a searchable collection
that software reads from at question time. The practical consequence is good news: you can
update it in seconds, and you can delete from it.

***********************************************

--{{0}}--
This misconception is worth correcting explicitly, because it drives bad procurement: people
who believe documents are "learned" assume updates are expensive and deletion is impossible.

## Section 2 — Knowledge Bases

### What a knowledge base is

    {{0}}
> A collection of documents **prepared for retrieval**: split into passages, labelled with
> where each came from, and indexed so relevant passages can be found quickly.

    {{1}}
That is all. It is a searchable folder with labels.

    {{2}}
**Three things it is not:**

| People say | Reality |
|---|---|
| "We trained it on our documents" | Nothing was trained |
| "It's the AI's memory" | It is a file, changed only when you rebuild it |
| "It's safe once it's in there" | It is as sensitive as its most sensitive passage |

--{{0}}--
Keep the definition on screen while you say it. Precision here saves an hour of confusion later.

--{{1}}--
Say "it is a searchable folder with labels" out loud. It is the sentence people repeat afterwards.

--{{2}}--
The third row is the governance point. Every passage in the knowledge base is a candidate for
appearing in an answer to whoever is allowed to ask. Retrieval has no concept of permission
unless you build one, and the safe default is one knowledge base per audience.

### The three decisions that decide quality

    {{0}}
1. **Chunking** — what counts as a passage. Too big, the model gets padding; too small,
   it gets a sentence with no context.
2. **Metadata** — what is stored alongside. Without a document name and section you
   cannot cite, and an answer you cannot check is not useful institutionally.
3. **Retrieval** — how a passage is matched to a question.

    {{1}}
> **None of the three involves the language model.**
> Most of the quality of a "document assistant" is decided before any model runs.

    {{2}}
Which is why, in the demo, four of the five programs contain no AI at all.

--{{0}}--
These three decisions are made in `kb_build.py`, which you can open in front of the room —
it is about 200 lines and reads like ordinary code, because it is.

--{{1}}--
This is the second key sentence of the session, after "everything is outside the model".

--{{2}}--
Foreshadow the demo. The count is genuine: make_corpus, anonymise, kb_build and eval_kb call
no model; only ask.py does, in one function.

### Retrieval-augmented generation, in three steps

    {{0}}
```text
       question
          │
          ▼
   (1) RETRIEVE ─── find the passages most likely to be relevant   [no AI]
          │
          ▼
   (2) GROUND ───── build a prompt containing those passages,
          │          numbered, and forbid anything not in them      [the AI]
          ▼
   (3) VERIFY ───── does it cite? do the citations exist?
          │          if not: retry, then refuse                     [no AI]
          ▼
     answer + citations, or an explicit refusal
```

    {{1}}
> Two of the three steps contain no AI — and they are the two that determine whether the
> assistant is trustworthy.

--{{0}}--
Draw this on the whiteboard as you talk if you can. Three boxes, one of which is the model.

--{{1}}--
If people leave with only this diagram, the session has done its job.

### Section 2 quiz

Which of these are decided **without** any language model being involved? (Select all.)

    [[X]] How documents are split into passages
    [[X]] Which passages are put into the prompt
    [[X]] Whether an answer is rejected for citing a source that does not exist
    [[ ]] The wording of the final answer
    [[X]] Whether the assistant refuses because nothing relevant was found
***********************************************

Only the wording comes from the model. Splitting, retrieval, the refusal gate and the citation
check are all ordinary code — which is why they can be inspected, tested and held to a standard.

***********************************************

--{{0}}--
Four of five correct answers, which is the point: the AI does less of the work than people assume.

## Section 3 — Assistants and Agents

### One discriminating question

    {{0}}
> **Who decides what happens next?**

    {{1}}
| | **Assistant** | **Semi-agent** | **Agent** |
|---|---|---|---|
| Decides the next step | you, every turn | a fixed sequence you wrote | the system |
| Takes actions | no | yes, at fixed points | yes, of its own choosing |
| Stops because | you stop asking | the sequence ended | a written rule is satisfied |
| Human checkpoint | every turn | at defined points | at the end, or on exception |

    {{2}}
A system that chooses and acts but has **no written stop condition** is not an agent.
It is an unbounded expense with write access.

--{{0}}--
One question, three answers. This is the cleanest boundary available and it holds up.

--{{1}}--
Point at the semi-agent column and say clearly that it is not a lesser agent. For most
institutional work it is the correct design, because it is auditable and predictable, and
the checkpoint is a genuine control rather than a formality.

--{{2}}--
Say this line as written. It is the sentence that protects a budget.

### Tools: how an agent "does" anything

    {{0}}
The model **never executes anything**. It emits text naming an operation.

    {{1}}
Your code parses that text, **decides whether to allow it**, runs the operation, and pastes
the result back.

    {{2}}
> "The agent can send email" always means: *we wrote code that sends email when the model
> asks for it.*
> The permission is yours to grant — and yours to withhold.

    {{3}}
**The list of tools is the list of things that can go wrong.** Keep it short.

--{{0}}--
This demystifies agents faster than anything else in the deck.

--{{1}}--
Emphasise "decides whether to allow it". In the Part 3 demo the harness overrides the model's
proposed action whenever a precondition is not met, and writes down that it did so.

--{{2}}--
If the room takes one governance point away, this is it.

--{{3}}--
Read-only tools are dramatically safer than write tools. Most useful assistants need only read.

### Section 3 quiz

A supplier demonstrates a system that reads submitted reports, drafts a summary, and emails it
to partners — unattended. What should you ask **first**?

    [( )] Which model does it use?
    [( )] How fast is it?
    [(X)] What is its stop condition, and what does it do when it cannot complete the job?
    [( )] Can it also handle spreadsheets?

***********************************************

Model choice, speed and format coverage are all easier to change later than the absence of a
defined stop condition and a defined failure behaviour. A system that emails partners
unattended and has no defined refusal will, eventually, email something invented.

***********************************************

--{{0}}--
This is the applied question of the deck. If it lands, section three has worked.

## Section 4 — UNEVOC Use Cases and Live Demo

### Four candidate use cases

    {{0}}
| | Pattern | Hardest part | Start? |
|---|---|---|---|
| **Document review** | assistant + checklist | deciding what "review" means | **first** |
| **Knowledge management** | assistant + knowledge base | document preparation, not AI | second |
| **Project monitoring** | semi-agent | telling variance from noise | third |
| **Training development** | semi-agent → agent | assessment design | fourth |

    {{1}}
> **The corpus is the project.** In every one of these, document preparation dominates the
> effort. Institutions that budget for "an AI project" instead of "a document project" run
> out of time in the same place.

--{{0}}--
Full write-ups, including a pilot specification and a stated failure criterion for each, are in
file B of this part. Do not attempt all four on a slide; name them and move to the demo.

--{{1}}--
Start with document review: the tightest feedback loop, the smallest corpus, the clearest
definition of done — and where staff form an accurate intuition fastest.

### The demo — a knowledge assistant over eight documents

    {{0}}
```bash
python make_corpus.py     # eight synthetic documents
python anonymise.py       # scrub identifiers, write a report a human reads
python kb_build.py        # 41 passages, with labels
python ask.py "What evidence counts for quality assurance?" --model llama3.1:8b
```

    {{1}}
Then the important one:

```bash
python ask.py "What is the capital city of Peru?" --model llama3.1:8b
```

    {{2}}
> It refuses. **And it refuses before calling the model at all**, because the question's words
> do not appear in anything retrieved.

--{{0}}--
Run this live. Open `kb.json` in a text editor first and scroll it — seeing that the knowledge
base is plainly readable text does more than any explanation.

--{{1}}--
Set the Peru question up as a test of the system rather than a joke. Ask the room to predict
what it will do.

--{{2}}--
Three independent layers can produce a refusal here: the retrieval gate before any model call,
the model's own insufficient-evidence signal, and the citation check afterwards. Walk through
`ask_log.md` and show which one fired.

### Measuring it instead of admiring it

    {{0}}
```bash
python eval_kb.py --model llama3.1:8b
```

    {{1}}
Three numbers, reported separately:

| | |
|---|---|
| **Retrieval hit rate** | did the right document reach the prompt? |
| **Answered when expected** | covered questions got an answer |
| **Refused when expected** | uncovered questions were declined, not invented |

    {{2}}
> A single blended "accuracy" figure hides which one broke.
> The refusal number is the one vendors do not publish — **ask for it.**

--{{0}}--
"It gave a good answer when I tried it" is not evidence. This slide is the professional standard
being proposed.

--{{1}}--
If retrieval hit rate is low, no model can fix it. That single diagnostic saves more money than
anything else in the deck.

--{{2}}--
Twelve questions is a demonstration. Thirty to fifty real questions collected from staff before
anything is built is a pilot — and collecting them first prevents building an assistant for
questions nobody asks.

### What we did with the documents

    {{0}}
The demo corpus is **synthetic** — written for this session. No real policy, no real project
data, no real people.

    {{1}}
One document contains invented names, emails and phone numbers, so `anonymise.py` has something
to remove in front of you. Every replacement is listed in a report.

    {{2}}
> **It is a redaction aid, not a compliance tool.** It cannot find names it was not told about,
> and it cannot remove indirect identifiers at all — *"the only welding instructor at partner C"*
> names a person and contains no name.

    {{3}}
A human reads the report before anything is indexed. The tool narrows what you look for.
It does not replace you.

--{{0}}--
Say this plainly. Overstating what the scrubber does would be the worst possible outcome of
this session.

--{{2}}--
Give the indirect-identifier example verbatim. It lands, and people remember it.

--{{3}}--
For live sessions, prefer documents that are already public. Use the scrubber on internal
material only when someone with authority over that material has signed off on the result.

### Closing quiz

**1.** A knowledge base is:

    [( )] A model trained on your documents.
    [(X)] A collection of documents split into passages, labelled and indexed for retrieval.
    [( )] The conversation history of the assistant.
    [( )] A type of database that only AI can read.

**2.** Which is decided **without** any language model?

    [( )] The wording of the answer
    [(X)] Which passages are retrieved and put into the prompt
    [( )] Nothing — the model does everything
    [( )] Only the user interface

**3.** What makes something an agent rather than an assistant? (Select all that apply.)

    [[X]] It chooses its own next action
    [[X]] Its choices cause things to happen
    [[X]] It stops on a written, checkable rule
    [[ ]] It uses a larger model
    [[ ]] It runs in the cloud

**4.** Your assistant answers every question confidently, including ones your documents do not
cover. What is missing?

    [( )] A larger model
    [( )] More documents
    [(X)] A defined refusal — a retrieval gate, and a check that rejects answers whose citations do not resolve
    [( )] A better user interface

**5. Applied.** You are asked to choose one pilot for next year. Which factor should weigh
most heavily in the choice?

    [( )] Which use case sounds most impressive to funders.
    [( )] Which one uses the newest model.
    [(X)] Which one has criteria already written down and a machine-checkable definition of done.
    [( )] Which one involves the most documents.

***********************************************

Question five is the session in one decision. Written criteria and a checkable definition of
done are what make a pilot capable of succeeding *or failing informatively*. Everything else —
model, scale, interface — is easier to change afterwards. The scoring worksheet in file C turns
this into ten questions you can score in the room.

***********************************************

--{{0}}--
Questions one to four are recall; five is applied. If you are short of time, ask five alone.

### Further reading

    {{0}}
- **File A** — precise definitions of all eleven terms used today
- **File B** — the four use cases in full, with pilot specifications and failure criteria
- **File C** — a ten-question scoring worksheet for choosing a pilot
- **demo_assistant/README.md** — what you just watched, explained line by line

    {{1}}
- UNESCO AI competency framework for teachers (2024) —
  15 competencies, five aspects, levels **Acquire / Deepen / Create**
  <https://www.unesco.org/en/articles/ai-competency-framework-teachers>
- UNESCO AI competency framework for students (2024) —
  12 competencies, four dimensions, levels **Understand / Apply / Create**
  <https://www.unesco.org/en/articles/ai-competency-framework-students>
- Meta-Harness (Lee, Nair, Zhang, Lee, Khattab & Finn, COLM 2026) —
  <https://yoonholee.com/meta-harness/>
- Learn Harness Engineering (Walking Labs) —
  <https://walkinglabs.github.io/learn-harness-engineering/en/>

    {{2}}
> **UNESCO alignment.** Sections 1–2 are *Acquire*-level work under the teachers' framework
> (aspect: AI foundations and applications) — understanding what an AI system is composed of
> well enough to evaluate tools rather than accept them. Section 3 is *Deepen*. Section 4,
> and specifically deciding what your own system must refuse to do, is *Create*. For students
> the same content maps to *AI techniques and applications* at Understand → Apply.

--{{1}}--
All four sources are freely accessible and were read in full when this material was prepared.

--{{2}}--
Note for anyone adapting this deck: LiaScript single choice uses round brackets, `[( )]` and
`[(X)]`; multiple choice uses square brackets, `[[ ]]` and `[[X]]`. Some summaries state this the
other way round. What is in this file is the working syntax — render it at liascript.github.io
to confirm before editing.
