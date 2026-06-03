function dx = tvc_nonlinear(t, x, p)
%% tvc_nonlinear.m

theta    = x(1);
thetadot = x(2);
delta    = x(3);
deltadot = x(4);
xc       = x(5);     % derivative-filter state

%Ref and disturbance 
r = p.r_fun(t);          % commanded pitch (rad)
d = p.d_fun(t);          % disturbance moment

%output with optional sensor noise 
y = theta + p.noise_fun(t);

%PD compensator with derivative roll-off, state-space form
%  C(s) = Kp + Kd*N - Kd*N^2/(s+N)
%  xc_dot = -N*xc + e ;  u = (Kp+Kd*N)*e - Kd*N^2*xc   (with e = r - y)
e  = p.kr*r - y;
xc_dot = -p.N*xc + e;
delta_c = (p.Kp + p.Kd*p.N)*e - p.Kd*p.N^2*xc;

%Gimbal saturation (hard nonlinearity) 
delta_c = max(min(delta_c, p.dmax), -p.dmax);

% noonlinear plant dynamics -
% Pitch:   I*thddot = qS*CNa*lcp*sin(theta + d) + T*lT*sin(delta)
%   the disturbance d adds to the effective angle of attack
thddot = (p.q*p.S*p.CNa*p.lcp*sin(theta + d) + p.T*p.lT*sin(delta)) / p.I;

% Gimbal servo (linear, second order)
ddddot = p.wn^2*(delta_c - delta) - 2*p.zeta_a*p.wn*deltadot;

dx = [thetadot; thddot; deltadot; ddddot; xc_dot];
end
