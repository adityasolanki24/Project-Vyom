%% fig8_val_sine.m  
%  Response to a sinusoidsal wind gust about vertical flight

tvc_params;
p = tvc_make_params(1,1);
p.r_fun = @(t) 0;

% Sinusoidal gust: amplitude 3 deg, 0.5 Hz, starting at t=1 s
amp = deg2rad(3); f = 0.5;
p.d_fun = @(t) amp*sin(2*pi*f*t).*(t>=1);

[tn,xn] = ode45(@(t,x) tvc_nonlinear(t,x,p), [0 6], zeros(5,1), ...
                odeset('RelTol',1e-7,'AbsTol',1e-9));

dc = zeros(size(tn));
for k=1:numel(tn)
    e = p.kr*p.r_fun(tn(k)) - xn(k,1);
    v = (p.Kp+p.Kd*p.N)*e - p.Kd*p.N^2*xn(k,5);
    dc(k) = max(min(v,p.dmax),-p.dmax);
end

figure('Color','w','Position',[100 100 560 380]);
plot(tn,rad2deg(xn(:,1)),'LineWidth',1.6); hold on;
plot(tn,rad2deg(arrayfun(p.d_fun,tn)),'--','LineWidth',1.0);
plot(tn,rad2deg(dc),':','LineWidth',1.2);
grid on; xlabel('Time (s)'); ylabel('Angle (deg)');
legend('Pitch \theta','Gust (input)','Gimbal \delta_c','Location','best');
title('Response to sinusoidal wind gust (\theta_{ref}=0)');

exportgraphics(gcf,'fig_val_sine.pdf','ContentType','vector');
disp('saved fig_val_sine.pdf');
