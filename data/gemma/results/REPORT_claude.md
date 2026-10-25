# Results: arm gemma, categories from judge claude

## Sample and integrity

- Organizations: hierarchy 84, polyarchy 84; proposals classified 2016, unscored 0, unclassified 0; organizations with fewer than 12 classified slots 0; proposals with one judge pass 0; missing votes 0.
- Readings by judge claude (PROTOCOL 4.4): 4 readings (the floor) (floor 4, ceiling 8, target 0.8); single-reading ICC(1,1) {"novelty": 0.874, "workability": 0.765, "relevance": 0.811}.
- Category rates (threshold 6.0 on the 2-8 scale): quality 0.880 (of which creative 0.009), below the quality threshold 0.120; novel 0.052 (novel but below 0.043). Share of proposals at the threshold: {"novelty": {"exactly": 0.046131, "within_half_point": 0.069444}, "workability": {"exactly": 0.022817, "within_half_point": 0.105655}, "relevance": {"exactly": 0.309524, "within_half_point": 0.447917}}.
- Approval rates of categorized proposals: {"quality_rule4": 0.023099, "quality_rule1": 0.980845, "creative_rule4": 0.055556, "creative_rule1": 1.0, "below_rule4": 0.012448, "below_rule1": 0.813278, "all_rule4": 0.021825, "all_rule1": 0.960813}.
- Internal pilot, quality (PROTOCOL 6.4, at alpha 0.0500): category rate 0.880, approval rates 0.981 (one of four) and 0.023 (four of four), dispersion phi 0.56 (used 0.66); simulated power of H2 at n = 84: 1.000.
- Internal pilot, below (PROTOCOL 6.4, at alpha 0.0500): category rate 0.120, approval rates 0.813 (one of four) and 0.012 (four of four), dispersion phi 0.56 (used 0.66); simulated power of H2 at n = 84: 1.000.
- Dispersion of counts written over binomial (phi): {"quality_hierarchy": 0.683714, "quality_polyarchy": 0.433275, "creative_hierarchy": 0.889222, "creative_polyarchy": 0.934198, "below_hierarchy": 0.683714, "below_polyarchy": 0.433275}; correlation of novelty with relevance: -0.465, with workability: -0.676.

## Registered tests (hierarchy minus polyarchy; each at alpha .05, no correction)

| | estimate | 95% CI | d | p | verdict |
|---|---|---|---|---|---|
| H1 below-threshold proportion generated (= 1 - quality proportion) | 0.013 | [-0.009, 0.034] | 0.18 | 0.2366 | not supported |
| H2a quality proposals approved per proposal, own rule | -0.842 | [-0.859, -0.826] | -15.33 | 0.0000 | supported |
| H2b below-threshold proposals approved per proposal, own rule | -0.093 | [-0.107, -0.079] | -2.08 | 0.0000 | supported |

H1 secondary equivalence (bound 0.035): p = 0.0209, equivalent = True.
- H2a_quality: decomposition (reported) H2 difference -0.842 = generation part 0.001 + rule part -0.843; bootstrap 95% {"h2_difference": [-0.858135, -0.825397], "generation_part": [-0.011905, 0.014385], "rule_part": [-0.854663, -0.831845]}; cells {"hierarchy_rule4": 0.357143, "hierarchy_rule1": 10.261905, "polyarchy_rule4": 0.130952, "polyarchy_rule1": 10.464286}.
- H2b_below: decomposition (reported) H2 difference -0.093 = generation part 0.002 + rule part -0.096; bootstrap 95% {"h2_difference": [-0.107143, -0.079365], "generation_part": [-0.007937, 0.012897], "rule_part": [-0.105655, -0.085813]}; cells {"hierarchy_rule4": 0.02381, "hierarchy_rule1": 1.190476, "polyarchy_rule4": 0.011905, "polyarchy_rule1": 1.142857}.

## Reported, not tested: the two rules on the same votes

