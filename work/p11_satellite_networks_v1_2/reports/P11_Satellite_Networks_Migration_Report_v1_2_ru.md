# P11 — строгая миграция `Satellite Networks`

Дата: 28 июля 2026  
Статус: **PASS**

## 1. Результат

Legacy-документ
`satellite_networks_observation_v11_relativistic_bilingual(2).pdf`
заменён эталонным модулем
`Satellite Networks under Typed Frames and Temporal Observation Channels v1.2`.
Новая версия является application-layer reference для GO Core v0.2 и
наследует строгий корпус P10.

Это не новый propagator, не operational ephemeris, не модель
конкретной группировки и не новая теория спутниковых сетей. Результат
P11 — типизированная инфраструктура, разделяющая скрытое состояние,
систему координат, сенсорный канал, дискретизацию, temporal graph и
протокол сравнения часов.

Итог эталона:

- 8 страниц A4;
- 53 типизированных выражения;
- 0 замечаний reference-lint;
- 553 benchmark-строки, все `PASS`;
- 623 независимых регрессионных теста, все `PASS`;
- все шрифты встроены;
- постраничный визуальный аудит: `PASS`.

После замены последнего legacy-адаптера корпус содержит
**18 PASS / 0 FAIL / 0 BLOCKED**, 347 зарегистрированных выражений и
0 находок. Тем самым закрыт последний FAIL-модуль корпуса.

## 2. Исходные дефекты и скрытые подмены

Зарегистрированный blocker был трёхчастным:

1. `COVERAGE-INCOMPLETE`: application-layer модуль не имел полного
   типизированного reference-ledger.
2. `FRAME-LAW`: observer-frame orbit closure назывался invariant без
   объявленной группы преобразований.
3. `FRAME-COVERAGE`: доказательство касалось только общего переноса и
   не покрывало вращающиеся системы или релятивистскую границу.

Строгий аудит выявил дополнительные категориальные ошибки:

- векторы из разных начал, ориентаций, эпох и шкал времени складывались
  как элементы одного линейного пространства;
- положение наблюдателя использовалось вместо полной системы отсчёта;
- coordinate spectrum назывался инвариантом, хотя вращающийся frame
  изменяет компоненты и их частотный состав;
- конечный sampled trace смешивался с точным замыканием непрерывной
  орбиты;
- одновременная евклидова геометрия смешивалась с retarded signal;
- snapshot connectivity смешивалась с time-respecting reachability;
- proximity graph интерпретировался как collision-risk model;
- proper time одной мировой линии смешивалось со сравнением разных
  часов при равном coordinate time.

## 3. Типизированное состояние и observation chain

Скрытый пространственный объект задан как маркированный кортеж

\[
X(t)=\bigl(c_E(t),(r_i(t),v_i(t))_{i\in V}\bigr),
\qquad v_i=\dot r_i.
\]

Множество \(\{r_i\}\) недостаточно: оно теряет метки и кратности,
необходимые для tracking и временных рёбер.

Протокол разделён на композицию

\[
\mathcal X
\xrightarrow{\Phi_t}\mathcal X_t
\xrightarrow{F_f}\mathcal Y_f
\xrightarrow{Q}\mathcal D
\xrightarrow{S_{\Delta t,T}}\mathcal D^M
\xrightarrow{\mathcal A}\mathcal I.
\]

Здесь \(F_f\) — обратимая смена координат, \(Q\) — возможно
неинъективный канал, \(S\) — конечная выборка, а \(\mathcal A\) —
оцениватель. Потеря информации относится к \(Q\) или \(S\), но не к
смене frame.

Two-body layer используется только как воспроизводимый synthetic
benchmark. Classical elements признаны локальной координатной картой с
особенностями в круговом и экваториальном пределах. TLE признан
model-specific mean-element record для совместимого SGP4-family
propagator, а не произвольным Kepler state.

## 4. Полный закон системы отсчёта

