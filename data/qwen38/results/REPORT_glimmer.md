# Results: arm qwen38, categories from judge glimmer

## Sample and integrity

- Organizations: hierarchy 84, polyarchy 84; proposals classified 2016, unscored 0, unclassified 0; organizations with fewer than 12 classified slots 0; proposals with one judge pass 0; missing votes 0.
- Readings by judge glimmer (PROTOCOL 4.4): 4 readings (the floor) (floor 4, ceiling 8, target 0.8); single-reading ICC(1,1) {"novelty": 0.876, "workability": 0.712, "relevance": 0.8}.
- Category rates (threshold 6.0 on the 2-8 scale): quality 0.875 (of which creative 0.188), below the quality threshold 0.125; novel 0.253 (novel but below 0.064). Share of proposals at the threshold: {"novelty": {"exactly": 0.142361, "within_half_point": 0.271825}, "workability": {"exactly": 0.048611, "within_half_point": 0.168651}, "relevance": {"exactly": 0.017361, "within_half_point": 0.085813}}.
- Approval rates of categorized proposals: {"quality_rule4": 0.759501, "quality_rule1": 0.999433, "creative_rule4": 0.642105, "creative_rule1": 0.997368, "below_rule4": 0.482213, "below_rule1": 1.0, "all_rule4": 0.724702, "all_rule1": 0.999504}.
- Internal pilot, quality (PROTOCOL 6.4, at alpha 0.0500): category rate 0.875, approval rates 0.999 (one of four) and 0.760 (four of four), dispersion phi 0.83 (used 0.83); simulated power of H2 at n = 84: 1.000.
- Internal pilot, below (PROTOCOL 6.4, at alpha 0.0500): category rate 0.125, approval rates 1.000 (one of four) and 0.482 (four of four), dispersion phi 0.83 (used 0.83); simulated power of H2 at n = 84: 1.000.
- Dispersion of counts written over binomial (phi): {"quality_hierarchy": 0.90804, "quality_polyarchy": 0.757999, "creative_hierarchy": 0.632184, "creative_polyarchy": 0.723303, "below_hierarchy": 0.90804, "below_polyarchy": 0.757999}; correlation of novelty with relevance: -0.104, with workability: -0.478.

## Registered tests (hierarchy minus polyarchy; each at alpha .05, no correction)

| | estimate | 95% CI | d | p | verdict |
|---|---|---|---|---|---|
| H1 below-threshold proportion generated (= 1 - quality proportion) | -0.007 | [-0.034, 0.020] | -0.08 | 0.6064 | not supported |
| H2a quality proposals approved per proposal, own rule | -0.196 | [-0.227, -0.166] | -1.97 | 0.0000 | supported |
| H2b below-threshold proposals approved per proposal, own rule | -0.062 | [-0.085, -0.038] | -0.79 | 0.0000 | supported |

H1 secondary equivalence (bound 0.044): p = 0.0036, equivalent = True.
- H2a_quality: decomposition (reported) H2 difference -0.196 = generation part 0.013 + rule part -0.210; bootstrap 95% {"h2_difference": [-0.22619, -0.166667], "generation_part": [-0.011409, 0.039187], "rule_part": [-0.225694, -0.194444]}; cells {"hierarchy_rule4": 8.095238, "hierarchy_rule1": 10.52381, "polyarchy_rule4": 7.845238, "polyarchy_rule1": 10.452381}.
- H2b_below: decomposition (reported) H2 difference -0.062 = generation part 0.003 + rule part -0.065; bootstrap 95% {"h2_difference": [-0.085317, -0.03869], "generation_part": [-0.017361, 0.024306], "rule_part": [-0.074901, -0.055556]}; cells {"hierarchy_rule4": 0.809524, "hierarchy_rule1": 1.464286, "polyarchy_rule4": 0.642857, "polyarchy_rule1": 1.547619}.

## Reported, not tested: the two rules on the same votes

