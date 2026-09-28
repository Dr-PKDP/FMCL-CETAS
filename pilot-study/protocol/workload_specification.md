# Computational Workload Specification

## Overview

The pilot workload is CPU-dominant local supervised training of a fully connected neural network on deterministic synthetic multiclass data. It was designed to generate reproducible computational demand across Android devices without invoking device-specific GPU, NPU, network-transfer, or persistent-storage stress components.

## Machine-learning task

The application trains a single-hidden-layer, fully connected multiclass classifier. For each sample, it performs:

1. Input-to-hidden affine transformation.
2. Rectified linear unit activation.
3. Hidden-to-output affine transformation to obtain class logits.
4. Softmax normalization to obtain class probabilities.
5. Cross-entropy loss evaluation.
6. Manual backpropagation for gradient computation.
7. Mini-batch gradient-descent parameter updates.

At the end of each completed training round, it evaluates mean cross-entropy loss, classification accuracy, and the L2 norm of the parameter update relative to the model initialization for that round.

## Workload configurations

| Parameter | Compact | High |
|---|---:|---:|
| Synthetic samples | 2,000 | 8,000 |
| Input features | 32 | 64 |
| Hidden-layer units | 32 | 64 |
| Output classes | 4 | 4 |
| Mini-batch size | 32 | 32 |
| Local epochs per round | 5 | 10 |
| Training volume per round | 10,000 example-epochs | 80,000 example-epochs |
| Trainable parameters | 1,188 | 4,484 |
| Learning rate | 0.015 | 0.015 |

High workload intensity is created jointly by increasing dataset size, feature dimension, hidden-layer width, and local epochs per completed round.

## Determinism and initialization

Synthetic features are generated from Gaussian random values. Labels are assigned using noisy linear logits generated from Gaussian-distributed latent weights and maximum-logit class selection.

Dataset construction uses a deterministic seed of `20260919 + feature_count`. The model is reinitialized at the beginning of each completed training round using `700000 + round_index`; model state does not accumulate across rounds.

## Execution model

The computation runs in one Kotlin background thread. The implementation does not define explicit processor affinity, core pinning, or an application-level worker pool. Physical-core selection and scheduling are controlled by the Android operating system.

The workload configuration does not adapt to battery level, battery temperature, charger state, CPU frequency, or observed telemetry values.

## Execution policies

### Continuous

The application repeatedly executes completed training rounds without planned pauses until it is stopped.

### Duty cycle

The duty-cycle controller uses a 90-s period:

- Active phase: 60,000 ms of repeated local-training rounds.
- Pause phase: 30,000 ms in which no new training round is initiated.

During pause phases, the worker repeatedly calls `Thread.sleep(200)` until the 30-s interval expires. The resulting active fraction is 66.7%. A requested 900-s run contains ten nominal duty cycles.

The application emits `DUTY_ACTIVE`, `DUTY_PAUSE`, and `DUTY_RESUME` events with workload, policy, cycle number, and planned phase duration.

## Source provenance

The protocol-defining implementation was retained as an archived versioned duty-cycle source release. Its SHA-256 digest is:

```text
9C63F7B469D8361741EFBC6F35A887CB120192F2C6AF0145FF84EF903182DDCB
```
