# D081 independent local read-only macro-entry filter review

Observed HEAD7a239eb7121885070147133fe2dfca72e857472e. CurrentAGENTS records D080 negative cost/risk result and permits one dailySMA200 macro-entry contrast. No Python/science/API/download/locked-body read or production edit performed by this reviewer.

## Predeclared mechanism and single changed factor
- Relative control is the complete D080 fixed4hDonchian/HOLDdaily-carry blend, not a newly rerun or retuned daily strategy. Change only the entry trend SMA context from200completed4hcloses to200completedDAILYcloses. Donchianprior20high, exit10priorlow, reentry20, strict predicates,4hdecision/execution,50/50targets,.10componentdailycov, fees/full10k/caps/band0 and terminal5remain unchanged.
- The vendor Donchian.filter_trend calls close>ma_trend and is referenced in filters; DailyDirection.should_long enforces filters on entry. Override only ma_trend, reusing originalshould_long/filterlogic. Exit10.update_position reads prior10lowerchannel only. A long position below dailySMA must remain open until the unchanged explicit channel/risk/terminal exit, never exit merely because the macrofilter fails.
- This is a new COINmulti-timeframe adaptation; identify the dailySMA filter explicitly and preserve originalvendor/sourceidentity. A successful result only supports this tested recipe and window, not generic filters or superiorityofslowstrategies.

## Daily context and causal checks
- For each4hdecisiond, riskdailycontext endpoint is floor(d/DAY)*DAY. Expose exactly last200completedconsecutive DAILYcandles with allavailability<=d, before the entryhook can read them.
- Candle matrix must retain six-column convention [open_ms,open,close,high,low,volume]; SMAusesclosecolumn2. Reuse the validated dailycontext rather than creating a separate differentlyindexed financialhistory.
- At04/08/...UTC the eventual currentdayclose is future; use prior completedday. At00UTC use the immediately completedday only when available. Missing/late dailycontext must preserveflat/reset or explicitwholeblendSTOP semantics, not bypass thefilter or silently impute.
- Optionaltrend1440 should be allowed only withsignal240 andriskdailycontext; defaultNone must retainD080semantics/output exactly. The normal1440default remains unchanged. Invalidtrendvalues/unsupportedpairs must rejectbefore anyaccount.

## Account/control and source reuse
- Reuse authenticatedD080 source_four_hour_bars, D077minutes/dailybars caches by explicitpath/SHA/bytes/rows. NoJulyredownload/reduction or4hcopy needed. Signalbaravailability allows targets to normalSpotentry at futureminuteopen; sourceclock remainsmicroseconds.
- Both newcostwallets36/52 use samefull10k/receivedassetfee/capacity/minimum/lot/terminal/caps asD080. Fullnewstrategy/accountreplay isrequired; cannotremovepriorlosstradeswhileholdingoldgrossreturn.
- Macrofilter changes actualentryavailability, holdings andassetcapitalcompetition. Actualriskmaydifferdespitesamerisksettings. Reportnet/gross/fee/exec, dailyvol/minuteDD/grossnet/turnover andretaineddust. Lowercostthroughlowerexposureisnotnecessarilygreateralpha.
- PriorD08040signalepisodes and~78%signalchangecosts motivatedthishypothesis; theyaredevelopmentdiagnosis,notcausalprooforindependentsamples. Do notpromotethese303seendays toOOS/stableAPR.

## New-path required evidence
- Minimal counterexample: current4hclose above4hSMA but belowdailySMA, breaking prior20channel; defaultenters andmacrodoesnot. Oppositecondition should follow dailyfilter, not mixtureofbothSMAs.
- Heldlong crossing belowdailySMA withoutprior10exit mustremainheld; explicitprior10exit stillworks. Flattoentryrequiresfilter eachfreshentry/reentry.
- Futurecurrentday/futuredailyOHLCV perturbation mustnotalterearlier4hprefix. Verify200dailyqualification, floorclock/lateavailability andcandleschema.
- Independent scalaractualtargetreference should calculate daily200mean fromrawsaved dailycloses and4hchannelstate; avoidcalling productionma_trend/property/sharedtargetkernel as soleindependentproof. Then independentlyrebuild actualreceivedassetcash/base/fees/fullminuteNAV/risk.
- Adoptioncriterionbeforeexecution: netimprovesatbothcosts andactualdailyvol/minuteDDdonotworsenagainstD080; otherwisepause thistestedmacrorecipe/retainestablishedreferences. Positiveoutcomeisadevelopmentchallengeronly; investmentNONE/CASH/longtermAPRNOT_EVALUABLE.
## Actual four-file normal source diff review
- Reviewed shared target, Donchian, blend and normal Spot runner diffs after source implementation. No static causal, accounting or execution blocker found.
- Shared240context adds a six-column dailycandlematrix using [open_ms,open,close,high,low,volume]. Only after the existing floor-day200-consecutive/availability checks pass does it expose candles[rf:ri+1] and completed_daily_close_us to the hook. Signals remain4h; riskcloses/covariance remaindaily.
- DailyTrendDirection overrides ma_trend only. Original vendorfilter_trend and filters are unchanged, DailyDirection.should_long still enforces them, and Exit10Direction inherits the chosen direction while itsupdate_position checks only prior10low. Thus dailySMA does not create an extra heldpositionexit.
- trend_filter_interval_minutes None follows priorD080directionclass/targetmath. Explicit1440 requires240signal, rejecting unsupportedpairs. Shared dailydefaults/finance/account code are untouched.
- New runner recipe HALF_HOLD10_EXIT10_4H_DAILY_TREND authenticates D080controlfour_hour_bars via STATEpath/no-symlink/bytes/SHA/rows, verifies control240signal/1440risk and reuses the artifact without copying/reducingJuly. Samecached daily/minutepricepath,3636targets/twocostwallets/band0/terminal5 and normalreceivedassetaccount remain.
- Active product ID and mathID are preserved distinctly; dailyentryfilter-only attribution versus same4hcontrol is explicit. Component rule metadata updates the actualDonchian DAILY_TREND identity and trendtimeframe.
- Required runtime evidence remains defaultNoneactualD080prefix/equality, freshentryfiltercounterexample, heldlongfiltercrosswithoutchannelexit, future/currentunfinisheddailyperturbation, independentactualtarget/ledger reconstruction and own fullminute observedcaps. Static review is not market/account acceptance.