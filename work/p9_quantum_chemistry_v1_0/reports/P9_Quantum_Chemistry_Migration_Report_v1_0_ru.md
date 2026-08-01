# P9 — строгая миграция `Quantum Chemistry`

Дата: 28 июля 2026  
Статус: **PASS**

## 1. Результат

Legacy-документ `quantum_chemistry_observation_v1_bilingual(1).pdf`
заменён эталонным модулем
`Quantum Chemistry as a Typed Inference Stack under Observation Maps v1.1`.
Новая версия является application-layer reference для GO Core v0.2 и
наследует контракт P8 для conical intersections.

Это не новый метод электронной структуры, не новый density functional и
не универсальная теория химической связи. Результат P9 — строгая
инфраструктура типов, редукций, gauge-свобод, приближений и каналов
наблюдения, необходимая для корректного сравнения квантово-химических
расчётов с измеряемыми данными.

Итог эталона:

- 9 страниц A4;
- 47 типизированных выражений;
- 0 замечаний reference-lint;
- 202 численные benchmark-строки, все `PASS`;
- 413 независимых регрессионных тестов, все `PASS`;
- все шрифты встроены;
- постраничный визуальный аудит: `PASS`.

После замены адаптера весь корпус содержит **16 PASS / 2 FAIL /
0 BLOCKED**, 253 зарегистрированных выражения и пять оставшихся
замечаний. Они относятся только к `Regular Polyhedra` и
`Satellite Networks`.

## 2. Почему legacy-цепочка была некорректна

Старая линейная запись

\[
\Psi\longrightarrow \rho\longrightarrow E(R)\longrightarrow R_\ast
\longrightarrow \text{chemical behavior}
\]

не является одной композиционной картой.

1. Полное молекулярное состояние зависит одновременно от электронных и
   ядерных координат; электронная волновая функция при фиксированном
   \(R\) уже относится к редуцированной clamped-nuclei модели.
2. Одночастичная матрица плотности и пространственная плотность
   получаются частичным следом и диагональным readout. Они не порождают
   поверхность потенциальной энергии без отдельного выбора
   гамильтониана и Born–Oppenheimer reduction.
3. \(E_k(R)\) — ветвь параметрического спектра \(H_{\rm e}(R)\), а
   \(R_\ast\) — класс стационарной геометрии после факторизации жёстких
   движений и, при необходимости, перестановок одинаковых ядер.
4. Химические дескрипторы и спектр требуют отдельных операторов,
   representation schemes, populations, line profiles и
   instrument channels.

В v1.1 эти операции представлены тремя разными строками typed graph:
many-body reduction, model/PES workflow и state-to-instrument
observation channel.

## 3. Исправления состояния и Born–Oppenheimer reduction

Полный нерелятивистский кулоновский гамильтониан записан со всеми
электронными и ядерными кинетическими членами, electron–nuclear,
electron–electron и nucleus–nucleus взаимодействиями. Его состояние
имеет аргументы

\[
\Psi(x_1,\ldots,x_{N_{\rm e}};R_1,\ldots,R_{N_{\rm n}}).
\]

Отдельно определена clamped-nuclei family
\(\widehat H_{\rm e}(R)\), причём явно зафиксировано включение
\(V_{\rm nn}(R)\). Born–Huang expansion является преобразованием внутри
объявленного электронного семейства, а одноповерхностная
Born–Oppenheimer модель — редукцией с возможной потерей информации.
Она не называется сменой системы отсчёта и не считается равномерно
валидной при замыкании внутренней щели.

В окрестности conical intersection индивидуальные rank-one projectors,
Berry holonomy, derivative couplings и динамический переход переданы
наследуемому контракту P8.

## 4. Reduced density matrices и контроль неинъективности

Принята нормировка

\[
\gamma^{(1)}
=N\,\operatorname{Tr}_{2,\ldots,N}\Gamma_N,\qquad
\operatorname{Tr}\gamma^{(1)}=N,\qquad
\int n(\mathbf r)\,d^3r=N.
\]

Для любого one-body observable
\(\widehat A=\sum_i a(i)\) доказано

\[
\operatorname{Tr}(\Gamma_N\widehat A)
=\operatorname{Tr}(\gamma^{(1)}a).
\]

Неинъективность не оставлена декларацией. Реализован точный контроль

\[
\lvert\Psi_\pm\rangle
=\frac{\lvert12\rangle\pm\lvert34\rangle}{\sqrt2},
\]

где оба состояния имеют
\(\gamma^{(1)}=\tfrac12 I_4\), но дают противоположные значения
двухчастичной когерентности. Поэтому ни one-RDM, ни её диагональ
\(n(\mathbf r)\) не являются общей томографией произвольного
many-body state.

## 5. Finite basis, Hartree–Fock и orbital gauge

Для неортогонального базиса восстановлена generalized Roothaan–Hall
задача

\[
FC=SC\varepsilon,\qquad C^\dagger SC=I,
\]

с обязательными условиями Hermiticity, \(S>0\) и порогом линейной
зависимости. Запись \(FC=C\varepsilon\) допустима только после
явной ортогонализации или в ортонормированном базисе.

Для занятых коэффициентов \(C_{\rm o}\) доказано действие

\[
C_{\rm o}\mapsto C_{\rm o}U,\qquad U\in U(N_{\rm occ}),
\]

которое сохраняет \(P=C_{\rm o}C_{\rm o}^\dagger\) и меняет Slater
determinant только фазой \(\det U\). Следовательно, локализованные
орбитали, hybrid labels и orbital-by-orbital bond pictures являются
representation choices, если локализационный или декомпозиционный
протокол не объявлен.

