function p = tvc_make_params(scale_mu_a, scale_mu_c)
%% tvc_make_params.m
if nargin < 1, scale_mu_a = 1.0; end
if nargin < 2, scale_mu_c = 1.0; end

% Physical params
p.I = 0.04; p.T = 25; p.lT = 0.30; p.lcp = 0.05;
p.q = 100;  p.S = 0.0045; p.CNa = 2.0;
p.zeta_a = 0.7; p.wn = 15;
p.dmax = deg2rad(10);

% Apply uncertainty by scaling the effective coefficients.
% mu_a = q*S*CNa*lcp/I ; we scale via lcp (aero) and T (control) for physicality.
p.lcp = p.lcp * scale_mu_a;
p.T   = p.T   * scale_mu_c;

% Controller gains (designed on the nominal linear model)
p.Kp = 0.022; p.Kd = 0.020; p.N = 30;
p.kr = 0.7273;   % reference prescale for unity DC gain

% Default reference / disturbance / noise = none
p.r_fun     = @(t) 0;
p.d_fun     = @(t) 0;
p.noise_fun = @(t) 0;
end
