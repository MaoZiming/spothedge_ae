# SpotHedge

This repository contains the code and instructions used in our EuroSys 25' paper: SpotHedge: Serving AI Models on Spot Instances.

## Abstract

Recent years have witnessed an explosive growth of AI models. The high cost of hosting AI services on GPUs and their demanding service requirements, make it timely and challenging to lower service costs and guarantee service quality. While spot instances have long been offered with a large discount, spot preemptions have discouraged users from using them to host model replicas when serving AI models.

To address this, we propose a simple yet efficient policy, SpotHedge, that leverages spot replicas across different failure domains (e.g., regions and clouds) to ensure availability, lower costs, and high service quality. SpotHedge intelligently spreads spot replicas across different failure domains (e.g., regions or clouds) to improve availability and reduce correlated preemptions, overprovisions cheap spot replicas than required as a safeguard against possible preemptions, and dynamically falls back to on-demand replicas when spot replicas become unavailable. We built a system leveraging SpotHedge to efficiently serve AI models over a mixture of spot and on-demand replicas across regions and clouds. We compared SpotHedge with both research and production systems on real AI workloads: SpotHedge reduces cost by up to 44% while achieving high resource availability compared to using on-demand replicas. Additionally, SpotHedge improves P50, P90, and P99 latency by up to 2.6×, 3.1×, and 2.7× compared to other research and production systems.

## Folder structure

- `eval/`: Contains the evaluation scripts.
- `results/`: Contains the results of the evaluation.
- `policies/`: Contains the policies used in the evaluation, as well as code to simulate autoscaler, scheduler and workload loader.
- `workloads/`: Contains the workloads used in the evaluation.
  - Arena Trace
  - MAF trace
- `data/`: Contains the Spot preemption trace used in the microbenchmarks.
  - AWS 1: A 2-week trace for 4 p3.2xlarge in 3 zones.
  - AWS 2: A 3-week trace for 16 p3.2xlarge in 3 zones.
  - AWS 3: A 2-month trace for p3.2xlarge in 9 zones.
  - GCP 1: A 3-day trace for a2-ultragpu-4g in 6 zones.
- `e2e/`: Contains the end-to-end evaluation scripts.

## Preparation

The SkyServe and SpotHedge related code is available on [SkyPilot](https://github.com/skypilot-org/skypilot/tree/spot-hedge-new).

To install from source, follow [Installation](https://docs.skypilot.co/en/latest/getting-started/installation.html).

## Macrobenchmarks

All scripts to reproduce the figures in Macrobenchmarks are in `e2e/plot/`.

Artifact evaluators can reproduce all figures by following those steps:

```bash
cd e2e/plot

# Decompress the data zip file.
unzip spot-hedge-ae-raw-data.zip

# Run the scripts to generate figures.
python3 draw-misc.py            # Figure 6
python3 draw-latency.py         # Figure 9(a-d), Figure 12(a-d)
python3 draw-cost-and-trace.py  # Figure 9(e-f), Figure 10, Figure 11, Figure 12(e-f)
```

## Microbenchmarks

To run microbenchmark experiments, run:

```bash
mkdir results
sky launch eval/run_eval.yaml
```

See results in `results/` directory.

## Person of contact

- Ziming Mao (ziming.mao@berkeley.edu)
- Tian Xia (tianxia@berkeley.edu)