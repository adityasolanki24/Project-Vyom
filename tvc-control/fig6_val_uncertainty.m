%% fig6_val_uncertainty.m
%  Scenario 2: parameter uncertainty. mu_a and mu_c varied +/-30%
%  (mass/inertia/thrust change as propellant burns). Same fixed-gain controller.

tvc_params;

theta_ref = deg2rad(5);
scales = [0.7 1.0 1.3];   % -30%, nominal, +30%
labels = {'-30%','nominal','+30%'};
colors = lines(3);

figure('Color','w','Position',[100 100 560 460]);
subplot(2,1,1); hold on;
subplot(2,1,2); hold on;

for i=1:numel(scales)
    p = tvc_make_params(scales(i), scales(i));
    p.r_fun = @(t) theta_ref*(t>=0.5);
    [tn,xn] = ode45(@(t,x) tvc_nonlinear(t,x,p), [0 4], zeros(5,1), ...
                    odeset('RelTol',1e-7,'AbsTol',1e-9));
    % gimbal command
    dc = zeros(size(tn));
    for k=1:numel(tn)
        e = p.kr*p.r_fun(tn(k)) - xn(k,1);
        v = (p.Kp+p.Kd*p.N)*e - p.Kd*p.N^2*xn(k,5);
        dc(k) = max(min(v,p.dmax),-p.dmax);
    end
    subplot(2,1,1);
    plot(tn,rad2deg(xn(:,1)),'LineWidth',1.5,'Color',colors(i,:));
    subplot(2,1,2);
    plot(tn,rad2deg(dc),'LineWidth',1.5,'Color',colors(i,:));
end

subplot(2,1,1);
yline(rad2deg(theta_ref),':','reference'); grid on;
ylabel('Pitch \theta (deg)'); legend(labels,'Location','southeast');
title('Scenario 2: \pm30% uncertainty in \mu_a and \mu_c');

subplot(2,1,2);
yline( rad2deg(deg2rad(10)),'r--'); yline(-rad2deg(deg2rad(10)),'r--');
grid on; xlabel('Time (s)'); ylabel('Gimbal \delta_c (deg)');

exportgraphics(gcf,'fig_val_uncertainty.pdf','ContentType','vector');
disp('saved fig_val_uncertainty.pdf');
