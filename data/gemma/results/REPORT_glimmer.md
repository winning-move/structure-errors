# Results: arm gemma, categories from judge glimmer

## Sample and integrity

- Organizations: hierarchy 84, polyarchy 84; proposals classified 2016, unscored 0, unclassified 0; organizations with fewer than 12 classified slots 0; proposals with one judge pass 0; missing votes 0.
- Readings by judge glimmer (PROTOCOL 4.4): 4 readings (the floor) (floor 4, ceiling 8, target 0.8); single-reading ICC(1,1) {"novelty": 0.843, "workability": 0.671, "relevance": 0.747}.
- Category rates (threshold 6.0 on the 2-8 scale): quality 0.809 (of which creative 0.077), below the quality threshold 0.191; novel 0.122 (novel but below 0.045). Share of proposals at the threshold: {"novelty": {"exactly": 0.064484, "within_half_point": 0.147321}, "workability": {"exactly": 0.061508, "within_half_point": 0.195933}, "relevance": {"exactly": 0.047123, "within_half_point": 0.174107}}.
- Approval rates of categorized proposals: {"quality_rule4": 0.022072, "quality_rule1": 0.976701, "creative_rule4": 0.012821, "creative_rule1": 0.833333, "below_rule4": 0.020779, "below_rule1": 0.893506, "all_rule4": 0.021825, "all_rule1": 0.960813}.
- Internal pilot, quality (PROTOCOL 6.4, at alpha 0.0500): category rate 0.809, approval rates 0.977 (one of four) and 0.022 (four of four), dispersion phi 0.69 (used 0.69); simulated power of H2 at n = 84: 1.000.
- Internal pilot, below (PROTOCOL 6.4, at alpha 0.0500): category rate 0.191, approval rates 0.894 (one of four) and 0.021 (four of four), dispersion phi 0.69 (used 0.69); simulated power of H2 at n = 84: 1.000.
- Dispersion of counts written over binomial (phi): {"quality_hierarchy": 0.823615, "quality_polyarchy": 0.550823, "creative_hierarchy": 0.794371, "creative_polyarchy": 0.565119, "below_hierarchy": 0.823615, "below_polyarchy": 0.550823}; correlation of novelty with relevance: -0.158, with workability: -0.604.

## Registered tests (hierarchy minus polyarchy; each at alpha .05, no correction)

| | estimate | 95% CI | d | p | verdict |
|---|---|---|---|---|---|
| H1 below-threshold proportion generated (= 1 - quality proportion) | 0.009 | [-0.020, 0.038] | 0.09 | 0.5400 | not supported |
| H2a quality proposals approved per proposal, own rule | -0.769 | [-0.790, -0.748] | -11.08 | 0.0000 | supported |
| H2b below-threshold proposals approved per proposal, own rule | -0.167 | [-0.186, -0.148] | -2.67 | 0.0000 | supported |

H1 secondary equivalence (bound 0.047): p = 0.0047, equivalent = True.
- H2a_quality: decomposition (reported) H2 difference -0.769 = generation part 0.003 + rule part -0.772; bootstrap 95% {"h2_difference": [-0.789683, -0.748016], "generation_part": [-0.011905, 0.018849], "rule_part": [-0.788194, -0.756944]}; cells {"hierarchy_rule4": 0.321429, "hierarchy_rule1": 9.416667, "polyarchy_rule4": 0.107143, "polyarchy_rule1": 9.547619}.
- H2b_below: decomposition (reported) H2 difference -0.167 = generation part 0.000 + rule part -0.167; bootstrap 95% {"h2_difference": [-0.185516, -0.147817], "generation_part": [-0.015377, 0.014893], "rule_part": [-0.181052, -0.152778]}; cells {"hierarchy_rule4": 0.059524, "hierarchy_rule1": 2.035714, "polyarchy_rule4": 0.035714, "polyarchy_rule1": 2.059524}.

## Reported, not tested: the two rules on the same votes

| per organization, proportion approved under four of four minus under one of four | mean | 95% CI | bootstrap 95% | organizations |
|---|---|---|---|---|
| quality proposals | -0.955 | [-0.966, -0.944] | [-0.965, -0.944] | 168 |
| below-threshold proposals | -0.870 | [-0.906, -0.834] | [-0.904, -0.834] | 163 |

