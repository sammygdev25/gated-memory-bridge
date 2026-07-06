# A Gated Architecture for Safe Cross-Session Memory in AI Coding Agents

**Sam Gurung** · ArtixNature Lab, San Francisco, CA · July 2026

📄 **[Read the paper (PDF)](paper/gated-memory-bridge-v1.pdf)** · Status: **Preprint, v1 (July 2026)**

## TL;DR

AI coding agents contain two subsystems with conflicting context requirements: a conversational pipeline that benefits from broad memory, and a code-generation pipeline that requires narrow, precise context. Passing conversational memory to the generator unfiltered risks **context poisoning**: irrelevant, stale, or contradictory signals corrupting generated code. This is the failure mode that preceded Cursor's withdrawal of its automatic Memories feature.

We propose the **gated memory bridge** (the "Memory PR" model): conversational memory is the feature branch, generation context is main, and information crosses only as **typed, content-constrained, provenance-verified proposals** that pass **confidence-tiered review gates**. We implement the extraction and validation layers in a production system (Shikshya v2) and evaluate them.

## Key findings

| Finding | Result |
|---|---|
| Extraction precision / required recall / provenance | 100% each, across 18 runs on 6 synthetic sessions (zero noise leakage) |
| **Proposer–reviewer conflict** | The extractor assigned the prohibited auto-approve tier in **20 of 25 restricted-type instances (80%)**, including **all 15** high-risk `tech_decision` instances (0% raw tier accuracy) |
| Deterministic tier enforcement | Raised overall tier accuracy **35.5% → 93.5% (+58.1 pp)** |
| Context poisoning at small scale | **Two pre-registered null results**: not reproducible in short synthetic histories; risk may emerge with accumulated history |
| Token economy | **8.6× smaller** generation context vs. naive transcript dumping; gap widens with history |
| Supersession | Topic-scoped, approval-time supersession verified, including the same-session exclusion rule |

The headline is not the 100% precision. It is that the model **understood the user's decisions but could not be trusted to assess the authority its own extractions deserved**: the proposing model should not be the sole authority over the privilege its proposals receive.

## Repository layout

```
paper/
  gated-memory-bridge-v1.pdf     # the paper (v1 preprint)
  source/                        # editable source (docx)
supplementary/
  README.md                      # manifest of evaluation materials
  (eval scripts + raw JSON outputs; see manifest)
```

Full test-session transcripts, ground-truth labels, scoring tables, the supersession trace, and the prompt-iteration log are included as Appendices B–G **inside the paper itself**. The `supplementary/` directory carries the machine-readable raw outputs and evaluation scripts.

## Citation

```bibtex
@misc{gurung2026gatedmemory,
  title   = {A Gated Architecture for Safe Cross-Session Memory in AI Coding Agents},
  author  = {Gurung, Sam},
  year    = {2026},
  month   = {July},
  note    = {Preprint},
  url     = {https://github.com/USERNAME/gated-memory-bridge}
}
```

(The canonical citation will be updated here if and when an archival identifier is assigned.)

## License

The paper, appendices, and supplementary data are released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The Shikshya v2 production system described in the paper is proprietary and not part of this repository.

## Contact

admin@shikshya.ai
