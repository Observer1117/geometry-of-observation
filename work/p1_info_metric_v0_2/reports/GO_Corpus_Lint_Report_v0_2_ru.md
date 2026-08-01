# GO Core v0.2 — отчёт линтера по корпусу

Статус этого отчёта: машинный аудит типизированных ledgers. Для старых PDF использованы адаптеры критических формул; это не полное синтаксическое доказательство корректности каждой формулы.

## Сводка

- канонических документов: 17;
- полных эталонных ledgers: 4;
- адаптеров критических формул: 13;
- проверенных выражений: 51;
- всех находок: 40;
- статусы: `{'BLOCKED': 2, 'FAIL': 11, 'PASS': 4}`.

## Статусы документов

| Документ | Ledger | Выражения | Auto | Review | Ошибки | Блокеры | Статус |
|---|---:|---:|---:|---:|---:|---:|---:|
| `functional-interface-go-qs-v0-2` | reference | 3 | 0 | 0 | 0 | 0 | **PASS** |
| `tensorial-observation-geometry-gr-v0-3` | reference | 2 | 0 | 0 | 0 | 0 | **PASS** |
| `information-theoretic-observation-v0-2` | reference | 9 | 0 | 0 | 0 | 0 | **PASS** |
| `metric-entropy-defect-v0-2` | reference | 13 | 0 | 0 | 0 | 0 | **PASS** |
| `unit-distances-observation-v0-1` | critical_adapter | 2 | 3 | 1 | 3 | 1 | **FAIL** |
| `planck-cosmos-rulers-v1` | critical_adapter | 3 | 1 | 1 | 0 | 2 | **BLOCKED** |
| `mandelbrot-rulers-v1` | critical_adapter | 3 | 3 | 1 | 3 | 1 | **FAIL** |
| `regular-polyhedra-v1` | critical_adapter | 0 | 1 | 1 | 1 | 1 | **FAIL** |
| `satellite-networks-v1-1` | critical_adapter | 1 | 2 | 1 | 1 | 1 | **FAIL** |
| `celestial-foucault-networks-v1` | critical_adapter | 2 | 2 | 0 | 1 | 1 | **FAIL** |
| `billiards-observation-v1` | critical_adapter | 2 | 3 | 0 | 2 | 1 | **FAIL** |
| `bobsleigh-contact-v1` | critical_adapter | 3 | 3 | 1 | 3 | 1 | **FAIL** |
| `roller-coaster-v1` | critical_adapter | 2 | 2 | 2 | 2 | 1 | **FAIL** |
| `gear-contact-v1` | critical_adapter | 1 | 1 | 2 | 1 | 1 | **FAIL** |
| `conical-intersections-v1` | critical_adapter | 1 | 2 | 2 | 1 | 1 | **FAIL** |
| `quantum-chemistry-observation-v1` | critical_adapter | 2 | 2 | 1 | 2 | 1 | **FAIL** |
| `lhc-beam-observation-v1-2` | critical_adapter | 2 | 1 | 1 | 0 | 2 | **BLOCKED** |

## Находки по правилам

- `ADD-DIM`: 1
- `ADD-FRAME`: 1
- `CAUSTIC-RANK`: 1
- `COMPARE-DIM`: 1
- `COVERAGE-INCOMPLETE`: 13
- `DUPLICATE-SOURCE`: 1
- `EIGENBUNDLE-GAUGE`: 1
- `FILTER-ORDER`: 1
- `FRAME-COVERAGE`: 1
- `FRAME-LAW`: 2
- `FRICTION-SIGN`: 1
- `GEAR-GAUGE`: 1
- `GLOBAL-PSEUDOMETRIC`: 1
- `LOG-BASE`: 2
- `LOG-DIM`: 2
- `REACH-CONDITION`: 1
- `REGRESSION-WINDOW`: 1
- `RESULT-DIM`: 2
- `ROTATION-NUMBER-SCOPE`: 1
- `SCALE-PROTOCOL-SEPARATION`: 1
- `UNIT-PASSPORT`: 1
- `VECTOR-NORM`: 1
- `ZERO-DENOMINATOR`: 1
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