| per organization, proportion approved under four of four minus under one of four | mean | 95% CI | bootstrap 95% | organizations |
|---|---|---|---|---|
| quality proposals | -0.238 | [-0.255, -0.222] | [-0.255, -0.222] | 168 |
| below-threshold proposals | -0.521 | [-0.587, -0.455] | [-0.586, -0.456] | 137 |

Approval rates by rule: {"quality_approved_rule4": 0.759501, "quality_approved_rule1": 0.999433, "creative_approved_rule4": 0.642105, "creative_approved_rule1": 0.997368, "below_approved_rule4": 0.482213, "below_approved_rule1": 1.0}. per organization, the proportion of its quality (below-threshold) proposals with complete votes approved under four of four minus the proportion approved under one of four, mean over organizations with a 95% interval; both rules read the same four votes, so the difference is never positive: a benchmark, not a hypothesis


Attrition (PROTOCOL 8.3): overall 0.0%, differential 0.0 points (cautious WWC bound 5.7); low attrition.
Failure rate by structure (Haldane estimator for sampling to a fixed number of completions): hierarchy 0.000 (naive 0.000), polyarchy 0.000 (naive 0.000).

| Lee bounds on the structure contrast (trimming the group with more completions) | lower | upper | trimmed | share |
|---|---|---|---|---|
| H1 | -0.007 | -0.007 | none | 0.000 |
| H2a | -0.196 | -0.196 | none | 0.000 |
| H2b | -0.062 | -0.062 | none | 0.000 |

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
   "diff": -0.006944,
   "p_permutation": 0.669733,
   "B": 10000
  },
  "creative_share": {
   "diff": 0.001984,
   "p_permutation": 0.946205,
   "B": 10000
  }
 },
 "creative_share": {
  "mean_hierarchy": 0.189484,
  "mean_polyarchy": 0.1875,
  "diff": 0.001984,
  "se": 0.01434,
  "t": 0.138363,
  "df": 165.339611,
  "p": 0.890122,
  "ci95": [
   -0.026329,
   0.030297
  ],
  "d": 0.02135,
  "sd_pooled": 0.092934,
  "n_hierarchy": 84,
  "n_polyarchy": 84
 },
 "lpm_cluster_H1": {
  "diff": -0.006944,
  "se": 0.013416,
  "t": -0.517623,
  "df": 167,
  "p": 0.605406
 },
 "lpm_cluster_creative": {
  "diff": 0.001984,
  "se": 0.014301,
  "t": 0.138745,
  "df": 167,
  "p": 0.889819
 },
 "novel_and_cells": {
  "novel_share": {
   "mean_hierarchy": 0.249008,
   "mean_polyarchy": 0.256944,
   "diff": -0.007937,
   "se": 0.01299,
   "t": -0.610979,
   "df": 162.884554,
   "p": 0.542065,
   "ci95": [
    -0.033587,
    0.017714
   ],
   "d": -0.094276,
   "sd_pooled": 0.084184,
   "n_hierarchy": 84,
   "n_polyarchy": 84
  },
  "novel_approved_own_rule_per_proposal": {
   "mean_hierarchy": 0.146825,
   "mean_polyarchy": 0.256944,
   "diff": -0.110119,
   "se": 0.012371,
   "t": -8.901217,
   "df": 155.866534,
   "p": 0.0,
   "ci95": [
    -0.134556,
    -0.085682
   ],
   "d": -1.373488,
   "sd_pooled": 0.080175,
   "n_hierarchy": 84,
   "n_polyarchy": 84
  },
  "cells_quality_by_novelty": {
   "hierarchy": {
    "creative (quality and novel)": 0.189484,
    "quality, not novel": 0.688492,
    "novel, below the quality threshold": 0.059524,
    "neither": 0.0625,
    "n_proposals": 1008
   },
   "polyarchy": {
    "creative (quality and novel)": 0.1875,
    "quality, not novel": 0.683532,
    "novel, below the quality threshold": 0.069444,
    "neither": 0.059524,
    "n_proposals": 1008
   }
  }
 },
 "creative_yield_own_rule": {
  "mean_hierarchy": 0.127976,
  "mean_polyarchy": 0.1875,
  "diff": -0.059524,
  "se": 0.012961,
  "t": -4.592685,
  "df": 152.161974,
  "p": 9e-06,
  "ci95": [
   -0.08513,
   -0.033918
  ],
  "d": -0.708667,
  "sd_pooled": 0.083994,
  "n_hierarchy": 84,
  "n_polyarchy": 84
 },
 "placebo_first_role": {
  "role": "compliance",
  "below_share": {
   "mean_hierarchy": 0.154762,
   "mean_polyarchy": 0.154762,
   "diff": 0.0,
   "se": 0.027596,
   "t": 0.0,
   "df": 165.709724,
   "p": 1.0,
   "ci95": [
    -0.054485,
    0.054485
   ],
   "d": 0.0,
   "sd_pooled": 0.178844,
   "n_hierarchy": 84,
   "n_polyarchy": 84
  },
  "creative_share": {
   "mean_hierarchy": 0.075397,
   "mean_polyarchy": 0.075397,
   "diff": 0.0,
   "se": 0.022372,
   "t": 0.0,
   "df": 165.329468,
   "p": 1.0,
   "ci95": [
    -0.044171,
    0.044171
   ],
   "d": 0.0,
   "sd_pooled": 0.144985,
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
  "mean_hierarchy": 0.121302,
  "mean_polyarchy": 0.129239,
  "diff": -0.007937,
  "se": 0.01346,
  "t": -0.589651,
  "df": 165.274326,
  "p": 0.55623,
  "ci95": [
   -0.034512,
   0.018639
  ],
  "d": -0.090985,
  "sd_pooled": 0.087229,
  "n_hierarchy": 84,
  "n_polyarchy": 84
 },
 "creative_share_without_flagged": {
  "mean_hierarchy": 0.188853,
  "mean_polyarchy": 0.187049,
  "diff": 0.001804,
  "se": 0.014349,
  "t": 0.125707,
  "df": 165.189117,
  "p": 0.900117,
  "ci95": [
   -0.026527,
   0.030135
  ],
  "d": 0.019397,
  "sd_pooled": 0.092991,
  "n_hierarchy": 84,
  "n_polyarchy": 84
 },
 "dispersion_kept_given_written_quality_rule4": 0.739154,
 "dispersion_kept_given_written_below_rule4": 0.848912,
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
   "novelty": 0.071115,
   "workability": -0.029641,
   "relevance": -0.054943
  },
  "H1_below_share_with_length_covariate": {
   "structure_coef": -0.007869,
   "se_hc2": 0.013301,
   "t": -0.591627,
   "p": 0.55491,
   "length_coef": 0.000541,
   "df": 165
  },
  "creative_share_with_length_covariate": {
   "structure_coef": -0.000737,
   "se_hc2": 0.014447,
   "t": -0.051007,
   "p": 0.959382,
   "length_coef": 0.001593,
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
     "mean_hierarchy": 0.046627,
     "mean_polyarchy": 0.042659,
     "diff": 0.003968,
     "se": 0.008332,
     "t": 0.476291,
     "df": 165.99721,
     "p": 0.634493,
     "ci95": [
      -0.012481,
      0.020418
     ],
     "d": 0.073493,
     "sd_pooled": 0.053995,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "creative_share": {
     "mean_hierarchy": 0.332341,
     "mean_polyarchy": 0.358135,
     "diff": -0.025794,
     "se": 0.014063,
     "t": -1.834173,
     "df": 161.649701,
     "p": 0.068467,
     "ci95": [
      -0.053564,
      0.001977
     ],
     "d": -0.283019,
     "sd_pooled": 0.091137,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "H2a_quality": {
     "mean_hierarchy": 0.713294,
     "mean_polyarchy": 0.957341,
     "diff": -0.244048,
     "se": 0.013304,
     "t": -18.344355,
     "df": 121.392329,
     "p": 0.0,
     "ci95": [
      -0.270385,
      -0.21771
     ],
     "d": -2.830595,
     "sd_pooled": 0.086218,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "H2b_below": {
     "mean_hierarchy": 0.02877,
     "mean_polyarchy": 0.042659,
     "diff": -0.013889,
     "se": 0.007857,
     "t": -1.767726,
     "df": 163.279419,
     "p": 0.078974,
     "ci95": [
      -0.029403,
      0.001625
     ],
     "d": -0.272766,
     "sd_pooled": 0.050919,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "rule_comparison_quality": {
     "mean": -0.26854,
     "se": 0.008827,
     "t": -30.420999,
     "df": 167,
     "p": 0.0,
     "ci95": [
      -0.285967,
      -0.251112
     ],
     "n_proposals": 1926,
     "n_organizations": 168
    },
    "rule_comparison_below": {
     "mean": -0.400433,
     "se": 0.053921,
     "t": -7.426312,
     "df": 76,
     "p": 0.0,
     "ci95": [
      -0.507826,
      -0.29304
     ],
     "n_proposals": 90,
     "n_organizations": 77
    },
    "category_rates": {
     "quality": 0.955357,
     "creative": 0.345238,
     "below": 0.044643,
     "novel": 0.362599
    }
   },
   "7.0": {
    "H1": {
     "mean_hierarchy": 0.349206,
     "mean_polyarchy": 0.372024,
     "diff": -0.022817,
     "se": 0.018126,
     "t": -1.258845,
     "df": 165.395531,
     "p": 0.20986,
     "ci95": [
      -0.058605,
      0.01297
     ],
     "d": -0.194244,
     "sd_pooled": 0.117468,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "creative_share": {
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
    "H2a_quality": {
     "mean_hierarchy": 0.527778,
     "mean_polyarchy": 0.627976,
     "diff": -0.100198,
     "se": 0.018713,
     "t": -5.35453,
     "df": 165.995774,
     "p": 0.0,
     "ci95": [
      -0.137144,
      -0.063253
     ],
     "d": -0.826222,
     "sd_pooled": 0.121273,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "H2b_below": {
     "mean_hierarchy": 0.214286,
     "mean_polyarchy": 0.372024,
     "diff": -0.157738,
     "se": 0.018816,
     "t": -8.382982,
     "df": 165.957647,
     "p": 0.0,
     "ci95": [
      -0.194889,
      -0.120588
     ],
     "d": -1.293522,
     "sd_pooled": 0.121945,
     "n_hierarchy": 84,
     "n_polyarchy": 84
    },
    "rule_comparison_quality": {
     "mean": -0.188906,
     "se": 0.009947,
     "t": -18.992006,
     "df": 167,
     "p": 0.0,
     "ci95": [
      -0.208544,
      -0.169269
     ],
     "n_proposals": 1289,
     "n_organizations": 168
    },
    "rule_comparison_below": {
     "mean": -0.433077,
     "se": 0.019465,
     "t": -22.248447,
     "df": 166,
     "p": 0.0,
     "ci95": [
      -0.471509,
      -0.394645
     ],
     "n_proposals": 727,
     "n_organizations": 167
    },
    "category_rates": {
     "quality": 0.639385,
     "creative": 0.000496,
     "below": 0.360615,
     "novel": 0.021329
    }
   }
  },
  "continuous": {
   "H1_shortfall_score": {
    "mean_hierarchy": 1.341518,
    "mean_polyarchy": 1.382192,
    "diff": -0.040675,
    "se": 0.027162,
    "t": -1.497495,
    "df": 165.740373,
    "p": 0.136167,
    "ci95": [
     -0.094302,
     0.012953
    ],
    "d": -0.231068,
    "sd_pooled": 0.176028,
    "n_hierarchy": 84,
    "n_polyarchy": 84
   },
   "creative_novelty_score": {
    "mean_hierarchy": 4.240823,
    "mean_polyarchy": 4.34499,
    "diff": -0.104167,
    "se": 0.037913,
    "t": -2.747529,
    "df": 165.241828,
    "p": 0.006672,
    "ci95": [
     -0.179023,
     -0.029311
    ],
    "d": -0.423953,
    "sd_pooled": 0.245703,
    "n_hierarchy": 84,
    "n_polyarchy": 84
   },
   "H2a_quality_score": {
    "mean_hierarchy": 5.00124,
    "mean_polyarchy": 6.617808,
    "diff": -1.616567,
    "se": 0.08032,
    "t": -20.126463,
    "df": 92.613216,
    "p": 0.0,
    "ci95": [
     -1.776077,
     -1.457058
    ],
    "d": -3.105581,
    "sd_pooled": 0.520536,
    "n_hierarchy": 84,
    "n_polyarchy": 84
   },
   "H2b_shortfall_score": {
    "mean_hierarchy": 0.935268,
    "mean_polyarchy": 1.382192,
    "diff": -0.446925,
    "se": 0.032344,
    "t": -13.817664,
    "df": 150.343547,
    "p": 0.0,
    "ci95": [
     -0.510833,
     -0.383016
    ],
    "d": -2.132112,
    "sd_pooled": 0.209616,
    "n_hierarchy": 84,
    "n_polyarchy": 84
   },
   "rule_comparison_quality_score": {
    "mean": -21.022321,
    "se": 0.670838,
    "t": -31.337415,
    "df": 167,
    "p": 0.0,
    "ci95": [
     -22.346737,
     -19.697906
    ],
    "n": 168
   }
  }
 },
 "mediation_imai": {
  "H2a_quality": {
   "acme_hierarchy": 0.003993,
   "acme_polyarchy": 0.006944,
   "ade_hierarchy": -0.203373,
   "ade_polyarchy": -0.200422,
   "total": -0.196429,
   "acme_hierarchy_ci95": [
    -0.011078,
    0.01966
   ],
   "acme_polyarchy_ci95": [
    -0.018849,
    0.03373
   ],
   "ade_hierarchy_ci95": [
    -0.227183,
    -0.181548
   ],
   "ade_polyarchy_ci95": [
    -0.222875,
    -0.179345
   ],
   "total_ci95": [
    -0.22619,
    -0.166667
   ],
   "interaction_slope_difference": -0.424991,
   "no_interaction": {
    "acme": 0.005371,
    "ade": -0.201799,
    "total": -0.196429,
    "acme_ci95": [
     -0.014277,
     0.025718
    ],
    "ade_ci95": [
     -0.22392,
     -0.181252
    ]
   },
   "sensitivity_rho_at_zero_acme": 0.675675,
   "acme_at_rho": {
    "-0.4": 0.007928,
    "-0.2": 0.006567,
    "0.0": 0.005371,
    "0.2": 0.004175,
    "0.4": 0.002813
   }
  },
  "H2b_below": {
   "acme_hierarchy": -0.004116,
   "acme_polyarchy": -0.006944,
   "ade_hierarchy": -0.054563,
   "ade_polyarchy": -0.057392,
   "total": -0.061508,
   "acme_hierarchy_ci95": [
    -0.01934,
    0.011494
   ],
   "acme_polyarchy_ci95": [
    -0.032738,
    0.018849
   ],
   "ade_hierarchy_ci95": [
    -0.066468,
    -0.042659
   ],
   "ade_polyarchy_ci95": [
    -0.071314,
    -0.044757
   ],
   "total_ci95": [
    -0.085317,
    -0.03869
   ],
   "interaction_slope_difference": -0.407298,
   "no_interaction": {
    "acme": -0.005436,
    "ade": -0.056072,
    "total": -0.061508,
    "acme_ci95": [
     -0.025594,
     0.014578
    ],
    "ade_ci95": [
     -0.067573,
     -0.044523
    ]
   },
   "sensitivity_rho_at_zero_acme": 0.874004,
   "acme_at_rho": {
    "-0.4": -0.006755,
    "-0.2": -0.006053,
    "0.0": -0.005436,
    "0.2": -0.004819,
    "0.4": -0.004117
   }
  }
 },
 "judge_pass_reliability": {
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
 "judge_pass_reliability_claude": {
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
 "judge_agreement_with_claude": {
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