Approval rates by rule: {"quality_approved_rule4": 0.022072, "quality_approved_rule1": 0.976701, "creative_approved_rule4": 0.012821, "creative_approved_rule1": 0.833333, "below_approved_rule4": 0.020779, "below_approved_rule1": 0.893506}. per organization, the proportion of its quality (below-threshold) proposals with complete votes approved under four of four minus the proportion approved under one of four, mean over organizations with a 95% interval; both rules read the same four votes, so the difference is never positive: a benchmark, not a hypothesis


Attrition (PROTOCOL 8.3): overall 0.0%, differential 0.0 points (cautious WWC bound 5.7); low attrition.
Failure rate by structure (Haldane estimator for sampling to a fixed number of completions): hierarchy 0.000 (naive 0.000), polyarchy 0.000 (naive 0.000).

| Lee bounds on the structure contrast (trimming the group with more completions) | lower | upper | trimmed | share |
|---|---|---|---|---|
| H1 | 0.009 | 0.009 | none | 0.000 |
| H2a | -0.769 | -0.769 | none | 0.000 |
| H2b | -0.167 | -0.167 | none | 0.000 |

| Call log | attempts | content failures | rate | first-attempt failures | outcomes from a retry | exhausted |
|---|---|---|---|---|---|---|
| calls_evaluation_qwen38.jsonl | 8065 | 1 | 0.000 | 1 of 8064 | 1 | 0 |
| calls_generation.jsonl | 672 | 0 | 0.000 | 0 of 672 | 0 | 0 |
| calls_judge_claude.jsonl | 8064 | 0 | 0.000 | 0 of 8064 | 0 | 0 |
| calls_judge_glimmer.jsonl | 8064 | 0 | 0.000 | 0 of 8064 | 0 | 0 |

## Secondary (PROTOCOL 7.4)

