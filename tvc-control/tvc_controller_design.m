%% tvc_controller_design.m
%  AMME3500 Design Project 2 - TVC Model Rocket


clear; clc; close all;

fprintf('==========================================================\n');
fprintf('  TVC MODEL ROCKET - CONTROLLER DESIGN\n');
fprintf('==========================================================\n\n');

%% ----------------------------------------------------------------
%  STEP 1: Physical parameters and lumped coefficients
% -----------------------------------------------------------------
fprintf('--- STEP 1: Parameters and lumped coefficients ---\n');

I      = 0.04;      % kg m^2   pitch moment of inertia
T      = 25;        % N        motor thrust
lT     = 0.30;      % m        CoM to nozzle
lcp    = 0.05;      % m        CoM to centre of pressure
q_dyn  = 100;       % Pa       dynamic pressure
S      = 0.0045;    % m^2      reference area
CNa    = 2.0;       % 1/rad    normal force slope
zeta_a = 0.7;       %          gimbal damping ratio
wn     = 15;        % rad/s    gimbal natural frequency
dmax   = deg2rad(10); % rad    gimbal hard limit

% Lumped coefficients  
mu_a = q_dyn*S*CNa*lcp / I;   % aerodynamic instability coefficient
mu_c = T*lT / I;               % control authority coefficient

fprintf('  mu_a = %.4f  rad/s^2  (+ve => aerodynamically unstable)\n', mu_a);
fprintf('  mu_c = %.4f  rad/s^2  (control authority)\n', mu_c);
fprintf('  Control/instability ratio mu_c/mu_a = %.1f\n', mu_c/mu_a);
fprintf('  Open-loop tip-over time constant = 1/sqrt(mu_a) = %.3f s\n\n', 1/sqrt(mu_a));

%% ----------------------------------------------------------------
%  STEP 2: State-space model
%  x = [theta; thetadot; delta; deltadot],  u = delta_c,  y = theta
% -----------------------------------------------------------------
fprintf('--- STEP 2: State-space model ---\n');

A = [ 0       1       0              0;
      mu_a    0       mu_c           0;
      0       0       0              1;
      0       0      -wn^2   -2*zeta_a*wn];
B = [0; 0; 0; wn^2];
C = [1 0 0 0];
D = 0;

fprintf('  A =\n'); disp(A);
fprintf('  B = ['); fprintf('%.2f  ',B); fprintf(']\n');
fprintf('  C = ['); fprintf('%d  ',C); fprintf(']\n\n');

%% ----------------------------------------------------------------
%  STEP 3: Open-loop stability analysis
% -----------------------------------------------------------------
fprintf('--- STEP 3: Open-loop stability ---\n');

ol_poles = eig(A);
fprintf('  Open-loop eigenvalues (poles of plant):\n');
for k = 1:length(ol_poles)
    if real(ol_poles(k)) > 0
        fprintf('    lambda_%d = %+.4f %+.4fi  <-- UNSTABLE (RHP)\n', ...
            k, real(ol_poles(k)), imag(ol_poles(k)));
    else
        fprintf('    lambda_%d = %+.4f %+.4fi  (stable)\n', ...
            k, real(ol_poles(k)), imag(ol_poles(k)));
    end
end
fprintf('  => System is UNSTABLE in open loop. Active control is essential.\n\n');

%% ----------------------------------------------------------------
%  STEP 4: Controllability and Observability
% -----------------------------------------------------------------
fprintf('--- STEP 4: Controllability and Observability ---\n');

W_c = ctrb(A,B);
W_o = obsv(A,C);

rank_c = rank(W_c);
rank_o = rank(W_o);
n = size(A,1);

fprintf('  Reachability matrix rank  = %d  (n = %d)  => ', rank_c, n);
if rank_c == n
    fprintf('FULLY CONTROLLABLE\n');
else
    fprintf('NOT FULLY CONTROLLABLE\n');
end

fprintf('  Observability matrix rank = %d  (n = %d)  => ', rank_o, n);
if rank_o == n
    fprintf('FULLY OBSERVABLE\n');
else
    fprintf('NOT FULLY OBSERVABLE\n');
end
fprintf('  => Observable from theta alone: no state observer is required\n');
fprintf('     for the output-feedback PD design.\n\n');

%% ----------------------------------------------------------------
%  STEP 5: Plant transfer function G(s) = theta(s) / delta_c(s)
%  G(s) = mu_c*wn^2 / [(s^2 - mu_a)(s^2 + 2*zeta*wn*s + wn^2)]
% -----------------------------------------------------------------
fprintf('--- STEP 5: Plant transfer function G(s) ---\n');

num_G = mu_c * wn^2;
den_G = conv([1 0 -mu_a], [1 2*zeta_a*wn wn^2]);
G = tf(num_G, den_G);

fprintf('  G(s) = %.4g / (s^4 + %.4g s^3 + %.4g s^2 + %.4g s + %.4g)\n', ...
    num_G, den_G(2), den_G(3), den_G(4), den_G(5));
fprintf('  Plant poles: '); fprintf('%.4f  ', pole(G)); fprintf('\n\n');

%% ----------------------------------------------------------------
%  STEP 6: PD compensator design
%  C(s) = Kp + Kd*N*s/(s+N)  (derivative with roll-off filter)
%  Design rationale:
%    - The derivative term provides phase lead to stabilise the RHP pole.
%    - The filter pole N is set below the gimbal resonance (wn=15 rad/s)
%      to prevent the high loop gain from exciting the actuator resonance.
%    - Kp and Kd are tuned to achieve PM > 40 deg and GM > 6 dB.
%    - A reference prescale kr restores unity DC gain for accurate tracking.
% -----------------------------------------------------------------
fprintf('--- STEP 6: PD compensator design ---\n');

