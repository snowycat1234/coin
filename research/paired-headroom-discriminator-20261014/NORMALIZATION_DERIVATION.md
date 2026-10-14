# Exact sufficient rolling statistic

For current signed inventory q, let s=sign(q), Q=abs(q), P=current own mark,
and E=current isolated equity. For one direction-clipped historical pair:

    r = exp(adverse five-minute mark log move)
    f = r * exp(adverse own execution gap) * (1 - s * .0008)
    stressed mark = P*r
    stressed fill = P*f

The unchanged original stressed headroom is:

    E + q*P*(r-1) - .005*Q*P*r - Q*P*abs(f-r) - .00055*Q*P*f

Factor Q*P, using q=s*Q:

    E - Q*P*[.005*r + abs(f-r) + .00055*f - s*(r-1)]

The bracket is K_pair. Since Q*P is nonnegative, the smallest scenario
headroom is E-Q*P*max(K_pair). Thus two rolling maxima, one for each direction,
are exact algebraic sufficient statistics for every own q/E/mark assessment.
The original monotone-deque routine computes them in O(N) per symbol. At a
decision, assessment is O(1). No scenarios are sampled, approximated or dropped
to reduce compute. IEEE float64 regrouping can differ by roundoff; tests compare
the direct original assess() result over every eligible synthetic pair. No
roundoff tolerance is inserted into the candidate trigger.

Finite scalar operands can still overflow the normalized multiplication or
headroom subtraction. READY invested assessments explicitly refuse nonfinite
required equity/headroom with ValueError. The final boolean also retains the
original finite-headroom gate. Independent review supplied two overflow
counterexamples, now retained as regressions. This is a numerical refusal,
not a new stress threshold, input bound or missing-scenario approximation.

For input index i with t=times[i]+MINUTE, eligible historical opens j are
i-43200+6 through i inclusive. Move endpoints are mark[j-6] and mark[j-1],
own gap is open[j]/mark[j-1]. A fixed43195-observation rolling window therefore
computes the exact population. The original readiness function retains its
43201-mark and43200-completed-open admission requirements unchanged.

Three fixed source outputs separate effects:

- Legacy independent: exact original HEADROOM maxima and endpoint population
- Aligned independent: separate adverse maxima of exactly the candidate pairs
- Paired candidate: maximum of each whole pair's K

Legacy versus aligned is an alignment/population difference. Aligned versus
paired isolates coupling. Neither difference estimates strategy PnL or labels
any historical alert false.

Independent maxima remain a conservative scenario assumption. Joint scenarios
constrain that assumption and can miss unseen co-occurring extremes. Do not
assert universal numerical hurdle dominance: for positive LONG ratios
(mark ratio=.5,gap ratio=1) and(mark ratio=1,gap ratio=.0001), paired max K is
1.004900134956, while independent-extrema K is1.002450067478. The maintenance
term varies with stressed mark. This synthetic coefficient counterexample is
not evidence that such a state or price gap occurred in the historical source,
nor that it is reachable with any particular original wallet. It is retained
without adding new domain bounds or changing the original cost formula.
