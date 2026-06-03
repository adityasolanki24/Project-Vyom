%% fig7_val_disturbance.m  
%  Scenario 3: the full original nonlinear system with a wind gust,
%  gimbal saturation, and IMU sensor noise. Reference = 0 (vertical flight).

tvc_params;
p = tvc_make_params(1,1);

p.r_fun = @(t) 0;

% Wind gus: 4 deg equivalent angle of attack from t=1.5 s
gust = deg2rad(4);
p.d_fun = @(t) gust*(t>=1.5);

% Sensor noise: zero-mean Gaussian, std = 0.05 deg
rng(1);
tn_grid = 0:0.001:5;
noise_grid = deg2rad(0.05)*randn(size(tn_grid));
p.noise_fun = @(t) interp1(tn_grid, noise_grid, t, 'previous', 0);

[tn,xn] = ode45(@(t,x) tvc_nonlinear(t,x,p), [0 5], zeros(5,1), ...
                odeset('RelTol',1e-6,'AbsTol',1e-8,'MaxStep',0.005));

% recompute gimbal command from simulation states
dc = zeros(size(tn));
for k = 1:numel(tn)
    e  = p.kr*p.r_fun(tn(k)) - (xn(k,1) + p.noise_fun(tn(k)));
    v  = (p.Kp + p.Kd*p.N)*e - p.Kd*p.N^2*xn(k,5);
    dc(k) = max(min(v, p.dmax), -p.dmax);
end

% act. gimbal angle (state 3 from ode45)
delta_actual = rad2deg(xn(:,3));

dc_deg   = rad2deg(dc);
dc_range = max(abs(dc_deg)) * 1.5;      % 50% buffer
if dc_range < 0.1; dc_range = 0.5; end  % minimum readable range

figure('Color','w','Position',[100 100 560 460]);

subplot(2,1,1);
plot(tn, rad2deg(xn(:,1)), 'LineWidth', 1.4); hold on;
yline(0, ':', 'reference');
xline(1.5, '--', 'gust on');
grid on;
ylabel('Pitch \theta (deg)');
title('Scenario 3: wind gust + saturation + sensor noise');

subplot(2,1,2);
plot(tn, dc_deg, 'LineWidth', 1.2); hold on;
% Show saturation limits as context but let axes auto-scale
yline( 10, 'r--', '+10° limit');
yline(-10, 'r--', '-10° limit');
ylim([-dc_range dc_range]);   % auto-scaled to actual motion
grid on;
xlabel('Time (s)');
ylabel('Gimbal \delta_c (deg)');

exportgraphics(gcf, 'fig_val_disturbance.pdf', 'ContentType', 'vector');
disp('saved fig_val_disturbance.pdf');

fprintf('Steady-state pitch = %.3f deg\n', rad2deg(xn(end,1)));
fprintf('Peak gimbal command = %.4f deg  (limit = 10 deg)\n', max(abs(dc_deg)));
fprintf('Note: gimbal uses only %.1f%% of available travel\n', max(abs(dc_deg))/10*100);