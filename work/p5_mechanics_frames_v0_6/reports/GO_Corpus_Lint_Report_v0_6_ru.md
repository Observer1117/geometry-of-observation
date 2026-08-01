# GO Core v0.2 — отчёт линтера по корпусу

Статус этого отчёта: машинный аудит типизированных ledgers. Для старых PDF использованы адаптеры критических формул; это не полное синтаксическое доказательство корректности каждой формулы.

## Сводка

- канонических документов: 18;
- полных эталонных ledgers: 12;
- адаптеров критических формул: 6;
- проверенных выражений: 132;
- всех находок: 18;
- статусы: `{'FAIL': 6, 'PASS': 12}`.

## Статусы документов

| Документ | Ledger | Выражения | Auto | Review | Ошибки | Блокеры | Статус |
|---|---:|---:|---:|---:|---:|---:|---:|
| `functional-interface-go-qs-v0-2` | reference | 3 | 0 | 0 | 0 | 0 | **PASS** |
| `tensorial-observation-geometry-gr-v0-3` | reference | 2 | 0 | 0 | 0 | 0 | **PASS** |
| `information-theoretic-observation-v0-2` | reference | 9 | 0 | 0 | 0 | 0 | **PASS** |
| `metric-entropy-defect-v0-2` | reference | 13 | 0 | 0 | 0 | 0 | **PASS** |
| `distance-scale-interface-v0-2` | reference | 12 | 0 | 0 | 0 | 0 | **PASS** |
| `planck-cosmos-rulers-v1-1` | reference | 19 | 0 | 0 | 0 | 0 | **PASS** |
| `mandelbrot-rulers-v1-1` | reference | 12 | 0 | 0 | 0 | 0 | **PASS** |
| `regular-polyhedra-v1` | critical_adapter | 0 | 1 | 1 | 1 | 1 | **FAIL** |
| `satellite-networks-v1-1` | critical_adapter | 1 | 2 | 1 | 1 | 1 | **FAIL** |
| `frames-forces-dissipation-interface-v0-1` | reference | 10 | 0 | 0 | 0 | 0 | **PASS** |
| `celestial-foucault-networks-v1-1` | reference | 7 | 0 | 0 | 0 | 0 | **PASS** |
| `billiards-observation-v1` | critical_adapter | 2 | 3 | 0 | 2 | 1 | **FAIL** |
| `bobsleigh-contact-v1-1` | reference | 11 | 0 | 0 | 0 | 0 | **PASS** |
| `roller-coaster-v1-1` | reference | 11 | 0 | 0 | 0 | 0 | **PASS** |
| `gear-contact-v1` | critical_adapter | 1 | 1 | 2 | 1 | 1 | **FAIL** |
| `conical-intersections-v1` | critical_adapter | 1 | 2 | 2 | 1 | 1 | **FAIL** |
| `quantum-chemistry-observation-v1` | critical_adapter | 2 | 2 | 1 | 2 | 1 | **FAIL** |
| `lhc-beam-observation-v1-3` | reference | 16 | 0 | 0 | 0 | 0 | **PASS** |

## Находки по правилам

- `CAUSTIC-RANK`: 1
- `COVERAGE-INCOMPLETE`: 6
- `DUPLICATE-SOURCE`: 1
- `EIGENBUNDLE-GAUGE`: 1
- `FILTER-ORDER`: 1
- `FRAME-COVERAGE`: 1
- `FRAME-LAW`: 1
- `GEAR-GAUGE`: 1
- `LOG-BASE`: 1
- `RESULT-DIM`: 2
- `ROTATION-NUMBER-SCOPE`: 1
- `ZERO-MODES`: 1

## Детальная карта исправлений

### Functional Interface GO-QS (0.2.0)

Статус: **PASS**. Следующее действие: retain_as_core_reference

- Нарушений не найдено в заявленном покрытии.

### Tensorial Observation Geometry in GR (0.3.0)

Статус: **PASS**. Следующее действие: retain_as_tensor_reference

- Нарушений не найдено в заявленном покрытии.

### Information-Theoretic Observation Geometry (0.2.0)

Статус: **PASS**. Следующее действие: retain_as_information_reference_and_migrate_downstream_probabilistic_modules

- Нарушений не найдено в заявленном покрытии.

### Metric Entropy and Observational Entropy Defect (0.2.0)

Статус: **PASS**. Следующее действие: retain_as_metric_scale_reference_and_migrate_distance_and_mechanics_modules

- Нарушений не найдено в заявленном покрытии.

### Distance and Scale Interface under Observation Maps (0.2.0)

Статус: **PASS**. Следующее действие: retain_as_common_distance_scale_reference_and_migrate_planck_cosmos

- Нарушений не найдено в заявленном покрытии.

### Planck-to-Cosmos Observation Rulers (1.1.0)

Статус: **PASS**. Следующее действие: retain_as_planck_cosmos_scale_reference_and_migrate_application_modules

- Нарушений не найдено в заявленном покрытии.

### Mandelbrot Rulers as Observation-Scale Geometry (1.1.0)

Статус: **PASS**. Следующее действие: retain_as_scale_trace_reference_and_migrate_planck_cosmos

- Нарушений не найдено в заявленном покрытии.

### Regular Polyhedra as Observation-Dependent Classification (1.0.0)

Статус: **FAIL**. Следующее действие: define_category_of_objects_and_preorder_of_observation_filters