Rigid frame задан началом \(o(t)\), ориентацией
\(R(t)\in SO(3)\) и объявленной шкалой времени:

\[
y_i=R^\mathsf T(r_i-o),\qquad
c_f=R^\mathsf T(c_E-o).
\]

Группа преобразований —
\[
\mathcal G_I=C^1(I,SE(3)),
\]
действующая диагонально на всех спутниках и центральном теле при общем
coordinate time. Закон скорости содержит transport term:

\[
\dot y_i
=R^\mathsf T(v_i-\dot o)-\Omega_\times y_i,
\qquad \Omega_\times=R^\mathsf T\dot R.
\]

Следовательно, component velocity, acceleration и coordinate spectrum
в общем случае не являются frame invariants.

Маркированная матрица расстояний
\[
D_{ij}(t)=\|r_i(t)-r_j(t)\|
\]
инвариантна при диагональном действии \(\mathcal G_I\). Её centered
Gram matrix
\[
B=-\frac12 JD^{\circ2}J
\]
восстанавливает конфигурацию только с точностью до \(E(3)\), а не
\(SE(3)\): отражение и chirality теряются.

## 5. Phase closure, image closure и frame covariance

Для потока
\[
\theta(t)=\theta_0+\omega t\pmod{2\pi}
\]
введена целочисленная resonance lattice
\[
L_\omega=\{m\in\mathbb Z^k:m\cdot\omega=0\}.
\]

Точное phase closure — coset subtorus размерности
\[
k-\operatorname{rank}_{\mathbb Z}L_\omega.
\]
Это покрывает и промежуточные resonance ranks, а не только дихотомию
«периодическая/плотная».

Для непрерывного канала \(F\) на компактном phase torus
\[
\overline{F(\theta_0+\omega\mathbb R)}
=F(\Gamma_{\theta_0,\omega}).
\]
Но это image closure конкретного канала, а не observer-independent
объект.

При постоянной изометрии \(g\)
\[
K_{gF}=gK_F,
\]
то есть closure эквивариантно с точностью до congruence, но не
поточечно invariant. Для time-dependent frame даже congruence не
гарантируется: неподвижная точка периодическим переносом превращается
в окружность.

## 6. Sampling и retarded observation

На равномерной сетке \(t_m=t_0+m\Delta t\) частоты
\[
\omega'=\omega+\frac{2\pi q}{\Delta t},\qquad q\in\mathbb Z,
\]
дают одинаковые complex samples. Поэтому конечная выборка без
admissible band, schedule, horizon, window, estimator и noise model не
идентифицирует непрерывную частоту и не доказывает рациональную
независимость.

Сигнальный канал использует emission time \(t_e\), определяемое
неявно:
\[
t_r-t_e
=\frac{\|r_s(t_e)-r_o(t_r)\|}{c}.
\]
Разные спутники обычно наблюдаются при разных \(t_e\). Pairwise
distance между apparent positions не является simultaneous state
distance.

Bearing-only data
\[
b_i(t)=\frac{y_i(t)}{\|y_i(t)\|}
\]
теряют range даже при отсутствии шума.

## 7. LOS и temporal graph

Для spherical body line of sight определяется по минимальному
расстоянию от центра тела до закрытого отрезка между спутниками. При
касании выбран строгий blocked policy. Snapshot adjacency требует
одновременно range gate и свободный сегмент.

При общем rigid frame преобразуются все узлы и центральное тело;
пороговые длины сохраняются. Тогда snapshot graph invariant. При
перенумерации \(P\)
\[
A\mapsto PAP^\mathsf T,\qquad
L\mapsto PLP^\mathsf T,
\]
поэтому spectrum графа invariant, а node-specific outputs лишь
equivariant.

Temporal journey сохраняет порядок контактов и неотрицательные delays:
\[
t_{\ell+1}\ge t_\ell+\delta_\ell.
\]
Связность агрегированного статического графа не гарантирует temporal
reachability.

