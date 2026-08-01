# P8: строгая миграция `Conical Intersections` на GO Core v0.2

Дата: 28 июля 2026 года  
Статус: `PASS` для нового эталона; полный корпус сохраняет ожидаемый ненулевой strict-run из-за трёх legacy-адаптеров.

## 1. Результат

Legacy-документ `Conical Intersections as Observation Caustics v1.0` заменён эталонным модулем:

`Conical Intersections as Typed Spectral Singularities under Observation Maps v1.1`.

Новая версия не объявляет коническое пересечение оптической каустикой. Формальный объект теперь определён как поперечный прообраз спектрального дискриминанта, на котором индивидуальное адиабатическое rank-one разбиение не продолжается, хотя проектор на изолированный двухуровневый кластер может оставаться гладким.

Итоговый reference-ledger:

- 1 эталонный документ;
- 36 типизированных выражений;
- 0 автоматических находок;
- 0 ручных замечаний;
- статус `PASS`.

Корпус после замены:

- 18 канонических документов;
- 15 полных reference-ledger;
- 3 legacy critical-adapter;
- 208 типизированных выражений;
- 8 находок только в ещё не мигрированных документах;
- статусы: `15 PASS / 3 FAIL / 0 BLOCKED`.

## 2. Дефекты v1.0

### 2.1. Глобальный собственный вектор как выход отображения

Старая запись

\[
\Pi_{\rm BO}:H_{\rm e}(Q)\longmapsto\{E_k(Q),|u_k(Q)\rangle\}_k
\]

не является глобальным gauge-invariant отображением. Нормированный собственный вектор зависит от локальной фазы, а в вещественном представлении меняет знак после нечётного обхода конического пересечения.

Исправление:

- gauge-invariant выходом служит спектральный проектор \(P_k\);
- собственный вектор \(u_k^{(\alpha)}\) является локальной секцией;
- преобразование \(u_k\mapsto e^{i\chi_k}u_k\) отделено от наблюдательного канала.

### 2.2. Смешение ядерных и энергетических координат

В v1.0 символы \(Q_1,Q_2\) сначала обозначали ядерные координаты, а затем входили в

\[
H=Q_1\sigma_z+Q_2\sigma_x
\]

как энергии. Из-за этого формула \(\|d_{12}\|\sim(2r)^{-1}\) не имела единственной физической размерности.

Исправление:

\[
x=g_\mu\delta q^\mu,\qquad y=h_\mu\delta q^\mu,
\]

где \(q^\mu\) — физические ядерные координаты, \(g_\mu,h_\mu\) — энергетические градиенты, а \(x,y\) — energy-valued branching coordinates.

В length-chart:

\[
[q]=L,\qquad [g]=[h]=EL^{-1},\qquad [x]=[y]=E.
\]

### 2.3. Неправильный объект, теряющий гладкость

Фраза «адиабатическая карта ломается» была слишком грубой. Для изолированного двухуровневого кластера Riesz-проектор

\[
P_{\rm cl}(q)=\frac{1}{2\pi i}\oint_\Gamma(z-H_{\rm e}(q))^{-1}\,dz
\]

может оставаться гладким при внутреннем вырождении. Сингулярно именно разбиение на индивидуальные \(P_+\) и \(P_-\).

В normal form

\[
P_\pm(x,y)=\frac12\left(I\pm\frac{x\sigma_z+y\sigma_x}{\sqrt{x^2+y^2}}\right).
\]

При подходе к началу по \(x>0\) и \(x<0\) пределы различаются, поэтому rank-one проектор не продолжается однозначно. При этом

\[
P_{\rm cl}=P_++P_-=I_2
\]

остаётся регулярным.

### 2.4. Критерий каустики через \(\det DF\)

Старая запись \(\det DF=0\) годилась только для квадратной локальной карты. Универсальный критерий классической каустики — потеря ранга объявленной проекции.

Для CI это всё равно не определяющий критерий. Карта параметров в пространство матриц может иметь полный ранг. Сингулярно eigen-decomposition отображение на дискриминанте повторных собственных значений.

Исправление:

- оптическая каустика и CI не объявляются эквивалентными;
- «observation caustic» имеет статус `analogy`;
- строгий термин — `spectral-discriminant singularity`.