```json
{
 "permutation_within_blocks": {
  "H1_below_share": {
   "diff": 0.008929,
   "p_permutation": 0.585441,
   "B": 10000
  },
  "creative_share": {
   "diff": 0.003968,
   "p_permutation": 0.770923,
   "B": 10000
  }
 },
 "creative_share": {
  "mean_hierarchy": 0.079365,
  "mean_polyarchy": 0.075397,
  "diff": 0.003968,
  "se": 0.009832,
  "t": 0.403615,
  "df": 160.135793,
  "p": 0.687035,
  "ci95": [
   -0.015448,
   0.023385
  ],
  "d": 0.062279,
  "sd_pooled": 0.063717,
  "n_hierarchy": 84,
  "n_polyarchy": 84
 },
 "lpm_cluster_H1": {
  "diff": 0.008929,
  "se": 0.014499,
  "t": 0.615799,
  "df": 167,
  "p": 0.538866
 },
 "lpm_cluster_creative": {
  "diff": 0.003968,
  "se": 0.009805,
  "t": 0.404728,
  "df": 167,
  "p": 0.686195
 },
 "novel_and_cells": {
  "novel_share": {
   "mean_hierarchy": 0.133929,
   "mean_polyarchy": 0.110119,
   "diff": 0.02381,
   "se": 0.009797,
   "t": 2.430349,
   "df": 161.699392,
   "p": 0.016178,
   "ci95": [
    0.004463,
    0.043156
   ],
   "d": 0.375011,
   "sd_pooled": 0.06349,
   "n_hierarchy": 84,
   "n_polyarchy": 84
  },
  "novel_approved_own_rule_per_proposal": {
   "mean_hierarchy": 0.001984,
   "mean_polyarchy": 0.092262,
   "diff": -0.090278,
   "se": 0.005645,
   "t": -15.993614,
   "df": 93.744929,
   "p": 0.0,
   "ci95": [
    -0.101486,
    -0.07907
   ],
   "d": -2.467868,
   "sd_pooled": 0.036581,
   "n_hierarchy": 84,
   "n_polyarchy": 84
  },
  "cells_quality_by_novelty": {
   "hierarchy": {
    "creative (quality and novel)": 0.079365,
    "quality, not novel": 0.725198,
    "novel, below the quality threshold": 0.054563,
    "neither": 0.140873,
    "n_proposals": 1008
   },
   "polyarchy": {
    "creative (quality and novel)": 0.075397,
    "quality, not novel": 0.738095,
    "novel, below the quality threshold": 0.034722,
    "neither": 0.151786,
    "n_proposals": 1008
   }
  }
 },
 "creative_yield_own_rule": {
  "mean_hierarchy": 0.000992,
  "mean_polyarchy": 0.063492,
  "diff": -0.0625,
  "se": 0.005302,
  "t": -11.787286,
  "df": 89.013939,
  "p": 0.0,
  "ci95": [
   -0.073036,
   -0.051964
  ],
  "d": -1.818818,
  "sd_pooled": 0.034363,
  "n_hierarchy": 84,
  "n_polyarchy": 84
 },
 "placebo_first_role": {
  "role": "compliance",
  "below_share": {
   "mean_hierarchy": 0.206349,
   "mean_polyarchy": 0.202381,
   "diff": 0.003968,
   "se": 0.026434,
   "t": 0.15012,
   "df": 165.995582,
   "p": 0.880852,
   "ci95": [
    -0.048222,
    0.056158
   ],
   "d": 0.023164,
   "sd_pooled": 0.171311,
   "n_hierarchy": 84,
   "n_polyarchy": 84
  },
  "creative_share": {
   "mean_hierarchy": 0.019841,
   "mean_polyarchy": 0.011905,
   "diff": 0.007937,
   "se": 0.011002,
   "t": 0.721371,
   "df": 157.08385,
   "p": 0.471754,
   "ci95": [
    -0.013794,
    0.029667
   ],
   "d": 0.11131,
   "sd_pooled": 0.071301,
   "n_hierarchy": 84,
   "n_polyarchy": 84
  }
 },
 "leakage": {
  "pattern": "\\b(colleague|colleagues|stance|senior colleague|senior colleagues|as the (compliance officer|lab director|director|researcher) (noted|notes|argued|argues|said|says|suggested|suggests|proposed|proposes|emphasized|emphasizes|stressed|stresses|recommended|recommends|pointed out|points out))\\b",
  "n_flagged": 0,
  "share_juniors_hierarchy": 0.0,
  "share_juniors_polyarchy": 0.0,
  "share_first_role": 0.0
 },
 "H1_without_flagged": {
  "mean_hierarchy": 0.195437,
  "mean_polyarchy": 0.186508,
  "diff": 0.008929,
  "se": 0.014539,
  "t": 0.614105,
  "df": 158.628344,
  "p": 0.540026,
  "ci95": [
   -0.019787,
   0.037644
  ],
  "d": 0.094758,
  "sd_pooled": 0.094225,
  "n_hierarchy": 84,
  "n_polyarchy": 84
 },
 "creative_share_without_flagged": {
  "mean_hierarchy": 0.079365,
  "mean_polyarchy": 0.075397,
  "diff": 0.003968,
  "se": 0.009832,
  "t": 0.403615,
  "df": 160.135793,
  "p": 0.687035,
  "ci95": [
   -0.015448,
   0.023385
  ],
  "d": 0.062279,
  "sd_pooled": 0.063717,
  "n_hierarchy": 84,
  "n_polyarchy": 84
 },
 "dispersion_kept_given_written_quality_rule4": 1.030495,
 "dispersion_kept_given_written_below_rule4": 0.943643,
 "stance_check": {
  "hierarchy": {
   "corr_junior_with_mean_senior": 0.256303,
   "mean_within_org_sd": 7.267966
  },
  "polyarchy": {
   "corr_junior_with_mean_senior": -0.127788,
   "mean_within_org_sd": 5.293231
  }
 },
 "stance_within_org_sd_welch": {
  "mean_hierarchy": 7.267966,
  "mean_polyarchy": 5.293231,
  "diff": 1.974735,
  "se": 0.25769,
  "t": 7.663217,
  "df": 154.588042,
  "p": 0.0,
  "ci95": [
   1.465687,
   2.483783
  ],
  "d": 1.18246,
  "sd_pooled": 1.670023,
  "n_hierarchy": 84,
  "n_polyarchy": 84
 },
 "reasoning_words_mean": {
  "hierarchy": 68.657738,
  "polyarchy": 65.842262
 },
 "manipulation_check": {
  "mean_hierarchy": 8.257275,
  "mean_polyarchy": 5.810185,
  "diff": 2.44709,
  "se": 0.314989,
  "t": 7.768819,
  "df": 158.191498,
  "p": 0.0,
  "ci95": [
   1.824964,
   3.069216
  ],
  "d": 1.198755,
  "sd_pooled": 2.04136,
  "n_hierarchy": 84,
  "n_polyarchy": 84,
  "verdict": "reversal"
 },
 "proposal_length": {
  "words_per_proposal_mean": {
   "hierarchy": 69.699405,
   "polyarchy": 74.625992
  },
  "welch_mean_length": {
   "mean_hierarchy": 69.699405,
   "mean_polyarchy": 74.625992,
   "diff": -4.926587,
   "se": 0.714916,
   "t": -6.891141,
   "df": 161.717058,
   "p": 0.0,
   "ci95": [
    -6.338362,
    -3.514813
   ],
   "d": -1.063326,
   "sd_pooled": 4.633186,
   "n_hierarchy": 84,
   "n_polyarchy": 84
  },
  "corr_length_with_dimension": {
   "novelty": 0.071146,
   "workability": -0.086502,
   "relevance": 0.072531
  },
  "H1_below_share_with_length_covariate": {
   "structure_coef": 0.001549,
   "se_hc2": 0.017301,
   "t": 0.089532,
   "p": 0.928768,
   "length_coef": -0.001498,
   "df": 165
  },
  "creative_share_with_length_covariate": {
   "structure_coef": 0.002602,
   "se_hc2": 0.011564,
   "t": 0.224983,
   "p": 0.822271,
   "length_coef": -0.000277,
   "df": 165
  },
  "words_by_structure": {
   "hierarchy": {
    "n": 1008,
    "mean": 69.699405,
    "percentiles": {
     "5": 56.0,
     "25": 61.0,
     "50": 69.0,
     "75": 78.0,
     "95": 86.0
    },
    "share_in_60_to_110": 0.810516
   },
   "polyarchy": {
    "n": 1008,
    "mean": 74.625992,
    "percentiles": {
     "5": 58.35,
     "25": 68.0,
     "50": 76.0,
     "75": 81.0,
     "95": 88.0
    },
    "share_in_60_to_110": 0.929563
   }
  }
 },
 "classification_sensitivity": {
  "thresholds": {
   "5.0": {
    "H1": {
     "mean_hierarchy": 0.0625,
     "mean_polyarchy": 0.049603,
     "diff": 0.012897,
     "se": 0.010079,
     "t": 1.279582,
     "df": 149.82368,
     "p": 0.20267,
     "ci95": [
      -0.007018,
      0.032812
     ],
     "d": 0.197444,
     "sd_pooled": 0.065319,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "creative_share": {
     "mean_hierarchy": 0.204365,
     "mean_polyarchy": 0.189484,
     "diff": 0.014881,
     "se": 0.011872,
     "t": 1.253413,
     "df": 165.860287,
     "p": 0.211819,
     "ci95": [
      -0.008559,
      0.038321
     ],
     "d": 0.193406,
     "sd_pooled": 0.076942,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "H2a_quality": {
     "mean_hierarchy": 0.030754,
     "mean_polyarchy": 0.920635,
     "diff": -0.889881,
     "se": 0.009435,
     "t": -94.318803,
     "df": 140.299341,
     "p": 0.0,
     "ci95": [
      -0.908534,
      -0.871228
     ],
     "d": -14.553707,
     "sd_pooled": 0.061145,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "H2b_below": {
     "mean_hierarchy": 0.000992,
     "mean_polyarchy": 0.046627,
     "diff": -0.045635,
     "se": 0.005793,
     "t": -7.877777,
     "df": 88.011079,
     "p": 0.0,
     "ci95": [
      -0.057147,
      -0.034123
     ],
     "d": -1.215567,
     "sd_pooled": 0.037542,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "rule_comparison_quality": {
     "mean": -0.939071,
     "se": 0.005302,
     "t": -177.121676,
     "df": 167,
     "p": 0.0,
     "ci95": [
      -0.949538,
      -0.928603
     ],
     "n_proposals": 1903,
     "n_organizations": 168
    },
    "rule_comparison_below": {
     "mean": -0.953488,
     "se": 0.019813,
     "t": -48.12495,
     "df": 85,
     "p": 0.0,
     "ci95": [
      -0.992881,
      -0.914095
     ],
     "n_proposals": 113,
     "n_organizations": 86
    },
    "category_rates": {
     "quality": 0.943948,
     "creative": 0.196925,
     "below": 0.056052,
     "novel": 0.202381
    }
   },
   "7.0": {
    "H1": {
     "mean_hierarchy": 0.518849,
     "mean_polyarchy": 0.532738,
     "diff": -0.013889,
     "se": 0.018638,
     "t": -0.745208,
     "df": 165.92663,
     "p": 0.4572,
     "ci95": [
      -0.050686,
      0.022909
     ],
     "d": -0.114988,
     "sd_pooled": 0.120785,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "creative_share": {
     "mean_hierarchy": 0.0,
     "mean_polyarchy": 0.0,
     "diff": 0.0,
     "se": 0.0,
     "t": null,
     "df": null,
     "p": null,
     "ci95": [
      null,
      null
     ],
     "d": null,
     "sd_pooled": 0.0,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "H2a_quality": {
     "mean_hierarchy": 0.012897,
     "mean_polyarchy": 0.46627,
     "diff": -0.453373,
     "se": 0.013656,
     "t": -33.199558,
     "df": 95.305633,
     "p": 0.0,
     "ci95": [
      -0.480482,
      -0.426264
     ],
     "d": -5.122803,
     "sd_pooled": 0.088501,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "H2b_below": {
     "mean_hierarchy": 0.018849,
     "mean_polyarchy": 0.500992,
     "diff": -0.482143,
     "se": 0.014452,
     "t": -33.361558,
     "df": 97.259855,
     "p": 0.0,
     "ci95": [
      -0.510825,
      -0.453461
     ],
     "d": -5.1478,
     "sd_pooled": 0.09366,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "rule_comparison_quality": {
     "mean": -0.977435,
     "se": 0.005335,
     "t": -183.215119,
     "df": 167,
     "p": 0.0,
     "ci95": [
      -0.987968,
      -0.966903
     ],
     "n_proposals": 956,
     "n_organizations": 168
    },
    "rule_comparison_below": {
     "mean": -0.907315,
     "se": 0.008658,
     "t": -104.799452,
     "df": 167,
     "p": 0.0,
     "ci95": [
      -0.924408,
      -0.890223
     ],
     "n_proposals": 1060,
     "n_organizations": 168
    },
    "category_rates": {
     "quality": 0.474206,
     "creative": 0.0,
     "below": 0.525794,
     "novel": 0.003968
    }
   }
  },
  "continuous": {
   "H1_shortfall_score": {
    "mean_hierarchy": 1.560268,
    "mean_polyarchy": 1.557044,
    "diff": 0.003224,
    "se": 0.02685,
    "t": 0.120084,
    "df": 164.600505,
    "p": 0.904563,
    "ci95": [
     -0.04979,
     0.056238
    ],
    "d": 0.018529,
    "sd_pooled": 0.174006,
    "n_hierarchy": 84,
    "n_polyarchy": 84
   },
   "creative_novelty_score": {
    "mean_hierarchy": 3.861111,
    "mean_polyarchy": 3.788442,
    "diff": 0.072669,
    "se": 0.032326,
    "t": 2.248008,
    "df": 164.873189,
    "p": 0.025901,
    "ci95": [
     0.008843,
     0.136495
    ],
    "d": 0.346875,
    "sd_pooled": 0.209495,
    "n_hierarchy": 84,
    "n_polyarchy": 84
   },
   "H2a_quality_score": {
    "mean_hierarchy": 0.206349,
    "mean_polyarchy": 6.252232,
    "diff": -6.045883,
    "se": 0.048937,
    "t": -123.544287,
    "df": 165.213172,
    "p": 0.0,
    "ci95": [
     -6.142505,
     -5.94926
    ],
    "d": -19.063297,
    "sd_pooled": 0.317148,
    "n_hierarchy": 84,
    "n_polyarchy": 84
   },
   "H2b_shortfall_score": {
    "mean_hierarchy": 0.047619,
    "mean_polyarchy": 1.485863,
    "diff": -1.438244,
    "se": 0.0215,
    "t": -66.894545,
    "df": 110.153238,
    "p": 0.0,
    "ci95": [
     -1.480852,
     -1.395636
    ],
    "d": -10.322052,
    "sd_pooled": 0.139337,
    "n_hierarchy": 84,
    "n_polyarchy": 84
   },
   "rule_comparison_quality_score": {
    "mean": -72.860119,
    "se": 0.41702,
    "t": -174.716305,
    "df": 167,
    "p": 0.0,
    "ci95": [
     -73.683429,
     -72.036809
    ],
    "n": 168
   }
  }
 },
 "mediation_imai": {
  "H2a_quality": {
   "acme_hierarchy": -0.000161,
   "acme_polyarchy": -0.008469,
   "ade_hierarchy": -0.76038,
   "ade_polyarchy": -0.768689,
   "total": -0.768849,
   "acme_hierarchy_ci95": [
    -0.001801,
    0.001448
   ],
   "acme_polyarchy_ci95": [
    -0.035302,
    0.018973
   ],
   "ade_hierarchy_ci95": [
    -0.781987,
    -0.737304
   ],
   "ade_polyarchy_ci95": [
    -0.789329,
    -0.747063
   ],
   "total_ci95": [
    -0.788715,
    -0.747024
   ],
   "interaction_slope_difference": -0.930515,
   "no_interaction": {
    "acme": -0.003419,
    "ade": -0.76543,
    "total": -0.768849,
    "acme_ci95": [
     -0.013831,
     0.008044
    ],
    "ade_ci95": [
     -0.782527,
     -0.74787
    ]
   },
   "sensitivity_rho_at_zero_acme": 0.519942,
   "acme_at_rho": {
    "-0.4": -0.005871,
    "-0.2": -0.004566,
    "0.0": -0.003419,
    "0.2": -0.002273,
    "0.4": -0.000968
   }
  },
  "H2b_below": {
   "acme_hierarchy": 0.000434,
   "acme_polyarchy": 0.008561,
   "ade_hierarchy": -0.175227,
   "ade_polyarchy": -0.167101,
   "total": -0.166667,
   "acme_hierarchy_ci95": [
    -0.000945,
    0.002267
   ],
   "acme_polyarchy_ci95": [
    -0.018377,
    0.034767
   ],
   "ade_hierarchy_ci95": [
    -0.196856,
    -0.154309
   ],
   "ade_polyarchy_ci95": [
    -0.184798,
    -0.149095
   ],
   "total_ci95": [
    -0.184549,
    -0.147817
   ],
   "interaction_slope_difference": -0.910171,
   "no_interaction": {
    "acme": 0.003622,
    "ade": -0.170288,
    "total": -0.166667,
    "acme_ci95": [
     -0.008007,
     0.014088
    ],
    "ade_ci95": [
     -0.185568,
     -0.155096
    ]
   },
   "sensitivity_rho_at_zero_acme": 0.611414,
   "acme_at_rho": {
    "-0.4": 0.005667,
    "-0.2": 0.004578,
    "0.0": 0.003622,
    "0.2": 0.002665,
    "0.4": 0.001576
   }
  }
 },
 "judge_pass_reliability": {
  "passes": 4,
  "n_all_passes": 2016,
  "r12_novelty": 0.840996,
  "icc1_novelty": {
   "icc1_1": 0.84273,
   "icc1_k": 0.955425,
   "n": 2016,
   "k": 4
  },
  "r12_workability": 0.681704,
  "icc1_workability": {
   "icc1_1": 0.671002,
   "icc1_k": 0.890807,
   "n": 2016,
   "k": 4
  },
  "r12_relevance": 0.74273,
  "icc1_relevance": {
   "icc1_1": 0.746741,
   "icc1_k": 0.921839,
   "n": 2016,
   "k": 4
  },
  "split_half_kappa_three_way": 0.700748,
  "split_half_kappa_creative": 0.682229,
  "split_half_kappa_below": 0.614847
 },
 "attrition_and_fallbacks": {
  "failed_organizations": {
   "hierarchy": 0,
   "polyarchy": 0
  },
  "attrition": {
   "overall_pct": 0.0,
   "differential_pct_points": 0.0,
   "rate_by_structure_pct": {
    "hierarchy": 0.0,
    "polyarchy": 0.0
   },
   "wwc_cautious_bound_pct_points": 5.7,
   "low_attrition": true
  },
  "failure_rate_haldane": {
   "hierarchy": {
    "completed": 84,
    "failed": 0,
    "run": 84,
    "naive": 0.0,
    "haldane": 0.0
   },
   "polyarchy": {
    "completed": 84,
    "failed": 0,
    "run": 84,
    "naive": 0.0,
    "haldane": 0.0
   }
  },
  "attempts": {
   "calls_evaluation_qwen38.jsonl": {
    "attempts_completed": 8065,
    "content_failures": 1,
    "content_failure_rate": 0.000124,
    "first_attempts": 8064,
    "first_attempt_failures": 1,
    "valid_outcomes": 8064,
    "outcomes_from_a_retry": 1,
    "exhausted_logical_calls": 0,
    "failure_reasons": {
     "invalid: stop_reason=length": 1
    },
    "by_structure": null,
    "audit_file": "results/failed_attempts_calls_evaluation_qwen38.jsonl"
   },
   "calls_generation.jsonl": {
    "attempts_completed": 672,
    "content_failures": 0,
    "content_failure_rate": 0.0,
    "first_attempts": 672,
    "first_attempt_failures": 0,
    "valid_outcomes": 672,
    "outcomes_from_a_retry": 0,
    "exhausted_logical_calls": 0,
    "failure_reasons": {},
    "by_structure": {
     "polyarchy": {
      "attempts": 336,
      "content_failures": 0
     },
     "hierarchy": {
      "attempts": 336,
      "content_failures": 0
     }
    }
   },
   "calls_judge_claude.jsonl": {
    "attempts_completed": 8064,
    "content_failures": 0,
    "content_failure_rate": 0.0,
    "first_attempts": 8064,
    "first_attempt_failures": 0,
    "valid_outcomes": 8064,
    "outcomes_from_a_retry": 0,
    "exhausted_logical_calls": 0,
    "failure_reasons": {},
    "by_structure": null
   },
   "calls_judge_glimmer.jsonl": {
    "attempts_completed": 8064,
    "content_failures": 0,
    "content_failure_rate": 0.0,
    "first_attempts": 8064,
    "first_attempt_failures": 0,
    "valid_outcomes": 8064,
    "outcomes_from_a_retry": 0,
    "exhausted_logical_calls": 0,
    "failure_reasons": {},
    "by_structure": null
   }
  },
  "single_mode_proposals_evaluation": {
   "hierarchy": 0,
   "polyarchy": 0
  },
  "single_mode_proposals_judge": {
   "hierarchy": 0,
   "polyarchy": 0
  }
 },
 "judge_pass_reliability_claude": {
  "passes": 4,
  "n_all_passes": 2016,
  "r12_novelty": 0.871615,
  "icc1_novelty": {
   "icc1_1": 0.874034,
   "icc1_k": 0.965223,
   "n": 2016,
   "k": 4
  },
  "r12_workability": 0.76013,
  "icc1_workability": {
   "icc1_1": 0.764897,
   "icc1_k": 0.928642,
   "n": 2016,
   "k": 4
  },
  "r12_relevance": 0.811947,
  "icc1_relevance": {
   "icc1_1": 0.810587,
   "icc1_k": 0.944806,
   "n": 2016,
   "k": 4
  },
  "split_half_kappa_three_way": 0.71298,
  "split_half_kappa_creative": 0.492063,
  "split_half_kappa_below": 0.712224
 },
 "judge_agreement_with_claude": {
  "n": 2016,
  "r_novelty": 0.890068,
  "icc_novelty": {
   "icc_c1": 0.889351,
   "icc_a1": 0.771226,
   "n": 2016
  },
  "r_disattenuated_novelty": 0.926854,
  "r_workability": 0.738931,
  "icc_workability": {
   "icc_c1": 0.681496,
   "icc_a1": 0.628279,
   "n": 2016
  },
  "r_disattenuated_workability": 0.812434,
  "r_relevance": 0.697039,
  "icc_relevance": {
   "icc_c1": 0.596105,
   "icc_a1": 0.548021,
   "n": 2016
  },
  "r_disattenuated_relevance": 0.746892,
  "kappa_three_way": 0.389529,
  "kappa_creative": 0.147267,
  "kappa_below": 0.352001,
  "agreement_three_way": 0.793155
 },
 "evaluator_agreement_among_roles": {
  "n": 2016,
  "fleiss_kappa_roles": -0.069323,
  "share_disagree": 0.938988,
  "kappa_by_pair": {
   "compliance-director": 0.547757,
   "compliance-engineer": 0.459553,
   "compliance-researcher": -0.15024,
   "director-engineer": 0.443059,
   "director-researcher": -0.141263,
   "engineer-researcher": -0.188312
  }
 }
}
```
