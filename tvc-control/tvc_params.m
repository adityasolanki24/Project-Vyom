%% tvc_params.m
%  Shared parameters, plant, and compensator for the TVC model rocket project.
%  Every plotting script calls this first:  run('tvc_params.m')  or
%  tvc_params;
%%Physical params
I    = 0.04;     % kg m^2   pitch moment of inertia
T    = 25;       % N        motor thrust
lT   = 0.30;     % m        CoM to nozzle
lcp  = 0.05;     % m        CoM to centre of pressure
q    = 100;      % Pa       dynamic pressure
S    = 0.0045;   % m^2      reference area
CNa  = 2.0;      % 1/rad    normal force slope
zeta_a = 0.7;    % -        gimbal servo damping ratio
wn   = 15;       % rad/s    gimbal servo natural frequency
dmax = deg2rad(10);   % rad  gimbal mechanical limit (+/-10 deg)

%%Lumped coefficients 
mu_a = q*S*CNa*lcp / I;    % aerodynamic instability  (= 1.125)
mu_c = T*lT / I;           % control authority        (= 187.5)

fprintf('mu_a = %.4f  (1/s^2, +ve => unstable)\n', mu_a);
fprintf('mu_c = %.4f  (1/s^2)\n', mu_c);
fprintf('open-loop tip-over time constant 1/sqrt(mu_a) = %.3f s\n', 1/sqrt(mu_a));

%%Linear state-space model  x = [theta, thetadot, delta, deltadot]
A = [ 0      1      0          0;
      mu_a   0      mu_c       0;
      0      0      0          1;
      0      0     -wn^2  -2*zeta_a*wn];
B = [0; 0; 0; wn^2];
C = [1 0 0 0];
D = 0;
sys_ss = ss(A,B,C,D);

%% Plant transfer function  G(s) = theta(s)/delta_c(s) 
G = tf(mu_c*wn^2, conv([1 0 -mu_a], [1 2*zeta_a*wn wn^2]));

%% PD compensator with derivative roll-] off filter]
%  C(s) = Kp + Kd*N*s/(s+N)
Kp = 0.022;
Kd = 0.020;
N  = 30;
C  = tf([Kp+Kd*N, Kp*N], [1 N]);

%%Loop and closedloop transfer functions -----
L  = C*G;                 % open loop  L(s) = C(s)G(s)
Tcl_raw = feedback(L,1);  % closed-loop before prescale

% The PD loop has DC gain ~1.375, so a reference prescale kr restores unity
% DC gain for accurate tracking 
kr  = 1/dcgain(Tcl_raw);  % ~0.727
Tcl = kr*Tcl_raw;         % closed-loop reference -> output (unity DC gain)
fprintf('  Reference prescale kr = %.4f (restores unity DC gain)\n', kr);

%% Report
[Gm,Pm,Wcg,Wcp] = margin(L);
fprintf('\nClosed-loop summary:\n');
fprintf('  Phase margin = %.1f deg at %.2f rad/s\n', Pm, Wcp);
fprintf('  Gain  margin = %.1f dB  at %.2f rad/s\n', 20*log10(Gm), Wcg);
fprintf('  Open-loop poles:  '); disp(round(pole(G).',3));
fprintf('  Closed-loop poles:'); disp(round(pole(Tcl).',3));
