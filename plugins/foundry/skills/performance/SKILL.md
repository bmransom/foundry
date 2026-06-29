---
name: performance
description: Use when designing, implementing, reviewing, or validating performance-sensitive work; benchmarking, baselining, profiling, tracing, logging, resource analysis, latency, throughput, memory, CPU, IO, cost, scaling, regressions, or comparing main vs feature, flag-off vs flag-on, old vs new, prior vs current, or local vs reference behavior.
---

# Performance

Treat performance as an SDLC check. Preserve a fair baseline, measure comparable
work, then explain confirmed gaps with evidence.

Use this during spec, plan, build, review, or verify when a change touches a hot
path, algorithm, storage shape, concurrency, caching, IO, model/tool calls,
resource use, or user-visible latency.

## Lifecycle Gates

- **Spec:** name the performance-sensitive path, expected risk, and baseline.
- **Plan:** define the workload, correctness gate, environment, metrics, and stop condition.
- **Build:** keep the baseline runnable; hide diagnostic logging behind flags.
- **Verify:** run representative measurements with enough warmup/repetition to expose noise.
- **Review:** accept causes only after counters, logs, traces, profilers, or source explain them.

## Baselines

Choose the fairest baseline that answers the product question:

- main vs feature branch;
- flag-off vs flag-on;
- old algorithm vs replacement algorithm;
- previous release vs current release;
- same implementation before vs after the feature;
- local implementation vs external reference, library, service, or competitor;
- no-feature path vs feature path when measuring the cost of adding a feature.

Do not compare "new code with extra work" against "old code doing less work"
without naming the extra work and normalizing the metric.

## Benchmarking

1. State the decision the benchmark will change.
2. Establish the common input contract: workload, data version, config class,
   machine, limits, concurrency, and correctness/quality gate.
3. Use production-faithful entrypoints for headline results; label diagnostic shortcuts.
4. Capture wall time plus work units and per-unit cost: throughput, time per unit,
   success/failure, correctness/quality, CPU, memory, IO, network, and spend.
5. Run enough warmup and repetitions to identify variance; record raw run data.
6. Split the gap into work-count factor, per-unit factor, and unmapped work such
   as setup, cleanup, retries, fallback paths, allocation, scheduling, or post-processing.

## Profiling And Attribution

Use profilers after confirming a fair gap, not as the headline benchmark.

- Start resource-first: CPU, memory, disk, network, locks, queues, external calls,
  utilization, saturation, and errors.
- Prefer existing counters and logs; add trace/log points only where they answer a
  named question.
- Build or patch dependencies when source-level evidence is needed; keep patches
  minimal and reversible.
- Read load-bearing source lines before naming the mechanism. Data points to a
  region; code explains why.

## Repo Workspace

When invoked in a repo, create or use `performance/` unless the repo has a
stronger convention:

```text
performance/
  README.md
  <topic-or-date>/
    plan.md
    runs/
    metrics.csv
    report.md
```

Keep raw logs, profiler captures, traces, and generated metrics in
`performance/<topic-or-date>/runs/`.

## Report Shape

```markdown
# <topic> Performance

## Question
Decision this measurement supports.

## Common Contract
Workload, correctness gate, config, machine, limits, and commands.

## Baseline And Candidate
Status, wall time, work units, per-unit metric, resources, and notes.

## Attribution
Count factor, per-unit factor, mapped regions, unmapped work, counters, traces,
profiler output, logs, and source citations.

## Caveats And Next Actions
Noise, instrumentation overhead, skipped workloads, ranked changes, or stop condition.
```

## Traps

- Do not compare different inputs, hidden defaults, or different production paths.
- Do not average over confounds; explain or exclude them.
- Do not infer causes from black-box wall time when evidence is available.
- Do not trust one surprising run until it reproduces through the production path.