### 2.5. Gauge-статус Berry-фазы

Смена знака одного выбранного собственного вектора не является сама по себе gauge-invariant алгоритмом.

Введено замкнутое произведение перекрытий:

\[
W_N=\prod_{j=0}^{N-1}
\frac{\langle u_j,u_{j+1}\rangle}
{|\langle u_j,u_{j+1}\rangle|},
\qquad u_N=u_0.
\]

Локальные фазы телескопически сокращаются. Для winding number \(w\):

\[
\operatorname{Hol}(C)=(-1)^w,\qquad
\gamma(C)=\pi w\pmod{2\pi}.
\]

Отдельно зафиксировано:

- вещественная line bundle при нечётном winding нетривиальна;
- комплексная line bundle над punctured plane может иметь глобальную комплексную секцию;
- нетривиальная голономия не требует ненулевой гладкой Berry curvature вне начала координат.

### 2.6. Gauge-covariant derivative coupling

Вектор \(d_{+-}=\langle u_+,\nabla u_-\rangle\) не является gauge-invariant. Инвариантны его норма и quantum metric.

В energy coordinates:

\[
d_{+-}^{(E)}
=\frac{1}{2r^2}(y,-x)^\mathsf T,
\qquad
\|d_{+-}^{(E)}\|=\frac{1}{2r},
\qquad [d_{+-}^{(E)}]=E^{-1}.
\]

Gauge-invariant metric:

\[
g^{(E)}
=\frac1{4r^4}
\begin{pmatrix}
y^2&-xy\\
-xy&x^2
\end{pmatrix},
\qquad
\operatorname{Tr}g^{(E)}=\frac1{4r^2}.
\]

Физический pullback:

\[
d_{+-}^{(q)}=J^\mathsf T d_{+-}^{(E)},\qquad
g^{(q)}=J^\mathsf T g^{(E)}J,\qquad
J=D_q(x,y).
\]

В length-chart:

\[
[d_{+-}^{(q)}]=L^{-1},\qquad [g^{(q)}]=L^{-2}.
\]

### 2.7. Статическая геометрия и динамика

Закрытие щели нарушает uniform-gap предпосылку стандартных адиабатических оценок, но не задаёт вероятность перехода.

Введён dimensionless diagnostic:

\[
\eta_{ab}(t)=
\frac{\hbar|\langle u_a,\dot H_{\rm e}u_b\rangle|}
{|E_b-E_a|^2}.
\]

Для контрольной модели

\[
H_{\rm LZ}(t)=vt\sigma_z+b\sigma_x
\]

точная Landau-Zener вероятность в заявленном infinite-time two-state протоколе равна

\[
P_{\rm D}=\exp\left(-\frac{\pi b^2}{\hbar v}\right).
\]

При одной и той же минимальной щели \(2b\) изменение скорости \(v\) меняет результат. Поэтому static gap, Berry phase и NAC не заменяют wavepacket dynamics.

### 2.8. Конечное спектральное разрешение

Для

\[
Y_\pm=E_\pm+\varepsilon_\pm
\]

введено:

\[
\widehat\Delta=Y_+-Y_-,
\qquad
\sigma_\Delta^2=
\sigma_+^2+\sigma_-^2-2\operatorname{Cov}(\varepsilon_+,\varepsilon_-).
\]

Решение

\[
|\widehat\Delta|
\le\kappa\sigma_\Delta+\epsilon_E
\]

классифицирует только `unresolved near-degeneracy`. Оно не доказывает:

- точное вырождение;
- коническую топологию;
- Berry-фазу \(\pi\);
- неадиабатический переход.

### 2.9. Gapped control меняет symmetry class

Модель

\[
H_\delta=x\sigma_z+y\sigma_x+\delta\sigma_y
\]

открывает щель, но при \(\delta\ne0\) выходит из real-symmetric class. Она не является нейтральной регуляризацией исходного real CI.

Для кругового пути:

\[
\gamma_\delta(R)=
\pi\left(1-\frac{\delta}{\sqrt{R^2+\delta^2}}\right)
\]

при зафиксированной ориентации. Фаза не квантуется при \(\delta\ne0\).

## 3. Формальная область действия

Эталон v1.1 строго покрывает:

