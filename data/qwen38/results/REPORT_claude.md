# Results: arm qwen38, categories from judge claude

## Sample and integrity

- Organizations: hierarchy 84, polyarchy 84; proposals classified 2016, unscored 0, unclassified 0; organizations with fewer than 12 classified slots 0; proposals with one judge pass 0; missing votes 0.
- Readings by judge claude (PROTOCOL 4.4): 4 readings (the floor) (floor 4, ceiling 8, target 0.8); single-reading ICC(1,1) {"novelty": 0.908, "workability": 0.826, "relevance": 0.8}.
- Category rates (threshold 6.0 on the 2-8 scale): quality 0.826 (of which creative 0.052), below the quality threshold 0.174; novel 0.163 (novel but below 0.111). Share of proposals at the threshold: {"novelty": {"exactly": 0.130952, "within_half_point": 0.198413}, "workability": {"exactly": 0.041171, "within_half_point": 0.140873}, "relevance": {"exactly": 0.166171, "within_half_point": 0.306548}}.
- Approval rates of categorized proposals: {"quality_rule4": 0.794718, "quality_rule1": 0.9994, "creative_rule4": 0.721154, "creative_rule1": 1.0, "below_rule4": 0.391429, "below_rule1": 1.0, "all_rule4": 0.724702, "all_rule1": 0.999504}.
- Internal pilot, quality (PROTOCOL 6.4, at alpha 0.0500): category rate 0.826, approval rates 0.999 (one of four) and 0.795 (four of four), dispersion phi 0.53 (used 0.53); simulated power of H2 at n = 84: 1.000.
- Internal pilot, below (PROTOCOL 6.4, at alpha 0.0500): category rate 0.174, approval rates 1.000 (one of four) and 0.391 (four of four), dispersion phi 0.53 (used 0.53); simulated power of H2 at n = 84: 1.000.
- Dispersion of counts written over binomial (phi): {"quality_hierarchy": 0.505292, "quality_polyarchy": 0.546948, "creative_hierarchy": 0.822765, "creative_polyarchy": 0.797338, "below_hierarchy": 0.505292, "below_polyarchy": 0.546948}; correlation of novelty with relevance: -0.502, with workability: -0.708.

## Registered tests (hierarchy minus polyarchy; each at alpha .05, no correction)

| | estimate | 95% CI | d | p | verdict |
|---|---|---|---|---|---|
| H1 below-threshold proportion generated (= 1 - quality proportion) | -0.008 | [-0.032, 0.016] | -0.10 | 0.5177 | not supported |
| H2a quality proposals approved per proposal, own rule | -0.158 | [-0.187, -0.129] | -1.65 | 0.0000 | supported |
| H2b below-threshold proposals approved per proposal, own rule | -0.100 | [-0.122, -0.078] | -1.38 | 0.0000 | supported |

H1 secondary equivalence (bound 0.040): p = 0.0052, equivalent = True.
- H2a_quality: decomposition (reported) H2 difference -0.158 = generation part 0.011 + rule part -0.169; bootstrap 95% {"h2_difference": [-0.186508, -0.128968], "generation_part": [-0.013393, 0.036706], "rule_part": [-0.183532, -0.155258]}; cells {"hierarchy_rule4": 7.97619, "hierarchy_rule1": 9.952381, "polyarchy_rule4": 7.785714, "polyarchy_rule1": 9.869048}.
- H2b_below: decomposition (reported) H2 difference -0.100 = generation part 0.005 + rule part -0.106; bootstrap 95% {"h2_difference": [-0.122024, -0.078373], "generation_part": [-0.013393, 0.02381], "rule_part": [-0.117063, -0.094742]}; cells {"hierarchy_rule4": 0.928571, "hierarchy_rule1": 2.035714, "polyarchy_rule4": 0.702381, "polyarchy_rule1": 2.130952}.

## Reported, not tested: the two rules on the same votes