Distance-threshold proximity graph не является conjunction-risk
оценкой: operational collision assessment требует covariance, размеров
объектов, propagation model и временного окна.

## 8. Density, entropy и часы

Kernel density ковариантна при rigid frame только для радиального
нормированного kernel и совместно преобразованных координат. Shannon
entropy конечного partition
\[
H_{\mathcal P}=-\sum_{p_\alpha>0}p_\alpha\log_2p_\alpha
\]
сохраняется только при co-transport partition. Fixed-bin occupancy
entropy является protocol diagnostic, а не frame invariant и не
термодинамической энтропией.

Proper time вдоль фиксированного сегмента мировой линии
\[
\tau[\gamma]=\frac1c\int_\gamma
\sqrt{-g_{\mu\nu}\,dx^\mu dx^\nu}
\]
— spacetime scalar при фиксированных endpoint events. Но разность
показаний разных часов «при \(t=T\)» зависит от coordinate chart,
synchronization и gravity model.

В stationary weak-field audit удержан порядок \(c^{-2}\):
\[
\frac{d\tau}{dt}
=1+\frac{\Phi}{c^2}-\frac{v^2}{2c^2}+O(c^{-4}).
\]
Для круговой орбиты относительно coordinate-stationary reference clock
\[
\Delta_{\rm circ}(r)
=\frac{\mu_E}{c^2}
\left(\frac1{R_\star}-\frac{3}{2r}\right).
\]
Численные controls воспроизводят знак LEO, GPS-like и GEO-like offsets,
но не претендуют на operational GNSS clock model.

## 9. Машинная проверка

Reference-ledger содержит 53 типизированных выражения и проходит strict
lint без находок. Общий ledger содержит 18 эталонных документов и 347
выражений:

- `PASS`: 18;
- `FAIL`: 0;
- `BLOCKED`: 0;
- findings: 0.

Численный слой содержит 553 строки:

- two-body energy и angular momentum: 96;
- rigid-frame distances и spherical clearances: 240;
- Euclidean distance matrix controls: 16;
- graph frame/relabel controls: 56;
- exact sampling alias: 128;
- weak-field clocks: 8;
- entropy: 3;
- static light time: 1;
- temporal earliest arrival: 5.

Полный independent suite содержит 623 теста. Максимальный
dimensionless spectral/reconstruction residual находится на уровне
\(3.4\times10^{-15}\); максимальное абсолютное расхождение
frame-covariance на координатных длинах порядка десятков тысяч
километров меньше \(2.6\times10^{-7}\,\mathrm m\).

## 10. Проверенные границы литературы

Frame/time-scale и relativistic conventions сверены с
`IERS Conventions (2010)`, Chapters 5 and 10. Orbit-message metadata
сверены с `CCSDS 502.0-B-3`. Ограничение TLE/SGP4 подтверждено
Vallado–Crawford–Hujsak–Kelso, AIAA 2006-6753. GPS clock context
сверен с `IS-GPS-200N` и Ashby,
DOI `10.12942/lrr-2003-1`. Temporal reachability сверена с
Kempe–Kleinberg–Kumar, DOI `10.1145/335305.335364`.
Euclidean distance reconstruction опирается на Schoenberg,
JSTOR `1968654`.

## 11. Строгая научная оценка

P11 закрывает дефекты типов и групповых законов в последнем
FAIL-модуле. Его содержательная ценность — в едином воспроизводимом
firewall между координатным представлением, invariant/equivariant
объектами, observation loss, временной сетевой структурой и
clock-comparison protocol.

Отдельные составляющие классические: \(SE(3)\)-covariance,
Euclidean-distance matrices, torus closures, sampling aliases,
line-of-sight geometry, temporal journeys и proper time. Их сборка не
является новой теорией astrodynamics или satellite networks.

Следующий рациональный этап — P12: полный corpus freeze, проверка
межмодульных зависимостей, унификация manifest/DOI metadata и
подготовка единого master release.
