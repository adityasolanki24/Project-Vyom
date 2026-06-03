# Thrust Vector Control — MATLAB Design

Linear and nonlinear TVC controller design for the Vyom model rocket 

## Entry point

Run from this folder in MATLAB:

```matlab
tvc_controller_design
```

## Scripts

| File | Purpose |
|------|---------|
| `tvc_controller_design.m` | Main design script (state-space, PID, analysis) |
| `tvc_params.m` | Parameter definitions |
| `tvc_make_params.m` | Build param struct with optional uncertainty scaling |
| `tvc_nonlinear.m` | Nonlinear simulation |
| `fig1_openloop.m` … `fig8_val_sine.m` | Analysis and validation figures |
| `fig_gain_sensitivity.m` | Gain sensitivity study |

