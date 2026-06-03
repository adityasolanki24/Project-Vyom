%% fig5_val_nominal.m  
%  Scenario 1: nominal conditions. Step command in pitch.
%  Compares the nonlinear (original) response to the linear-model prediction,
%  and shows the gimbal command against the +/-10 deg limit

tvc_params;                 % gives us the linear Tcl 
p = tvc_make_params(1,1);   % nominal nonlinear params

% Step command: 5 degrees at t = 0.5 s
theta_ref = deg2rad(5);
p.r_fun = @(t) theta_ref*(t>=0.5);

%  Nonlinear simul
tspan = [0 4];
x0 = zeros(5,1);
opts = odeset('RelTol',1e-7,'AbsTol',1e-9);
[tn,xn] = ode45(@(t,x) tvc_nonlinear(t,x,p), tspan, x0, opts);

% recover the gimbal command applied 
delta_c = zeros(size(tn));
for k=1:numel(tn)
    e = p.kr*p.r_fun(tn(k)) - xn(k,1);
    dc = (p.Kp+p.Kd*p.N)*e - p.Kd*p.N^2*xn(k,5);
    delta_c(k) = max(min(dc,p.dmax),-p.dmax);
end

%Linearmodel prediction for comparison 
tl = linspace(0,4,800);
rl = theta_ref*(tl>=0.5);
yl = lsim(Tcl, rl, tl);

% ----- Plot -----
figure('Color','w','Position',[100 100 560 460]);
subplot(2,1,1);
plot(tn, rad2deg(xn(:,1)),'LineWidth',1.6); hold on;
plot(tl, rad2deg(yl),'--','LineWidth',1.3);
yline(rad2deg(theta_ref),':','reference');
grid on; ylabel('Pitch \theta (deg)');
legend('Nonlinear (original)','Linear prediction','Location','southeast');
title('Scenario 1: nominal step response');

subplot(2,1,2);
plot(tn, rad2deg(delta_c),'LineWidth',1.6); hold on;
yline( rad2deg(p.dmax),'r--','+10^\circ limit');
yline(-rad2deg(p.dmax),'r--','-10^\circ limit');
grid on; xlabel('Time (s)'); ylabel('Gimbal \delta_c (deg)');

exportgraphics(gcf,'fig_val_nominal.pdf','ContentType','vector');
disp('saved fig_val_nominal.pdf');

% Print metrics
info = stepinfo(rad2deg(xn(:,1)),tn,rad2deg(theta_ref));
fprintf('Nominal: Ts=%.3f s, OS=%.1f%%, peak gimbal=%.2f deg\n',...
    info.SettlingTime, info.Overshoot, max(abs(rad2deg(delta_c))));