### Unit Distances under Observation Maps (0.1.0)

Статус: **FAIL**. Следующее действие: introduce_reference_shell_radius_and_global_observed_pseudometric

- `BLOCKER` `COVERAGE-INCOMPLETE` (AUTO): critical-formula adapter is not complete enough for a P1 pass
- `ERROR` `COMPARE-DIM` (AUTO) [text lines 55-63 and 95: d(pi(x),pi(y)) = 1]: comparison mixes L^1 and 1
- `ERROR` `ADD-DIM` (AUTO) [text lines 201-212: d_n = d_0 + n/2]: add mixes L^1 and 1
- `ERROR` `GLOBAL-PSEUDOMETRIC` (REVIEW) [section 6, text lines 255-282]: the pullback tensor is local; the global observed pseudometric d_pi(x,x')=d_Y(pi x,pi x') is not registered

### Planck–Cosmos Observation Rulers (1.0.0)

Статус: **BLOCKED**. Следующее действие: split_intrinsic_scale_descriptor_from_observation_resolution_protocol

- `BLOCKER` `COVERAGE-INCOMPLETE` (AUTO): critical-formula adapter is not complete enough for a P1 pass
- `BLOCKER` `SCALE-PROTOCOL-SEPARATION` (REVIEW) [sections 7-8, text lines 304-340]: intrinsic object scales and instrument resolutions occupy the same coordinates without separate xi and lambda passports

### Mandelbrot’s Rulers as Observation-Scale Geometry (1.0.0)

Статус: **FAIL**. Следующее действие: replace_log_epsilon_by_log_reference_ratio_and_add_regression_uncertainty

- `BLOCKER` `COVERAGE-INCOMPLETE` (AUTO): critical-formula adapter is not complete enough for a P1 pass
- `ERROR` `LOG-DIM` (AUTO) [text lines 157-162: log(1/epsilon)]: log argument has dimension L^1
- `ERROR` `LOG-DIM` (AUTO) [text lines 206-211: Delta log(1/epsilon)]: log argument has dimension L^1
- `ERROR` `REGRESSION-WINDOW` (REVIEW) [section 4, text lines 180-211]: finite-scale exponent lacks a mandatory fit window, weighting rule, and confidence interval

### Regular Polyhedra as Observation-Dependent Classification (1.0.0)

Статус: **FAIL**. Следующее действие: define_category_of_objects_and_preorder_of_observation_filters

- `BLOCKER` `COVERAGE-INCOMPLETE` (AUTO): critical-formula adapter is not complete enough for a P1 pass
- `ERROR` `FILTER-ORDER` (REVIEW) [text lines 278-286: O1 subset O2]: O=(A,R,Q) is a tuple, but the partial order O1<=O2 and its variance in A,R,Q are not defined

### Satellite Networks as Nested Observation Geometry (1.1.0)

Статус: **FAIL**. Следующее действие: restrict_invariant_claims_to_declared_group_and_type_orbit_closure_as_protocol_dependent

- `BLOCKER` `COVERAGE-INCOMPLETE` (AUTO): critical-formula adapter is not complete enough for a P1 pass
- `ERROR` `FRAME-LAW` (AUTO) [text lines 310-365]: observer_frame_orbit_closure is called invariant without a declared transformation group
- `WARNING` `FRAME-COVERAGE` (REVIEW) [sections 1.2 and 1.9]: the proved frame law covers common translations, not the full SE(3) or Lorentz observer class used elsewhere in the narrative

### Foucault Networks on Celestial Bodies (1.0.0)

Статус: **FAIL**. Следующее действие: replace_A_r_plus_q_by_A_times_r_plus_q_or_declare_q_inertial

