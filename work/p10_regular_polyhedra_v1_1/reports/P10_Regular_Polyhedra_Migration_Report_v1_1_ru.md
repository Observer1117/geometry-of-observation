# P10 — строгая миграция `Regular Polyhedra`

Дата: 28 июля 2026  
Статус: **PASS**

## 1. Результат

Legacy-документ `regular_polyhedra_observation_v1_bilingual(2).pdf`
заменён эталонным модулем
`Regular Polyhedra under Typed Observation Filters v1.1`.
Новая версия является application-layer reference для GO Core v0.2 и
наследует инфраструктуру корпуса P9.

Это не новая классификация многогранников, не новый регулярный
многогранник и не новый алгоритм распознавания формы. Результат P10 —
строго типизированная инфраструктура, разделяющая абстрактную
инцидентность, евклидову реализацию, регулярность, допустимость объектов,
потерю информации и идентифицируемость при конечном разрешении.

Итог эталона:

- 7 страниц A4;
- 42 типизированных выражения;
- 0 замечаний reference-lint;
- 302 benchmark-строки, все `PASS`;
- 357 независимых регрессионных тестов, все `PASS`;
- максимальный численный остаток \(1.34\times10^{-15}\);
- все шрифты встроены;
- постраничный визуальный аудит: `PASS`.

После замены legacy-адаптера корпус содержит **17 PASS / 1 FAIL /
0 BLOCKED**, 295 зарегистрированных выражений и три оставшихся
замечания. Все они принадлежат только `Satellite Networks`.

## 2. Почему legacy filter ladder был неопределён

В старой версии observation filter задавался кортежем
\(O=(A,R,Q)\), после чего использовались выражения \(O_1\subset O_2\)
и «variance of \(O\)». Для произвольного кортежа ни включение, ни
направление монотонности не определены.

В v1.1 observation specification имеет тип

\[
\mathcal O=(\mathcal C_{\mathcal O},Y_{\mathcal O},Q_{\mathcal O}),
\]

где \(\mathcal C_{\mathcal O}\) — полный подгруппоид допустимых
реализованных объектов, \(Y_{\mathcal O}\) — пространство данных, а
\(Q_{\mathcal O}\) — invariant observation map.

Определены два независимых предпорядка.

1. Допустимость:
   \[
   \mathcal O_1\preceq_{\rm adm}\mathcal O_2
   \iff
   \mathcal C_{\mathcal O_1}
   \text{ — полный подгруппоид }
   \mathcal C_{\mathcal O_2}.
   \]
   Увеличение домена допускает больше объектов.
2. Информационное огрубление:
   \[
   \mathcal O_{\rm fine}\succeq_{\rm info}\mathcal O_{\rm coarse}
   \iff
   Q_{\rm coarse}=\kappa\circ Q_{\rm fine}.
   \]
   Тогда
   \(\ker Q_{\rm fine}\subseteq\ker Q_{\rm coarse}\): грубый канал
   отождествляет не меньше объектов.

Расширение допустимого класса не задаёт информационного огрубления.
Исторические послабления конечности, планарности граней,
самопересечений и локальной конечности также не образуют одну цепь:
они дают частично упорядоченное семейство, filter poset.

## 3. Абстрактный объект и его реализация

Legacy-кортеж \((V,E,F,I)\) был недостаточен как определение
многогранника. В v1.1 rank-3 abstract polyhedron задан как ранжированный
poset с единственными наименьшей и наибольшей гранями, diamond condition
и strong flag connectivity.

Реализованный объект имеет тип

\[
X=(\mathcal P,\beta,\mathsf T),
\]

где \(\mathcal P\) — абстрактный многогранник, \(\beta\) — реализация в
\(\mathbb R^3\), а \(\mathsf T\) фиксирует соглашения о рёбрах, гранях,
дискретности, локальной конечности и faithful realization. Эти объекты
и согласованные изоморфизмы образуют группоид
\(\mathbf{RPol}_3\).

Тем самым выпуклые face-lattice realizations, regular maps, звёздчатые
модели и skeletal apeirohedra больше не считаются одним неуточнённым
типом.

## 4. Абстрактная и геометрическая регулярность

Абстрактная группа

\[
\Gamma(\mathcal P)=\operatorname{Aut}(\mathcal P)
\]

действует на абстрактных флагах. Абстрактная регулярность означает
транзитивность этого действия. Для abstract polyhedron стабилизатор
флага тривиален; в конечном случае

\[
|\operatorname{Aut}(\mathcal P)|
=|\operatorname{Flag}(\mathcal P)|=4E.
\]

Геометрическая группа \(G_\beta\) состоит из изометрий окружающего
пространства, сохраняющих реализованные вершины, рёбра и объявленные
грани. Она индуцирует подгруппу
\(\iota_\beta(G_\beta)\leq\operatorname{Aut}(\mathcal P)\).

Faithful geometrically regular realization имеет абстрактно регулярную
инцидентную структуру, но обратное утверждение ложно. Точный контроль —
абстрактный куб и прямоугольный cuboid с тремя различными длинами рёбер:
абстрактная группа имеет порядок 48 и один flag orbit, тогда как
геометрическая группа cuboid имеет порядок 8 и шесть flag orbits.