| per organization, proportion approved under four of four minus under one of four | mean | 95% CI | bootstrap 95% | organizations |
|---|---|---|---|---|
| quality proposals | -0.204 | [-0.221, -0.187] | [-0.221, -0.188] | 168 |
| below-threshold proposals | -0.605 | [-0.661, -0.549] | [-0.659, -0.551] | 160 |

Approval rates by rule: {"quality_approved_rule4": 0.794718, "quality_approved_rule1": 0.9994, "creative_approved_rule4": 0.721154, "creative_approved_rule1": 1.0, "below_approved_rule4": 0.391429, "below_approved_rule1": 1.0}. per organization, the proportion of its quality (below-threshold) proposals with complete votes approved under four of four minus the proportion approved under one of four, mean over organizations with a 95% interval; both rules read the same four votes, so the difference is never positive: a benchmark, not a hypothesis


Attrition (PROTOCOL 8.3): overall 0.0%, differential 0.0 points (cautious WWC bound 5.7); low attrition.
Failure rate by structure (Haldane estimator for sampling to a fixed number of completions): hierarchy 0.000 (naive 0.000), polyarchy 0.000 (naive 0.000).

| Lee bounds on the structure contrast (trimming the group with more completions) | lower | upper | trimmed | share |
|---|---|---|---|---|
| H1 | -0.008 | -0.008 | none | 0.000 |
| H2a | -0.158 | -0.158 | none | 0.000 |
| H2b | -0.100 | -0.100 | none | 0.000 |

| Call log | attempts | content failures | rate | first-attempt failures | outcomes from a retry | exhausted |
|---|---|---|---|---|---|---|
| calls_evaluation_gemma.jsonl | 8064 | 0 | 0.000 | 0 of 8064 | 0 | 0 |
| calls_generation.jsonl | 673 | 1 | 0.001 | 1 of 672 | 1 | 0 |
| calls_judge_claude.jsonl | 8064 | 0 | 0.000 | 0 of 8064 | 0 | 0 |
| calls_judge_glimmer.jsonl | 8064 | 0 | 0.000 | 0 of 8064 | 0 | 0 |

## Secondary (PROTOCOL 7.4)