- `BLOCKER` `COVERAGE-INCOMPLETE` (AUTO): critical-formula adapter is not complete enough for a P1 pass
- `ERROR` `ADD-FRAME` (AUTO) [text lines 165-171: Y=R_b+A_b r_bl+q_bl-O]: add mixes frames inertial and body

### Billiards as Geometry of Observation (1.0.0)

Статус: **FAIL**. Следующее действие: rename_E_n_to_lambda_n_or_apply_hbar_squared_over_2m_energy_bridge

- `BLOCKER` `COVERAGE-INCOMPLETE` (AUTO): critical-formula adapter is not complete enough for a P1 pass
- `ERROR` `RESULT-DIM` (AUTO) [text lines 265-276: -Delta psi_n=E_n psi_n]: result has L^-2, expected L^2 M^1 T^-2
- `ERROR` `LOG-BASE` (AUTO) [text lines 249-255: H=-sum p_j log p_j]: logarithm lacks an explicit base

### Bobsleigh Contact Geometry as a Mass-Distributed Observation System (1.0.0)

Статус: **FAIL**. Следующее действие: define_nonnegative_dissipation_power_and_guard_zero_normal_reaction

- `BLOCKER` `COVERAGE-INCOMPLETE` (AUTO): critical-formula adapter is not complete enough for a P1 pass
- `ERROR` `ZERO-DENOMINATOR` (AUTO) [text lines 300-307: 1-max |T_j|/(mu N_j)]: normalization lacks zero-denominator policy
- `ERROR` `LOG-BASE` (AUTO) [text lines 291-299: H_contact=-sum p_i log p_i]: logarithm lacks an explicit base
- `ERROR` `FRICTION-SIGN` (REVIEW) [equations (14) and (39), text lines 255-263 and 526-535]: with T_j defined as force on the sled, sum T_j dot v_j,rel is nonpositive; dE/dt=-P_fric therefore has the wrong sign unless P_fric is redefined with a leading minus

### Roller-Coaster Geometry as an Observation-Invariant Laboratory (1.0.0)

Статус: **FAIL**. Следующее действие: split_load_vector_from_norm_and_replace_signed_invariant_by_absolute_or_oriented_form

- `BLOCKER` `COVERAGE-INCOMPLETE` (AUTO): critical-formula adapter is not complete enough for a P1 pass
- `ERROR` `FRAME-LAW` (AUTO) [text lines 178-185]: signed_rail_length_split is called invariant without a declared transformation group
- `ERROR` `VECTOR-NORM` (REVIEW) [formula G_body and scalar benchmark maxima]: the vector G_body and scalar load ||G_body|| are used under one name and require separate quantity ids
- `WARNING` `REACH-CONDITION` (REVIEW) [offset rail curves, text lines 164-185]: offset curves require a tubular-neighborhood or reach bound to exclude singular offsets

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

### Relativistic Beam Paths as Observation Geometry (1.2.0)

Статус: **BLOCKED**. Следующее действие: add_complete_SI_HEP_quantity_passport_without_changing_kinematic_core

- `BLOCKER` `COVERAGE-INCOMPLETE` (AUTO): critical-formula adapter is not complete enough for a P1 pass
- `BLOCKER` `UNIT-PASSPORT` (REVIEW) [SI, GeV/c, TeV, and c=1 formulas across sections 3, 6, and 10]: conversions are locally explained but not yet represented by one machine-readable SI/HEP quantity passport

## Интерпретация шлюза

- `PASS` означает прохождение зарегистрированного P0/P1-контракта.
- `FAIL` означает обнаруженную формульную, типовую, кадровую или семантическую ошибку.
- `BLOCKED` означает, что критические примеры не дали ошибки, но покрытие старого PDF недостаточно для строгого P1-pass.
- `REVIEW` означает отсутствие ошибок и блокеров при наличии нефатальных замечаний.