- \(C^2\) finite-dimensional Hermitian family;
- изолированный двухуровневый spectral cluster;
- real-symmetric two-state branching normal form;
- физическую length-chart с типизированным branching Jacobian;
- rank-one projectors вне seam;
- Berry holonomy замкнутых путей вне seam;
- quantum metric и физический pullback;
- Landau-Zener control как отдельную dynamical model;
- finite-resolution spectral channel.

Не покрываются без отдельного расширения:

- unbounded electronic operators без common-domain/resolvent контракта;
- spin-orbit complex class;
- Kramers degeneracy;
- higher multiplicity intersections;
- global exact diabatization;
- multistate nonadiabatic dynamics;
- surface hopping, MCTDH и ab initio CI search;
- universal chemical branching prediction.

## 4. Верификация

### 4.1. Машинная типизация

- reference documents: 1;
- typed expressions: 36;
- findings: 0;
- status: `PASS`.

### 4.2. Численные регрессии

Пройдено 150 тестов:

- Pauli algebra и exact spectrum;
- projector idempotence, orthogonality и cluster closure;
- отсутствие rank-one limit;
- gauge invariance замкнутого overlap product;
- winding parity;
- quantum metric и finite-difference projector identity;
- physical pullback;
- gapped Berry phase;
- Landau-Zener scaling и guards;
- covariance-aware gap uncertainty;
- finite-resolution classification;
- contract, ledger, PDF metadata, fonts, hashes и source fragments.

Benchmark table содержит 35 строк. Максимальные остатки:

- projector idempotence: \(1.39\times10^{-16}\);
- projector orthogonality: \(7.63\times10^{-17}\);
- quantum-metric identity: \(1.43\times10^{-14}\);
- random-gauge holonomy: \(4.45\times10^{-15}\);
- discretized gapped Berry phase: \(2.21\times10^{-7}\) rad.

### 4.3. PDF

- 8 страниц;
- все шрифты встроены;
- LaTeX-log без layout/reference warnings;
- 8/8 страниц отрендерены и проверены;
- обрезок, наложений, сломанных таблиц, дублированных заголовков и пропавших glyphs нет.

## 5. Строгая оценка новизны

Математическая и физическая база модуля классическая:

- Born-Oppenheimer reduction;
- codimension counting для level degeneracy;
- spectral projectors;
- Longuet-Higgins/Berry holonomy;
- derivative couplings и quantum metric;
- Landau-Zener control.

Новое здесь не является новой теорией конических пересечений. Результат P8 — нормативная интеграция этих объектов в GO Core:

- типизация координат и единиц;
- gauge/channel separation;
- cluster/rank-one separation;
- static/dynamic separation;
- finite-resolution identifiability;
- machine-verifiable claim firewall.

Любая заявка на физическую новизну сверх этой инфраструктуры пока была бы необоснованной.

## 6. Следующий этап

Следующий прямой кандидат — `Quantum Chemistry through Geometry of Observation`. P8 уже дал ему недостающий spectral-cluster, gauge и nonadiabatic interface. В legacy-версии остаются две точные ошибки:

1. собственные значения mass-weighted Hessian имеют размерность \(T^{-2}\), а частоты равны \(\omega_k=\sqrt{\lambda_k}\);
2. критерии минимума/transition state должны формулироваться после удаления 5 или 6 rigid translation/rotation zero modes.

После этой миграции корпус должен перейти к `16 PASS / 2 FAIL`.

## 7. Проверенные первичные источники

- [Born--Oppenheimer 1927](https://onlinelibrary.wiley.com/doi/10.1002/andp.19273892002)
- [Longuet-Higgins et al. 1958](https://royalsocietypublishing.org/rspa/article/244/1236/1/10193/Studies-of-the-Jahn-Teller-effect-II-The-dynamical)
- [Herzberg--Longuet-Higgins 1963](https://pubs.rsc.org/en/content/articlelanding/1963/df/df9633500077)
- [Mead--Truhlar 1979](https://aip.scitation.org/doi/abs/10.1063/1.437734)
- [Berry 1984](https://royalsocietypublishing.org/rspa/article/392/1802/45/15579/Quantal-phase-factors-accompanying-adiabatic)
- [Zener 1932](https://royalsocietypublishing.org/rspa/article/137/833/696/3285/Non-adiabatic-crossing-of-energy-levels)