| per organization, proportion approved under four of four minus under one of four | mean | 95% CI | bootstrap 95% | organizations |
|---|---|---|---|---|
| quality proposals | -0.959 | [-0.968, -0.950] | [-0.967, -0.950] | 168 |
| below-threshold proposals | -0.801 | [-0.856, -0.747] | [-0.853, -0.747] | 150 |

Approval rates by rule: {"quality_approved_rule4": 0.023099, "quality_approved_rule1": 0.980845, "creative_approved_rule4": 0.055556, "creative_approved_rule1": 1.0, "below_approved_rule4": 0.012448, "below_approved_rule1": 0.813278}. per organization, the proportion of its quality (below-threshold) proposals with complete votes approved under four of four minus the proportion approved under one of four, mean over organizations with a 95% interval; both rules read the same four votes, so the difference is never positive: a benchmark, not a hypothesis


Attrition (PROTOCOL 8.3): overall 0.0%, differential 0.0 points (cautious WWC bound 5.7); low attrition.
Failure rate by structure (Haldane estimator for sampling to a fixed number of completions): hierarchy 0.000 (naive 0.000), polyarchy 0.000 (naive 0.000).

| Lee bounds on the structure contrast (trimming the group with more completions) | lower | upper | trimmed | share |
|---|---|---|---|---|
| H1 | 0.013 | 0.013 | none | 0.000 |
| H2a | -0.842 | -0.842 | none | 0.000 |
| H2b | -0.093 | -0.093 | none | 0.000 |

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
   "diff": 0.012897,
   "p_permutation": 0.289971,
   "B": 10000
  },
  "creative_share": {
   "diff": 0.003968,
   "p_permutation": 0.447455,
   "B": 10000
  }
 },
 "creative_share": {
  "mean_hierarchy": 0.010913,
  "mean_polyarchy": 0.006944,
  "diff": 0.003968,
  "se": 0.003989,
  "t": 0.99477,
  "df": 159.815265,
  "p": 0.321352,
  "ci95": [
   -0.00391,
   0.011846
  ],
  "d": 0.153496,
  "sd_pooled": 0.025852,
  "n_hierarchy": 84,
  "n_polyarchy": 84
 },
 "lpm_cluster_H1": {
  "diff": 0.012897,
  "se": 0.010824,
  "t": 1.191502,
  "df": 167,
  "p": 0.235147
 },
 "lpm_cluster_creative": {
  "diff": 0.003968,
  "se": 0.003978,
  "t": 0.997514,
  "df": 167,
  "p": 0.319958
 },
 "novel_and_cells": {
  "novel_share": {
   "mean_hierarchy": 0.060516,
   "mean_polyarchy": 0.043651,
   "diff": 0.016865,
   "se": 0.007578,
   "t": 2.225516,
   "df": 165.300695,
   "p": 0.027399,
   "ci95": [
    0.001903,
    0.031827
   ],
   "d": 0.343405,
   "sd_pooled": 0.049111,
   "n_hierarchy": 84,
   "n_polyarchy": 84
  },
  "novel_approved_own_rule_per_proposal": {
   "mean_hierarchy": 0.000992,
   "mean_polyarchy": 0.040675,
   "diff": -0.039683,
   "se": 0.005279,
   "t": -7.517356,
   "df": 89.0695,
   "p": 0.0,
   "ci95": [
    -0.050171,
    -0.029194
   ],
   "d": -1.159953,
   "sd_pooled": 0.03421,
   "n_hierarchy": 84,
   "n_polyarchy": 84
  },
  "cells_quality_by_novelty": {
   "hierarchy": {
    "creative (quality and novel)": 0.010913,
    "quality, not novel": 0.863095,
    "novel, below the quality threshold": 0.049603,
    "neither": 0.076389,
    "n_proposals": 1008
   },
   "polyarchy": {
    "creative (quality and novel)": 0.006944,
    "quality, not novel": 0.87996,
    "novel, below the quality threshold": 0.036706,
    "neither": 0.076389,
    "n_proposals": 1008
   }
  }
 },
 "creative_yield_own_rule": {
  "mean_hierarchy": 0.000992,
  "mean_polyarchy": 0.006944,
  "diff": -0.005952,
  "se": 0.002716,
  "t": -2.191771,
  "df": 107.970048,
  "p": 0.030544,
  "ci95": [
   -0.011336,
   -0.000569
  ],
  "d": -0.338198,
  "sd_pooled": 0.0176,
  "n_hierarchy": 84,
  "n_polyarchy": 84
 },
 "placebo_first_role": {
  "role": "compliance",
  "below_share": {
   "mean_hierarchy": 0.055556,
   "mean_polyarchy": 0.055556,
   "diff": 0.0,
   "se": 0.019284,
   "t": 0.0,
   "df": 166.0,
   "p": 1.0,
   "ci95": [
    -0.038073,
    0.038073
   ],
   "d": 0.0,
   "sd_pooled": 0.124972,
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
  "mean_hierarchy": 0.125992,
  "mean_polyarchy": 0.113095,
  "diff": 0.012897,
  "se": 0.010854,
  "t": 1.188224,
  "df": 154.872899,
  "p": 0.236564,
  "ci95": [
   -0.008544,
   0.034338
  ],
  "d": 0.183347,
  "sd_pooled": 0.070341,
  "n_hierarchy": 84,
  "n_polyarchy": 84
 },
 "creative_share_without_flagged": {
  "mean_hierarchy": 0.010913,
  "mean_polyarchy": 0.006944,
  "diff": 0.003968,
  "se": 0.003989,
  "t": 0.99477,
  "df": 159.815265,
  "p": 0.321352,
  "ci95": [
   -0.00391,
   0.011846
  ],
  "d": 0.153496,
  "sd_pooled": 0.025852,
  "n_hierarchy": 84,
  "n_polyarchy": 84
 },
 "dispersion_kept_given_written_quality_rule4": 0.968444,
 "dispersion_kept_given_written_below_rule4": 0.978102,
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
   "novelty": 0.071914,
   "workability": -0.097405,
   "relevance": 0.060176
  },
  "H1_below_share_with_length_covariate": {
   "structure_coef": 0.015179,
   "se_hc2": 0.012368,
   "t": 1.227309,
   "p": 0.221455,
   "length_coef": 0.000463,
   "df": 165
  },
  "creative_share_with_length_covariate": {
   "structure_coef": 0.004689,
   "se_hc2": 0.004239,
   "t": 1.106336,
   "p": 0.270192,
   "length_coef": 0.000146,
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
     "mean_hierarchy": 0.00496,
     "mean_polyarchy": 0.001984,
     "diff": 0.002976,
     "se": 0.002575,
     "t": 1.155991,
     "df": 141.787564,
     "p": 0.249629,
     "ci95": [
      -0.002113,
      0.008066
     ],
     "d": 0.178373,
     "sd_pooled": 0.016685,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "creative_share": {
     "mean_hierarchy": 0.103175,
     "mean_polyarchy": 0.08631,
     "diff": 0.016865,
     "se": 0.009045,
     "t": 1.86464,
     "df": 156.402554,
     "p": 0.064106,
     "ci95": [
      -0.001,
      0.034731
     ],
     "d": 0.28772,
     "sd_pooled": 0.058616,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "H2a_quality": {
     "mean_hierarchy": 0.031746,
     "mean_polyarchy": 0.96627,
     "diff": -0.934524,
     "se": 0.0072,
     "t": -129.792582,
     "df": 165.988746,
     "p": 0.0,
     "ci95": [
      -0.948739,
      -0.920308
     ],
     "d": -20.02743,
     "sd_pooled": 0.046662,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "H2b_below": {
     "mean_hierarchy": 0.0,
     "mean_polyarchy": 0.000992,
     "diff": -0.000992,
     "se": 0.000992,
     "t": -1.0,
     "df": 83.0,
     "p": 0.320217,
     "ci95": [
      -0.002965,
      0.000981
     ],
     "d": -0.154303,
     "sd_pooled": 0.006429,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "rule_comparison_quality": {
     "mean": -0.940792,
     "se": 0.004908,
     "t": -191.671639,
     "df": 167,
     "p": 0.0,
     "ci95": [
      -0.950482,
      -0.931101
     ],
     "n_proposals": 2009,
     "n_organizations": 168
    },
    "rule_comparison_below": {
     "mean": -0.428571,
     "se": 0.202031,
     "t": -2.12132,
     "df": 6,
     "p": 0.078141,
     "ci95": [
      -0.922922,
      0.065779
     ],
     "n_proposals": 7,
     "n_organizations": 7
    },
    "category_rates": {
     "quality": 0.996528,
     "creative": 0.094742,
     "below": 0.003472,
     "novel": 0.095734
    }
   },
   "7.0": {
    "H1": {
     "mean_hierarchy": 0.55754,
     "mean_polyarchy": 0.508929,
     "diff": 0.048611,
     "se": 0.014043,
     "t": 3.461593,
     "df": 165.984445,
     "p": 0.000683,
     "ci95": [
      0.020885,
      0.076337
     ],
     "d": 0.534135,
     "sd_pooled": 0.091009,
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
     "mean_hierarchy": 0.007937,
     "mean_polyarchy": 0.490079,
     "diff": -0.482143,
     "se": 0.010082,
     "t": -47.822716,
     "df": 95.599594,
     "p": 0.0,
     "ci95": [
      -0.502156,
      -0.462129
     ],
     "d": -7.379205,
     "sd_pooled": 0.065338,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "H2b_below": {
     "mean_hierarchy": 0.02381,
     "mean_polyarchy": 0.477183,
     "diff": -0.453373,
     "se": 0.011718,
     "t": -38.69187,
     "df": 112.118331,
     "p": 0.0,
     "ci95": [
      -0.47659,
      -0.430157
     ],
     "d": -5.970285,
     "sd_pooled": 0.075938,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "rule_comparison_quality": {
     "mean": -0.984361,
     "se": 0.003781,
     "t": -260.357602,
     "df": 167,
     "p": 0.0,
     "ci95": [
      -0.991825,
      -0.976896
     ],
     "n_proposals": 941,
     "n_organizations": 168
    },
    "rule_comparison_below": {
     "mean": -0.899487,
     "se": 0.008979,
     "t": -100.1741,
     "df": 167,
     "p": 0.0,
     "ci95": [
      -0.917215,
      -0.88176
     ],
     "n_proposals": 1075,
     "n_organizations": 168
    },
    "category_rates": {
     "quality": 0.466766,
     "creative": 0.0,
     "below": 0.533234,
     "novel": 0.000496
    }
   }
  },
  "continuous": {
   "H1_shortfall_score": {
    "mean_hierarchy": 1.574157,
    "mean_polyarchy": 1.514633,
    "diff": 0.059524,
    "se": 0.0146,
    "t": 4.076873,
    "df": 164.950459,
    "p": 7.1e-05,
    "ci95": [
     0.030696,
     0.088351
    ],
    "d": 0.629075,
    "sd_pooled": 0.094621,
    "n_hierarchy": 84,
    "n_polyarchy": 84
   },
   "creative_novelty_score": {
    "mean_hierarchy": 3.21627,
    "mean_polyarchy": 3.138641,
    "diff": 0.077629,
    "se": 0.02846,
    "t": 2.72767,
    "df": 165.986618,
    "p": 0.007065,
    "ci95": [
     0.021439,
     0.133819
    ],
    "d": 0.420889,
    "sd_pooled": 0.184441,
    "n_hierarchy": 84,
    "n_polyarchy": 84
   },
   "H2a_quality_score": {
    "mean_hierarchy": 0.201141,
    "mean_polyarchy": 6.299355,
    "diff": -6.098214,
    "se": 0.044224,
    "t": -137.893368,
    "df": 165.439014,
    "p": 0.0,
    "ci95": [
     -6.185531,
     -6.010898
    ],
    "d": -21.277409,
    "sd_pooled": 0.286605,
    "n_hierarchy": 84,
    "n_polyarchy": 84
   },
   "H2b_shortfall_score": {
    "mean_hierarchy": 0.052827,
    "mean_polyarchy": 1.43874,
    "diff": -1.385913,
    "se": 0.016482,
    "t": -84.087912,
    "df": 140.7129,
    "p": 0.0,
    "ci95": [
     -1.418496,
     -1.353329
    ],
    "d": -12.975047,
    "sd_pooled": 0.106814,
    "n_hierarchy": 84,
    "n_polyarchy": 84
   },
   "rule_comparison_quality_score": {
    "mean": -73.136905,
    "se": 0.382195,
    "t": -191.360145,
    "df": 167,
    "p": 0.0,
    "ci95": [
     -73.891461,
     -72.382348
    ],
    "n": 168
   }
  }
 },
 "mediation_imai": {
  "H2a_quality": {
   "acme_hierarchy": -0.001265,
   "acme_polyarchy": -0.011599,
   "ade_hierarchy": -0.830663,
   "ade_polyarchy": -0.840997,
   "total": -0.842262,
   "acme_hierarchy_ci95": [
    -0.004867,
    0.001027
   ],
   "acme_polyarchy_ci95": [
    -0.03085,
    0.007489
   ],
   "ade_hierarchy_ci95": [
    -0.847034,
    -0.812809
   ],
   "ade_polyarchy_ci95": [
    -0.85669,
    -0.825354
   ],
   "total_ci95": [
    -0.858135,
    -0.825397
   ],
   "interaction_slope_difference": -0.801229,
   "no_interaction": {
    "acme": -0.005047,
    "ade": -0.837215,
    "total": -0.842262,
    "acme_ci95": [
     -0.013117,
     0.003599
    ],
    "ade_ci95": [
     -0.851519,
     -0.823077
    ]
   },
   "sensitivity_rho_at_zero_acme": 0.500955,
   "acme_at_rho": {
    "-0.4": -0.008853,
    "-0.2": -0.006827,
    "0.0": -0.005047,
    "0.2": -0.003267,
    "0.4": -0.001242
   }
  },
  "H2b_below": {
   "acme_hierarchy": 0.000512,
   "acme_polyarchy": 0.011237,
   "ade_hierarchy": -0.104491,
   "ade_polyarchy": -0.093766,
   "total": -0.093254,
   "acme_hierarchy_ci95": [
    -0.00025,
    0.002475
   ],
   "acme_polyarchy_ci95": [
    -0.006753,
    0.030379
   ],
   "ade_hierarchy_ci95": [
    -0.121358,
    -0.088158
   ],
   "ade_polyarchy_ci95": [
    -0.107032,
    -0.080938
   ],
   "total_ci95": [
    -0.107143,
    -0.080357
   ],
   "interaction_slope_difference": -0.831598,
   "no_interaction": {
    "acme": 0.004437,
    "ade": -0.097691,
    "total": -0.093254,
    "acme_ci95": [
     -0.002907,
     0.011437
    ],
    "ade_ci95": [
     -0.109192,
     -0.085876
    ]
   },
   "sensitivity_rho_at_zero_acme": 0.538708,
   "acme_at_rho": {
    "-0.4": 0.007465,
    "-0.2": 0.005853,
    "0.0": 0.004437,
    "0.2": 0.003021,
    "0.4": 0.001409
   }
  }
 },
 "judge_pass_reliability": {
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
 "judge_pass_reliability_glimmer": {
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
 "judge_agreement_with_glimmer": {
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
