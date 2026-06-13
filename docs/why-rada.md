# Why RADA?

RADA is built for decision-heavy systems where a raw model response is not enough. The system around the model matters just as much as the model itself.

## What It Optimizes For

RADA is designed to make every decision:

- auditable after the fact
- constrained by explicit risk checks
- reviewable by an operator when confidence is low or policy requires it
- exportable into evaluation, reflection, and training loops

That makes it a better fit for operational decisioning than a thin LLM wrapper.

## Core Library and Showcase

RADA ships as both:

- a **core library** under `src/rada/` for teams extending reasoners, policies, schemas, audit trails, and storage
- a **standalone showcase** with API, dashboards, scripts, configs, and runbooks that demonstrate a complete deployment shape

This split is intentional. You can either embed the library inside a larger platform or run the repository itself as a working reference implementation.

## Reasoner Strategy

Runtime defaults to a real local reasoner through Ollama and Qwen. BYOK cloud routing is available through the OpenAI-compatible LiteLLM path. Tests and CI continue to use mock mode so validation stays deterministic and inexpensive.

## Why This Shape Works

RADA separates hot-path decisioning from off-path learning workflows. It keeps auditability close to the runtime, preserves operator intervention points, and treats model portability as a first-class requirement instead of an afterthought.