Для type \(\{p,q\}\) также введены distinguished involutions
\((\rho_0,\rho_1,\rho_2)\), string relations и обязательное
intersection property. Одни Coxeter relations без intersection
property не сертифицируют abstract polyhedron.

## 5. Классический сферический счёт и его границы

Для конечной equivelar map типа \(\{p,q\}\)

\[
pF=2E,\qquad qV=2E.
\]

При сферической топологии \(V-E+F=2\), поэтому

\[
\frac1p+\frac1q-\frac12=\frac1E>0.
\]

Для целых \(p,q\geq3\) остаются пять пар

\[
(3,3),\ (4,3),\ (3,4),\ (5,3),\ (3,5).
\]

Это доказательство относится к конечным тонким equivelar spherical maps.
Оно не классифицирует звёздчатые многогранники, higher-genus maps,
apeirohedra или все abstract regular polyhedra.

Duality точно меняет \((V,E,F)\) на \((F,E,V)\) и
\(\{p,q\}\) на \(\{q,p\}\); это комбинаторная операция, а не смена
точки наблюдения.

## 6. Точная неинъективность skeleton observation

Утверждение «один skeleton, разные грани» заменено явным контролем.
Petrie operation меняет distinguished generators на

\[
(\rho_0\rho_2,\rho_1,\rho_2)
\]

и сохраняет вершины и рёбра. Для куба исходная map имеет шесть
квадратных граней и \(f\)-vector \((8,12,6)\), а её Petrial — четыре
шестиугольных Petrie faces и \(f\)-vector \((8,12,4)\).

Их vertex-edge skeleton совпадает, но Euler characteristics равны
соответственно 2 и 0. Следовательно, observation map, сохраняющий
только \((V,E)\), неинъективен на конкретной паре объектов; это не
метафора и не аргумент от рисунка.

## 7. Конечное разрешение и идентифицируемость

После объявленных регистрации, маркировки и incidence matching для
данных \(y_i=x_i+\eta_i\), \(\|\eta_i\|\leq\epsilon\), определён
размерный RMS residual

\[
r_Y(g)=\min_{\pi\in\Pi}
\left(\frac1n\sum_i
\|g y_i-y_{\pi(i)}\|^2\right)^{1/2}.
\]

Если \(g\) является точной симметрией исходного объекта для допустимой
перестановки, то \(r_Y(g)\leq2\epsilon\). Обратное неверно: малый
остаток доказывает только threshold-dependent approximate symmetry.

Для конечной библиотеки кандидатов \(\{M_1,\ldots,M_K\}\) введён
half-separation certificate. Если

\[
\Delta_i=\min_{j\ne i}d_Q(M_i,M_j)>0,\qquad
d_Q(Y,M_i)<\Delta_i/2,
\]

то \(M_i\) — единственный ближайший кандидат в объявленной библиотеке.
Сертификат не доказывает полноту библиотеки.

Flag-orbit entropy задан с основанием 2 и только для конечного
вероятностного разбиения. Это комбинаторная Shannon diagnostic, а не
термодинамическая энтропия.

## 8. Convention-scoped counts и claim firewall

Числа 5, 4 и 48 относятся к разным категориям:

- пять convex regular polyhedra в \(\mathbb R^3\) с точностью до
  similarity;
- четыре classical Kepler–Poinsot star polyhedra;
- 48 discrete geometrically regular skeletal polyhedra в
  \(\mathbb R^3\) по соглашению Schulte: 18 finite и 30 infinite.

Число 48 не является числом всех abstract regular polyhedra. В v1.1
каждое перечисление связано с object class, equivalence relation и
реализационным соглашением.

Границы формализма сверены с McMullen–Schulte
(`10.1017/CBO9780511546686`, `10.1007/PL00009304`), Schulte
(`arXiv:1711.02297`, `10.1107/S2053273314000217`), Grünbaum
(`10.1007/BF01836414`) и Dress
(`10.1007/BF02188039`, `10.1007/BF02189831`).

## 9. Машинная проверка

Reference-ledger содержит 42 выражения и проходит строгий lint без
находок. Benchmarks проверяют:

- инцидентные тождества, Euler characteristic, duality и flag counts
  пяти Platonic controls;
- полный integer grid для сферического ограничения;
- квадратные и Petrie cycles куба;
- порядки групп куба и generic cuboid;
- числа flag orbits;
- bounded-noise residual;
- half-separation certificate для конечной библиотеки.

Итог: **302/302 benchmark-строки**, **357/357 регрессионных тестов**.
Обновлённый corpus-ledger содержит 18 документов, 17 reference records,
один critical adapter и 295 выражений. Строгий полный прогон намеренно
остаётся ненулевым только из-за `Satellite Networks`: **17 PASS /
1 FAIL / 0 BLOCKED**.

Следующий рациональный кандидат — `Satellite Networks`, последний
оставшийся critical adapter корпуса.