```json
{
 "permutation_within_blocks": {
  "H1_below_share": {
   "diff": -0.007937,
   "p_permutation": 0.594941,
   "B": 10000
  },
  "creative_share": {
   "diff": 0.027778,
   "p_permutation": 0.0045,
   "B": 10000
  }
 },
 "creative_share": {
  "mean_hierarchy": 0.065476,
  "mean_polyarchy": 0.037698,
  "diff": 0.027778,
  "se": 0.008868,
  "t": 3.132383,
  "df": 154.704877,
  "p": 0.002074,
  "ci95": [
   0.01026,
   0.045296
  ],
  "d": 0.483337,
  "sd_pooled": 0.057471,
  "n_hierarchy": 84,
  "n_polyarchy": 84
 },
 "lpm_cluster_H1": {
  "diff": -0.007937,
  "se": 0.012208,
  "t": -0.650109,
  "df": 167,
  "p": 0.516515
 },
 "lpm_cluster_creative": {
  "diff": 0.027778,
  "se": 0.008844,
  "t": 3.141024,
  "df": 167,
  "p": 0.001992
 },
 "novel_and_cells": {
  "novel_share": {
   "mean_hierarchy": 0.172619,
   "mean_polyarchy": 0.152778,
   "diff": 0.019841,
   "se": 0.011861,
   "t": 1.672836,
   "df": 165.691413,
   "p": 0.096247,
   "ci95": [
    -0.003577,
    0.043259
   ],
   "d": 0.258124,
   "sd_pooled": 0.076867,
   "n_hierarchy": 84,
   "n_polyarchy": 84
  },
  "novel_approved_own_rule_per_proposal": {
   "mean_hierarchy": 0.092262,
   "mean_polyarchy": 0.152778,
   "diff": -0.060516,
   "se": 0.01154,
   "t": -5.243964,
   "df": 164.292379,
   "p": 0.0,
   "ci95": [
    -0.083302,
    -0.03773
   ],
   "d": -0.809161,
   "sd_pooled": 0.074788,
   "n_hierarchy": 84,
   "n_polyarchy": 84
  },
  "cells_quality_by_novelty": {
   "hierarchy": {
    "creative (quality and novel)": 0.065476,
    "quality, not novel": 0.764881,
    "novel, below the quality threshold": 0.107143,
    "neither": 0.0625,
    "n_proposals": 1008
   },
   "polyarchy": {
    "creative (quality and novel)": 0.037698,
    "quality, not novel": 0.784722,
    "novel, below the quality threshold": 0.115079,
    "neither": 0.0625,
    "n_proposals": 1008
   }
  }
 },
 "creative_yield_own_rule": {
  "mean_hierarchy": 0.047619,
  "mean_polyarchy": 0.037698,
  "diff": 0.009921,
  "se": 0.007945,
  "t": 1.24859,
  "df": 164.639344,
  "p": 0.213587,
  "ci95": [
   -0.005768,
   0.025609
  ],
  "d": 0.192662,
  "sd_pooled": 0.051493,
  "n_hierarchy": 84,
  "n_polyarchy": 84
 },
 "placebo_first_role": {
  "role": "compliance",
  "below_share": {
   "mean_hierarchy": 0.087302,
   "mean_polyarchy": 0.055556,
   "diff": 0.031746,
   "se": 0.021088,
   "t": 1.505394,
   "df": 161.661361,
   "p": 0.134174,
   "ci95": [
    -0.009898,
    0.07339
   ],
   "d": 0.232287,
   "sd_pooled": 0.136667,
   "n_hierarchy": 84,
   "n_polyarchy": 84
  },
  "creative_share": {
   "mean_hierarchy": 0.02381,
   "mean_polyarchy": 0.02381,
   "diff": 0.0,
   "se": 0.013326,
   "t": 0.0,
   "df": 166.0,
   "p": 1.0,
   "ci95": [
    -0.02631,
    0.02631
   ],
   "d": 0.0,
   "sd_pooled": 0.086362,
   "n_hierarchy": 84,
   "n_polyarchy": 84
  }
 },
 "leakage": {
  "pattern": "\\b(colleague|colleagues|stance|senior colleague|senior colleagues|as the (compliance officer|lab director|director|researcher) (noted|notes|argued|argues|said|says|suggested|suggests|proposed|proposes|emphasized|emphasizes|stressed|stresses|recommended|recommends|pointed out|points out))\\b",
  "n_flagged": 4,
  "share_juniors_hierarchy": 0.002646,
  "share_juniors_polyarchy": 0.001323,
  "share_first_role": 0.001984
 },
 "H1_without_flagged": {
  "mean_hierarchy": 0.168831,
  "mean_polyarchy": 0.17803,
  "diff": -0.009199,
  "se": 0.012292,
  "t": -0.748398,
  "df": 165.481026,
  "p": 0.455283,
  "ci95": [
   -0.033468,
   0.01507
  ],
  "d": -0.11548,
  "sd_pooled": 0.07966,
  "n_hierarchy": 84,
  "n_polyarchy": 84
 },
 "creative_share_without_flagged": {
  "mean_hierarchy": 0.065747,
  "mean_polyarchy": 0.037789,
  "diff": 0.027958,
  "se": 0.008903,
  "t": 3.140245,
  "df": 154.465644,
  "p": 0.002023,
  "ci95": [
   0.01037,
   0.045546
  ],
  "d": 0.48455,
  "sd_pooled": 0.057699,
  "n_hierarchy": 84,
  "n_polyarchy": 84
 },
 "dispersion_kept_given_written_quality_rule4": 0.728217,
 "dispersion_kept_given_written_below_rule4": 0.932478,
 "stance_check": {
  "hierarchy": {
   "corr_junior_with_mean_senior": 0.457629,
   "mean_within_org_sd": 6.351672
  },
  "polyarchy": {
   "corr_junior_with_mean_senior": -0.122705,
   "mean_within_org_sd": 9.148764
  }
 },
 "stance_within_org_sd_welch": {
  "mean_hierarchy": 6.351672,
  "mean_polyarchy": 9.148764,
  "diff": -2.797092,
  "se": 0.438881,
  "t": -6.373242,
  "df": 149.108063,
  "p": 0.0,
  "ci95": [
   -3.66432,
   -1.929863
  ],
  "d": -0.983413,
  "sd_pooled": 2.844271,
  "n_hierarchy": 84,
  "n_polyarchy": 84
 },
 "reasoning_words_mean": {
  "hierarchy": 168.229167,
  "polyarchy": 154.041667
 },
 "manipulation_check": {
  "mean_hierarchy": 7.10119,
  "mean_polyarchy": 9.988757,
  "diff": -2.887566,
  "se": 0.529073,
  "t": -5.457781,
  "df": 148.094304,
  "p": 0.0,
  "ci95": [
   -3.933074,
   -1.842058
  ],
  "d": -0.842154,
  "sd_pooled": 3.428787,
  "n_hierarchy": 84,
  "n_polyarchy": 84,
  "verdict": "supported"
 },
 "proposal_length": {
  "words_per_proposal_mean": {
   "hierarchy": 98.600198,
   "polyarchy": 96.891865
  },
  "welch_mean_length": {
   "mean_hierarchy": 98.600198,
   "mean_polyarchy": 96.891865,
   "diff": 1.708333,
   "se": 0.661431,
   "t": 2.582783,
   "df": 163.888098,
   "p": 0.010674,
   "ci95": [
    0.402308,
    3.014359
   ],
   "d": 0.398532,
   "sd_pooled": 4.286564,
   "n_hierarchy": 84,
   "n_polyarchy": 84
  },
  "corr_length_with_dimension": {
   "novelty": 0.081382,
   "workability": -0.03386,
   "relevance": -0.070981
  },
  "H1_below_share_with_length_covariate": {
   "structure_coef": -0.002218,
   "se_hc2": 0.012288,
   "t": -0.18048,
   "p": 0.856997,
   "length_coef": -0.003348,
   "df": 165
  },
  "creative_share_with_length_covariate": {
   "structure_coef": 0.02623,
   "se_hc2": 0.008706,
   "t": 3.012988,
   "p": 0.002995,
   "length_coef": 0.000906,
   "df": 165
  },
  "words_by_structure": {
   "hierarchy": {
    "n": 1008,
    "mean": 98.600198,
    "percentiles": {
     "5": 82.35,
     "25": 92.0,
     "50": 99.0,
     "75": 104.0,
     "95": 113.65
    },
    "share_in_60_to_110": 0.921627
   },
   "polyarchy": {
    "n": 1008,
    "mean": 96.891865,
    "percentiles": {
     "5": 81.0,
     "25": 90.0,
     "50": 97.0,
     "75": 103.0,
     "95": 111.0
    },
    "share_in_60_to_110": 0.946429
   }
  }
 },
 "classification_sensitivity": {
  "thresholds": {
   "5.0": {
    "H1": {
     "mean_hierarchy": 0.021825,
     "mean_polyarchy": 0.021825,
     "diff": 0.0,
     "se": 0.006028,
     "t": 0.0,
     "df": 166.0,
     "p": 1.0,
     "ci95": [
      -0.011901,
      0.011901
     ],
     "d": 0.0,
     "sd_pooled": 0.039063,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "creative_share": {
     "mean_hierarchy": 0.251984,
     "mean_polyarchy": 0.224206,
     "diff": 0.027778,
     "se": 0.012301,
     "t": 2.258249,
     "df": 165.540863,
     "p": 0.025236,
     "ci95": [
      0.003492,
      0.052064
     ],
     "d": 0.348455,
     "sd_pooled": 0.079717,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "H2a_quality": {
     "mean_hierarchy": 0.739087,
     "mean_polyarchy": 0.978175,
     "diff": -0.239087,
     "se": 0.012773,
     "t": -18.718138,
     "df": 103.477731,
     "p": 0.0,
     "ci95": [
      -0.264418,
      -0.213756
     ],
     "d": -2.888271,
     "sd_pooled": 0.082779,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "H2b_below": {
     "mean_hierarchy": 0.002976,
     "mean_polyarchy": 0.021825,
     "diff": -0.018849,
     "se": 0.004588,
     "t": -4.108596,
     "df": 108.684099,
     "p": 7.7e-05,
     "ci95": [
      -0.027942,
      -0.009756
     ],
     "d": -0.63397,
     "sd_pooled": 0.029732,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "rule_comparison_quality": {
     "mean": -0.261147,
     "se": 0.008614,
     "t": -30.316435,
     "df": 167,
     "p": 0.0,
     "ci95": [
      -0.278154,
      -0.244141
     ],
     "n_proposals": 1972,
     "n_organizations": 168
    },
    "rule_comparison_below": {
     "mean": -0.880952,
     "se": 0.050576,
     "t": -17.418381,
     "df": 41,
     "p": 0.0,
     "ci95": [
      -0.983093,
      -0.778812
     ],
     "n_proposals": 44,
     "n_organizations": 42
    },
    "category_rates": {
     "quality": 0.978175,
     "creative": 0.238095,
     "below": 0.021825,
     "novel": 0.25744
    }
   },
   "7.0": {
    "H1": {
     "mean_hierarchy": 0.478175,
     "mean_polyarchy": 0.447421,
     "diff": 0.030754,
     "se": 0.015583,
     "t": 1.973542,
     "df": 165.998714,
     "p": 0.050094,
     "ci95": [
      -1.3e-05,
      0.061521
     ],
     "d": 0.304524,
     "sd_pooled": 0.10099,
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
     "mean_hierarchy": 0.434524,
     "mean_polyarchy": 0.552579,
     "diff": -0.118056,
     "se": 0.015192,
     "t": -7.771075,
     "df": 165.597957,
     "p": 0.0,
     "ci95": [
      -0.14805,
      -0.088061
     ],
     "d": -1.199103,
     "sd_pooled": 0.098453,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "H2b_below": {
     "mean_hierarchy": 0.30754,
     "mean_polyarchy": 0.447421,
     "diff": -0.139881,
     "se": 0.016262,
     "t": -8.601546,
     "df": 164.827586,
     "p": 0.0,
     "ci95": [
      -0.17199,
      -0.107772
     ],
     "d": -1.327247,
     "sd_pooled": 0.105392,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "rule_comparison_quality": {
     "mean": -0.170885,
     "se": 0.01028,
     "t": -16.623516,
     "df": 167,
     "p": 0.0,
     "ci95": [
      -0.19118,
      -0.15059
     ],
     "n_proposals": 1083,
     "n_organizations": 168
    },
    "rule_comparison_below": {
     "mean": -0.397711,
     "se": 0.016619,
     "t": -23.930524,
     "df": 167,
     "p": 0.0,
     "ci95": [
      -0.430522,
      -0.3649
     ],
     "n_proposals": 933,
     "n_organizations": 168
    },
    "category_rates": {
     "quality": 0.537202,
     "creative": 0.0,
     "below": 0.462798,
     "novel": 0.006448
    }
   }
  },
  "continuous": {
   "H1_shortfall_score": {
    "mean_hierarchy": 1.519841,
    "mean_polyarchy": 1.50248,
    "diff": 0.017361,
    "se": 0.020831,
    "t": 0.833416,
    "df": 164.213777,
    "p": 0.405821,
    "ci95": [
     -0.023771,
     0.058493
    ],
    "d": 0.128599,
    "sd_pooled": 0.135002,
    "n_hierarchy": 84,
    "n_polyarchy": 84
   },
   "creative_novelty_score": {
    "mean_hierarchy": 3.777282,
    "mean_polyarchy": 3.725942,
    "diff": 0.051339,
    "se": 0.03785,
    "t": 1.356387,
    "df": 163.737699,
    "p": 0.176843,
    "ci95": [
     -0.023398,
     0.126076
    ],
    "d": 0.209295,
    "sd_pooled": 0.245296,
    "n_hierarchy": 84,
    "n_polyarchy": 84
   },
   "H2a_quality_score": {
    "mean_hierarchy": 4.901786,
    "mean_polyarchy": 6.49752,
    "diff": -1.595734,
    "se": 0.078846,
    "t": -20.238598,
    "df": 89.643646,
    "p": 0.0,
    "ci95": [
     -1.752384,
     -1.439084
    ],
    "d": -3.122884,
    "sd_pooled": 0.510981,
    "n_hierarchy": 84,
    "n_polyarchy": 84
   },
   "H2b_shortfall_score": {
    "mean_hierarchy": 1.034722,
    "mean_polyarchy": 1.50248,
    "diff": -0.467758,
    "se": 0.026844,
    "t": -17.424955,
    "df": 149.249812,
    "p": 0.0,
    "ci95": [
     -0.520802,
     -0.414714
    ],
    "d": -2.688729,
    "sd_pooled": 0.17397,
    "n_hierarchy": 84,
    "n_polyarchy": 84
   },
   "rule_comparison_quality_score": {
    "mean": -20.098214,
    "se": 0.646453,
    "t": -31.090005,
    "df": 167,
    "p": 0.0,
    "ci95": [
     -21.374487,
     -18.821942
    ],
    "n": 168
   }
  }
 },
 "mediation_imai": {
  "H2a_quality": {
   "acme_hierarchy": 0.005366,
   "acme_polyarchy": 0.007937,
   "ade_hierarchy": -0.165675,
   "ade_polyarchy": -0.163104,
   "total": -0.157738,
   "acme_hierarchy_ci95": [
    -0.01022,
    0.023497
   ],
   "acme_polyarchy_ci95": [
    -0.014881,
    0.031746
   ],
   "ade_hierarchy_ci95": [
    -0.1875,
    -0.144841
   ],
   "ade_polyarchy_ci95": [
    -0.184083,
    -0.142463
   ],
   "total_ci95": [
    -0.185541,
    -0.128968
   ],
   "interaction_slope_difference": -0.323929,
   "no_interaction": {
    "acme": 0.006725,
    "ade": -0.164463,
    "total": -0.157738,
    "acme_ci95": [
     -0.012581,
     0.026992
    ],
    "ade_ci95": [
     -0.185056,
     -0.144163
    ]
   },
   "sensitivity_rho_at_zero_acme": 0.704739,
   "acme_at_rho": {
    "-0.4": 0.00968,
    "-0.2": 0.008107,
    "0.0": 0.006725,
    "0.2": 0.005343,
    "0.4": 0.00377
   }
  },
  "H2b_below": {
   "acme_hierarchy": -0.003159,
   "acme_polyarchy": -0.007937,
   "ade_hierarchy": -0.092262,
   "ade_polyarchy": -0.09704,
   "total": -0.100198,
   "acme_hierarchy_ci95": [
    -0.013359,
    0.006036
   ],
   "acme_polyarchy_ci95": [
    -0.032738,
    0.014906
   ],
   "ade_hierarchy_ci95": [
    -0.108135,
    -0.077381
   ],
   "ade_polyarchy_ci95": [
    -0.11362,
    -0.080476
   ],
   "total_ci95": [
    -0.124008,
    -0.077381
   ],
   "interaction_slope_difference": -0.602015,
   "no_interaction": {
    "acme": -0.005685,
    "ade": -0.094513,
    "total": -0.100198,
    "acme_ci95": [
     -0.023201,
     0.011199
    ],
    "ade_ci95": [
     -0.10853,
     -0.080659
    ]
   },
   "sensitivity_rho_at_zero_acme": 0.785473,
   "acme_at_rho": {
    "-0.4": -0.00764,
    "-0.2": -0.0066,
    "0.0": -0.005685,
    "0.2": -0.004771,
    "0.4": -0.00373
   }
  }
 },
 "judge_pass_reliability": {
  "passes": 4,
  "n_all_passes": 2016,
  "r12_novelty": 0.904928,
  "icc1_novelty": {
   "icc1_1": 0.907616,
   "icc1_k": 0.975185,
   "n": 2016,
   "k": 4
  },
  "r12_workability": 0.816525,
  "icc1_workability": {
   "icc1_1": 0.826388,
   "icc1_k": 0.9501,
   "n": 2016,
   "k": 4
  },
  "r12_relevance": 0.802027,
  "icc1_relevance": {
   "icc1_1": 0.799716,
   "icc1_k": 0.941078,
   "n": 2016,
   "k": 4
  },
  "split_half_kappa_three_way": 0.75658,
  "split_half_kappa_creative": 0.599463,
  "split_half_kappa_below": 0.739699
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
   "calls_evaluation_gemma.jsonl": {
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
   "calls_generation.jsonl": {
    "attempts_completed": 673,
    "content_failures": 1,
    "content_failure_rate": 0.001486,
    "first_attempts": 672,
    "first_attempt_failures": 1,
    "valid_outcomes": 672,
    "outcomes_from_a_retry": 1,
    "exhausted_logical_calls": 0,
    "failure_reasons": {
     "invalid: stop_reason=length": 1
    },
    "by_structure": {
     "hierarchy": {
      "attempts": 336,
      "content_failures": 0
     },
     "polyarchy": {
      "attempts": 337,
      "content_failures": 1
     }
    },
    "audit_file": "results/failed_attempts_calls_generation.jsonl"
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
  "r12_novelty": 0.871649,
  "icc1_novelty": {
   "icc1_1": 0.876027,
   "icc1_k": 0.96583,
   "n": 2016,
   "k": 4
  },
  "r12_workability": 0.697806,
  "icc1_workability": {
   "icc1_1": 0.71246,
   "icc1_k": 0.90835,
   "n": 2016,
   "k": 4
  },
  "r12_relevance": 0.799919,
  "icc1_relevance": {
   "icc1_1": 0.79958,
   "icc1_k": 0.941031,
   "n": 2016,
   "k": 4
  },
  "split_half_kappa_three_way": 0.808848,
  "split_half_kappa_creative": 0.776892,
  "split_half_kappa_below": 0.72226
 },
 "judge_agreement_with_glimmer": {
  "n": 2016,
  "r_novelty": 0.907468,
  "icc_novelty": {
   "icc_c1": 0.907294,
   "icc_a1": 0.84792,
   "n": 2016
  },
  "r_disattenuated_novelty": 0.935056,
  "r_workability": 0.741573,
  "icc_workability": {
   "icc_c1": 0.676257,
   "icc_a1": 0.658278,
   "n": 2016
  },
  "r_disattenuated_workability": 0.798257,
  "r_relevance": 0.70161,
  "icc_relevance": {
   "icc_c1": 0.669669,
   "icc_a1": 0.540996,
   "n": 2016
  },
  "r_disattenuated_relevance": 0.745557,
  "kappa_three_way": 0.542525,
  "kappa_creative": 0.32553,
  "kappa_below": 0.489472,
  "agreement_three_way": 0.800099
 },
 "evaluator_agreement_among_roles": {
  "n": 2016,
  "fleiss_kappa_roles": 0.190105,
  "share_disagree": 0.274802,
  "kappa_by_pair": {
   "compliance-director": 0.459218,
   "compliance-engineer": 0.471126,
   "compliance-researcher": -0.073982,
   "director-engineer": 0.510231,
   "director-researcher": -0.028385,
   "engineer-researcher": 0.030895
  }
 }
}
```