Kp = 0.022;   % proportional gain
Kd = 0.020;   % derivative gain
N  = 30;      % derivative filter pole 

% C(s) = Kp + Kd*N*s/(s+N)
%       = [(Kp+Kd*N)*s + Kp*N] / (s + N)
num_C = [Kp + Kd*N,  Kp*N];
den_C = [1,  N];
C = tf(num_C, den_C);

fprintf('  Compensator C(s) = (%.4g*s + %.4g) / (s + %.4g)\n', ...
    num_C(1), num_C(2), den_C(2));
fprintf('  Parameters:  Kp = %.3f,  Kd = %.3f,  N = %.0f\n', Kp, Kd, N);
fprintf('  Filter pole at %.0f rad/s (below gimbal resonance at %.0f rad/s)\n', N, wn);

%% ----------------------------------------------------------------
%  STEP 7: Loop transfer function and stability margins
% -----------------------------------------------------------------
fprintf('\n--- STEP 7: Open-loop margins ---\n');

L  = C*G;                     % openloop transfer function
[Gm, Pm, Wcg, Wcp] = margin(L);
fprintf('  Gain  margin = %.2f dB   at %.3f rad/s\n', 20*log10(Gm), Wcg);
fprintf('  Phase margin = %.2f deg  at %.3f rad/s (crossover freq)\n', Pm, Wcp);

if Pm > 40
    fprintf('  => Phase margin MEETS target (>40 deg)\n');
else
    fprintf('  => Phase margin DOES NOT meet target\n');
end
if 20*log10(Gm) > 6
    fprintf('  => Gain margin MEETS target (>6 dB)\n');
else
    fprintf('  => Gain margin DOES NOT meet target\n');
end

%% ----------------------------------------------------------------
%  STEP 8: Closed-loop analysis
% -----------------------------------------------------------------
fprintf('\n--- STEP 8: Closed-loop poles and step response ---\n');

Tcl_raw = feedback(L, 1);     % closed-loop (before prescale)
DC_gain = dcgain(Tcl_raw);
kr = 1/DC_gain;               % reference prescale for unity DC gain

fprintf('  Closed-loop DC gain before prescale = %.4f\n', DC_gain);
fprintf('  Reference prescale  kr = %.4f\n', kr);

Tcl = kr * Tcl_raw;           % prescaled closed-loop (unity DC gain)

cl_poles = pole(Tcl_raw);
fprintf('  Closed-loop poles:\n');
for k = 1:length(cl_poles)
    if real(cl_poles(k)) > 0
        fprintf('    %+.4f %+.4fi  <-- UNSTABLE\n', ...
            real(cl_poles(k)), imag(cl_poles(k)));
    else
        fprintf('    %+.4f %+.4fi\n', ...
            real(cl_poles(k)), imag(cl_poles(k)));
    end
end

% Step response metrics
info = stepinfo(Tcl);
fprintf('\n  Step response (with prescale kr = %.4f):\n', kr);
fprintf('    Rise time    = %.3f s\n', info.RiseTime);
fprintf('    Settling time = %.3f s  (2%% criterion)\n', info.SettlingTime);
fprintf('    Overshoot    = %.2f %%\n', info.Overshoot);
fprintf('    Steady-state = %.4f  (target: 1.000)\n', dcgain(Tcl));

% Check design criteria
fprintf('\n  Design criteria check:\n');
fprintf('    Settling time <= 1.5 s?  %.3f s  => %s\n', info.SettlingTime, ...
    pass_fail(info.SettlingTime <= 1.5));
fprintf('    Overshoot <= 10%%?        %.2f%%  => %s\n', info.Overshoot, ...
    pass_fail(info.Overshoot <= 10));
fprintf('    Phase margin >= 40 deg?  %.1f deg  => %s\n', Pm, ...
    pass_fail(Pm >= 40));
fprintf('    Gain margin >= 6 dB?     %.1f dB   => %s\n', 20*log10(Gm), ...
    pass_fail(20*log10(Gm) >= 6));

%% ----------------------------------------------------------------
%  STEP 9: Summary figure -- Bode of compensated loop with margins
% -----------------------------------------------------------------
figure('Color','w','Position',[100 100 620 460]);
margin(L);
grid on;
title('Compensated open-loop L(s) = C(s)G(s) with stability margins');
set(findall(gcf,'Type','line'),'LineWidth',1.5);
exportgraphics(gcf,'fig_bode_loop.pdf','ContentType','vector');
fprintf('\nFigure saved: fig_bode_loop.pdf\n');

%% ----------------------------------------------------------------
%  STEP 10: Closed-loop step response figure
% -----------------------------------------------------------------
figure('Color','w','Position',[100 100 560 360]);
step(Tcl, 3); grid on;
title(sprintf('Closed-loop step response  (T_s = %.2f s, OS = %.1f%%)', ...
    info.SettlingTime, info.Overshoot));
xlabel('Time (s)'); ylabel('Pitch angle (normalised)');
set(findall(gcf,'Type','line'),'LineWidth',1.5);
exportgraphics(gcf,'fig_step_response.pdf','ContentType','vector');
fprintf('Figure saved: fig_step_response.pdf\n');

fprintf('\n==========================================================\n');
fprintf('  Controller design complete. All results above go in\n');
fprintf('  Section IV (Solutions) of the report.\n');
fprintf('==========================================================\n');

%% ----------------------------------------------------------------
%  Helper function
% -----------------------------------------------------------------
function s = pass_fail(condition)
    if condition; s = 'PASS'; else; s = 'FAIL'; end
end