- `BLOCKER` `COVERAGE-INCOMPLETE` (AUTO): critical-formula adapter is not complete enough for a P1 pass
- `ERROR` `FILTER-ORDER` (REVIEW) [text lines 278-286: O1 subset O2]: O=(A,R,Q) is a tuple, but the partial order O1<=O2 and its variance in A,R,Q are not defined

### Satellite Networks as Nested Observation Geometry (1.1.0)

Статус: **FAIL**. Следующее действие: restrict_invariant_claims_to_declared_group_and_type_orbit_closure_as_protocol_dependent

- `BLOCKER` `COVERAGE-INCOMPLETE` (AUTO): critical-formula adapter is not complete enough for a P1 pass
- `ERROR` `FRAME-LAW` (AUTO) [text lines 310-365]: observer_frame_orbit_closure is called invariant without a declared transformation group
- `WARNING` `FRAME-COVERAGE` (REVIEW) [sections 1.2 and 1.9]: the proved frame law covers common translations, not the full SE(3) or Lorentz observer class used elsewhere in the narrative

### Frames, Forces, Constraints, and Dissipation under Observation Maps (0.1.0)

Статус: **PASS**. Следующее действие: retain_as_common_mechanics_reference

- Нарушений не найдено в заявленном покрытии.

### Foucault Networks on Celestial Bodies (1.1.0)

Статус: **PASS**. Следующее действие: retain_as_frame_consistent_celestial_toy_reference

- Нарушений не найдено в заявленном покрытии.

### Billiards as Geometry of Observation (1.0.0)

Статус: **FAIL**. Следующее действие: rename_E_n_to_lambda_n_or_apply_hbar_squared_over_2m_energy_bridge

- `BLOCKER` `COVERAGE-INCOMPLETE` (AUTO): critical-formula adapter is not complete enough for a P1 pass
- `ERROR` `RESULT-DIM` (AUTO) [text lines 265-276: -Delta psi_n=E_n psi_n]: result has L^-2, expected L^2 M^1 T^-2
- `ERROR` `LOG-BASE` (AUTO) [text lines 249-255: H=-sum p_j log p_j]: logarithm lacks an explicit base

### Bobsleigh Contact Geometry as a Typed Observation System (1.1.0)

Статус: **PASS**. Следующее действие: retain_as_typed_contact_observation_reference

- Нарушений не найдено в заявленном покрытии.

### Roller-Coaster Geometry as a Typed Observation Laboratory (1.1.0)

Статус: **PASS**. Следующее действие: retain_as_framed_curve_observation_reference

- Нарушений не найдено в заявленном покрытии.

### Gear Contact Geometry as a Minimal Laboratory for Observation Invariants (1.0.0)

Статус: **FAIL**. Следующее действие: define_carrier_frame_action_and_precise_non_circular_return_map

- `BLOCKER` `COVERAGE-INCOMPLETE` (AUTO): critical-formula adapter is not complete enough for a P1 pass
- `ERROR` `GEAR-GAUGE` (REVIEW) [text lines 290-306 and 581-594]: subtracting carrier angular velocity is a frame change; calling it gauge requires an explicit group action and quotient
- `WARNING` `ROTATION-NUMBER-SCOPE` (REVIEW) [text lines 321-334]: non-circular rotation number is invoked without defining the return map, invariant measure, or lift

### Conical Intersections as Observation Caustics (1.0.0)

Статус: **FAIL**. Следующее действие: replace_global_eigenvector_output_by_projector_or_eigenline_bundle

- `BLOCKER` `COVERAGE-INCOMPLETE` (AUTO): critical-formula adapter is not complete enough for a P1 pass
- `ERROR` `EIGENBUNDLE-GAUGE` (REVIEW) [map (3) and equations (13)-(14), text lines 156-166 and 212-237]: the global output cannot be a single eigenvector map; it must be an eigenprojector or a local section of the eigenline bundle
- `WARNING` `CAUSTIC-RANK` (REVIEW) [equation (18), text lines 268-276]: det DF is valid only for the stated square two-dimensional chart; the reusable core criterion must be rank loss
- `WARNING` `DUPLICATE-SOURCE` (AUTO): upload/conical_intersections_observation_caustics_v1_bilingual (1)(2).pdf duplicates upload/conical_intersections_observation_caustics_v1_bilingual.pdf

### Quantum Chemistry through Geometry of Observation (1.0.0)

Статус: **FAIL**. Следующее действие: replace_lambda_by_omega_squared_take_square_roots_and_quotient_rigid_modes

- `BLOCKER` `COVERAGE-INCOMPLETE` (AUTO): critical-formula adapter is not complete enough for a P1 pass
- `ERROR` `RESULT-DIM` (AUTO) [text lines 360-370: vibrational frequencies are eigenvalues of the mass-weighted Hessian]: result has T^-2, expected T^-1
- `ERROR` `ZERO-MODES` (REVIEW) [equations (6)-(7) and spectroscopy section]: Hessian positivity and the one-negative-mode criterion must be stated after removing 5 or 6 rigid translation/rotation zero modes

### Relativistic Beam Paths as Observation Geometry (1.3.0)

Статус: **PASS**. Следующее действие: use_as_reference_accelerator_module_and_migrate_remaining_mechanical_applications

- Нарушений не найдено в заявленном покрытии.

## Интерпретация шлюза

- `PASS` означает прохождение зарегистрированного P0/P1-контракта.
- `FAIL` означает обнаруженную формульную, типовую, кадровую или семантическую ошибку.
- `BLOCKED` означает, что критические примеры не дали ошибки, но покрытие старого PDF недостаточно для строгого P1-pass.
- `REVIEW` означает отсутствие ошибок и блокеров при наличии нефатальных замечаний.