Hartree–Fock сформулирован как вариационная задача на нормированных
Slater determinants. SCF convergence означает стационарное решение,
но не сертификат глобального минимума. Для общего гамильтониана и
пространства

\[
E_{\rm corr}=E_0-E_{\rm HF}\le 0.
\]

## 6. DFT firewall

Ground-state DFT отделена от операции partial trace. Введён
Levy constrained search

\[
F[n]=\inf_{\Gamma\mapsto n}
\operatorname{Tr}\Gamma(\widehat T+\widehat W)
\]

и отдельная вариация по допустимым плотностям при фиксированных
particle number и interaction.

Hohenberg–Kohn theorem квалифицирован как ground-state statement об
external scalar potential modulo constant. Он не превращён в
томографию произвольных excited, mixed, time-dependent или open-system
states. Kohn–Sham orbitals названы auxiliary construction, а общие
KS eigenvalue differences не отождествлены с interacting excitation
energies.

## 7. Nuclear geometry и нормальные моды

Внутренняя геометрия изолированной молекулы определена как quotient
Cartesian configuration space по \(\mathrm{SE}(3)\) и, когда это
физически принято, по перестановкам одинаковых ядер.

Legacy-ошибка размерности исправлена:

\[
\mathsf K=\mathsf M^{-1/2}H_R\mathsf M^{-1/2},\qquad
\mathsf Ku_k=\lambda_k u_k,\qquad
\lambda_k=\omega_k^2.
\]

Следовательно, eigenvalue mass-weighted Hessian имеет размерность
\(T^{-2}\), angular frequency — \(T^{-1}\), а cyclic frequency и
wavenumber требуют деления на \(2\pi\) и \(2\pi c\).

Перед классификацией minimum или first-order transition state
удаляются пять rigid zero modes для линейной изолированной молекулы
или шесть для нелинейной. Порог нуля должен быть масштабирован и
записан; computed small value не объявляется exact zero автоматически.

## 8. Active spaces, bonds и valence interpretations

Active-space reduction теперь начинается с объявленного projector
\(P_{\mathcal A}\):

\[
\gamma_{\mathcal A}
=P_{\mathcal A}\gamma^{(1)}P_{\mathcal A},\qquad
N_{\mathcal A}
=\operatorname{Tr}(\gamma^{(1)}P_{\mathcal A}).
\]

Алгоритм построения projector, basis, window или threshold входят в
протокол. Partial charges, bond orders, oxidation assignments,
hybridization и valence populations являются scheme-conditional
interpretations, пока не доказана соответствующая инвариантность.

## 9. Спектр и observation channel

Идеальный спектр определяется не одними energy differences:

\[
S_A(\omega)
=\sum_{i,f}p_i
\lvert\langle f|\widehat A|i\rangle\rvert^2
L_\Gamma\!\left(
\omega-\frac{E_f-E_i}{\hbar}
\right).
\]

Необходимы stationary states, initial populations, transition
operator, matrix elements и нормированный line profile.
Measured record вынесен в отдельный канал

\[
Y=\mathcal D_\epsilon\mathcal C_{\rm inst}[S_A]+\eta.
\]

Instrument response, sampling, quantization, calibration, baseline,
noise law, estimator и uncertainty не смешиваются с идеальным
quantum observable. Symmetry-allowed transition трактуется как
необходимое условие разрешённости, а не гарантия ненулевой интенсивности.

## 10. Проверки

Машинный reference-ledger содержит 47 выражений и проходит strict mode
без находок. Общий corpus-ledger содержит 18 документов и 253
выражения. Его strict-run намеренно остаётся ненулевым только из-за
двух legacy-адаптеров:

- `regular-polyhedra-v1`: incomplete coverage и неопределённый порядок
  на tuple \(O=(A,R,Q)\);
- `satellite-networks-v1-1`: incomplete coverage, необъявленная группа
  frame-invariance и неполное покрытие observer transformations.

Численные контроли проверяют generalized eigenproblems, metric
orthonormality, occupied-orbital gauge, one-RDM non-injectivity,
diatomic и synthetic normal modes, variational correlation sign,
nested Rayleigh–Ritz bounds, line-profile normalization, spectral
convolution и active-space occupations.

PDF собран без LaTeX warnings, обрезки и наложений. Девять страниц
отрендерены при 144 dpi и проверены постранично; библиография имеет
единственный заголовок.

## 11. Первичные источники

- M. Born, R. Oppenheimer, DOI `10.1002/andp.19273892002`;
- J. C. Slater, DOI `10.1103/PhysRev.34.1293`;
- C. C. J. Roothaan, DOI `10.1103/RevModPhys.23.69`;
- P.-O. Löwdin, DOI `10.1103/PhysRev.97.1474`;
- A. J. Coleman, DOI `10.1103/RevModPhys.35.668`;
- P. Hohenberg, W. Kohn, DOI `10.1103/PhysRev.136.B864`;
- W. Kohn, L. J. Sham, DOI `10.1103/PhysRev.140.A1133`;
- M. Levy, DOI `10.1073/pnas.76.12.6062`;
- C. A. Mead, D. G. Truhlar, DOI `10.1063/1.437734`.

## 12. Следующий кандидат

Следующий рациональный кандидат — `Regular Polyhedra`: его оставшийся
дефект локален и структурно отделён от более широкого frame-law
переписывания `Satellite Networks`.
