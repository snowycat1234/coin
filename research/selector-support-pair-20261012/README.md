# Fixed training-date support pair

This parent-authorized continuation tests one hypothesis: with the same A46
features, Ridge30 learner, fixed expert pool and conditional paid-cost rewards,
does using all actually disjoint one-day owned intervals improve prediction over
the original conservative maturity-based thinning? It is an adaptation and a
seen-history development experiment, not a paper replication or native return.

Exactly two historical fits are frozen. Both train on truly complete rewards
before 2022-09-15, and predict the same natural 61-date October–November calendar.
OWNED_FULL must contain at least 600 distinct UTC dates with positive effective
data loss. The control may have approximately 305 dates. No shortened holding,
resampled validation, forced SHORT, alternative seed or recipe rescue is allowed.

Owned intervals remain `(decision+60000001us, decision+DAY+60000001us]`.
The funding event after the owned end is a separate completeness watermark;
it enters true reward maturity and is purged before fitting. Boundary funding
events belong to one reward only. This corrects date geometry without moving
publication clocks backwards. Support count is not independent information/ESS.

The previous 181-date experiment, four failed selector gates, default-account
paid-flat failure and finite-exit dust STOP are preserved. Native financial
reward certification remains BLOCKED: this daily quantity reference does not
implement the native wallet's capacity, minimum filters, exact charge prices,
historical margin tiers or terminal paid-flat behavior. No native wallet runs.

Source identities, protocol, interval tests and independent read-only review
are frozen before fits. Results, actual date IDs and zero-fit public artifact
verification will be saved in this directory. See PROTOCOL.json for the exact
MSE/CI gate and bounded resource limits.
